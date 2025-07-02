# plately_ai/api/routers/simulation_api.py

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Dict, Any

from plately_ai.api.models.simulation_models import (
    PriceSimulationRequest, PriceSimulationResponse,
    PEDRequest, XEDRequest, PEDResponseData, XEDResponseData, ErrorResponse
)
from plately_ai.simulation.simulation_engine import SimulationEngine
from plately_ai.simulation.elasticity_calculator import (
    calculate_ped_from_simulation_data,
    calculate_xed_from_simulation_data
)

router = APIRouter()

# --- Helper for accessing SimulationEngine ---
# This is a simple way to get it from app.state.
# FastAPI's Depends system is more robust for complex dependencies.
def get_simulation_engine(request: Request) -> SimulationEngine:
    engine = request.app.state.simulation_engine
    if not engine:
        raise HTTPException(status_code=503, detail="Simulation engine is not available.")
    return engine

# --- Endpoints ---

@router.post(
    "/simulate",
    response_model=PriceSimulationResponse,
    responses={503: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def simulate_price_change_endpoint(
    sim_request: PriceSimulationRequest,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """
    Receives a price change, runs a simulation, and returns comparative results.
    """
    item_id_to_change = sim_request.item_id
    new_price = sim_request.new_price

    original_menu = engine.menu_items_master_list # Keep a reference

    # Run baseline simulation (with original prices)
    engine.reset_menu_to_master()
    baseline_choices = engine.run_simulation_step()
    baseline_results = engine.analyze_results(baseline_choices)

    # Run scenario simulation
    # run_price_scenario handles resetting the menu internally after its run
    scenario_results = engine.run_price_scenario(item_id_to_change, new_price)

    if scenario_results is None:
        # This implies item_id_to_change was not found or new_price was invalid (though Pydantic ge=0 helps)
        # run_price_scenario itself returns None if update_menu_item_price fails
        item_exists = any(item['id'] == item_id_to_change for item in original_menu)
        if not item_exists:
             raise HTTPException(status_code=404, detail=f"Item with ID '{item_id_to_change}' not found.")
        # If item exists, then price must have been invalid for the engine's internal update to fail
        # (e.g. if a more complex validation existed there, though not currently)
        # Pydantic already checks new_price >= 0.
        # The simulation engine's update_menu_item_price also checks new_price < 0, but Pydantic would catch it first.
        # So, this path is less likely if Pydantic validation is robust.
        raise HTTPException(status_code=400, detail=f"Failed to run scenario for item {item_id_to_change}. Price might be invalid or item missing, though Pydantic should catch most price issues.")


    comparison_data = []
    changed_item_name = ""
    original_changed_item_price = None

    for item in original_menu:
        name = item['name']
        current_original_price = item['price']
        scenario_price_val = new_price if item['id'] == item_id_to_change else current_original_price

        if item['id'] == item_id_to_change:
            changed_item_name = name
            original_changed_item_price = current_original_price

        comparison_data.append({
            "name": name,
            "original_price": current_original_price,
            "scenario_price": scenario_price_val,
            "baseline_demand": baseline_results["demand_per_item"].get(name, 0),
            "scenario_demand": scenario_results["demand_per_item"].get(name, 0),
            "baseline_revenue": baseline_results["revenue_per_item"].get(name, 0),
            "scenario_revenue": scenario_results["revenue_per_item"].get(name, 0)
        })

    # Simplified cross-price elasticity (same as Flask version for this endpoint)
    elasticities: Dict[str, Any] = {}
    if original_changed_item_price is not None and original_changed_item_price > 0 and new_price != original_changed_item_price:
        percentage_change_price_changed_item = (new_price - original_changed_item_price) / original_changed_item_price
        if percentage_change_price_changed_item != 0:
            for item_data in comparison_data:
                if item_data['name'] == changed_item_name: continue
                q1, q2 = item_data['baseline_demand'], item_data['scenario_demand']
                if q1 > 0:
                    elasticities[item_data['name']] = round(((q2 - q1) / q1) / percentage_change_price_changed_item, 3)
                elif q2 > 0 : # q1 is 0, q2 is >0 (new demand)
                     elasticities[item_data['name']] = "Inf (New Demand)" # Or some other indicator
                else: # q1 and q2 are 0
                    elasticities[item_data['name']] = 0.0 # Or "N/A"

    return PriceSimulationResponse(
        message=f"Simulation complete for {changed_item_name} at ${new_price:.2f}",
        baseline_total_revenue=baseline_results["total_revenue"],
        scenario_total_revenue=scenario_results["total_revenue"],
        comparison_table=comparison_data,
        cross_price_elasticities_with_changed_item=elasticities,
        changed_item_id=item_id_to_change,
        new_price_for_changed_item=new_price
    )


@router.post(
    "/calculate-elasticities",
    response_model=Dict[str, Any], # More dynamic: PEDResponseData | XEDResponseData
    responses={503: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def calculate_elasticities_api(
    request_data: Dict[str, Any], # Using Dict for initial parsing, then specific models
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    elasticity_type = request_data.get('type', '').upper()

    if elasticity_type == 'PED':
        try:
            ped_input = PEDRequest(**request_data)
        except ValueError as e: # Pydantic validation error
            raise HTTPException(status_code=400, detail=str(e))

        item_id_vary = ped_input.item_id_vary
        try:
            # Parse comma-separated string to list of floats
            ped_price_changes = [float(x.strip()) for x in ped_input.ped_price_changes.split(',')]
            if not all(-1 < x < 10 for x in ped_price_changes):
                 raise ValueError("Percentage changes for PED should be reasonable (e.g., between >-1 and <10).")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid format for PED price changes: {str(e)}. Expect comma-separated floats.")

        sim_data = engine.run_ped_simulation_set(item_id_vary, ped_price_changes)
        if not sim_data:
            raise HTTPException(status_code=404, detail=f"Could not generate simulation data for PED of item {item_id_vary}. Item may not exist or other simulation error.")

        ped_results = calculate_ped_from_simulation_data(sim_data)
        item_info = next((item for item in engine.menu_items_master_list if item['id'] == item_id_vary), None)
        item_name = item_info['name'] if item_info else item_id_vary

        return PEDResponseData(type="PED", item_name=item_name, item_id=item_id_vary, data=ped_results)

    elif elasticity_type == 'XED':
        try:
            xed_input = XEDRequest(**request_data)
        except ValueError as e: # Pydantic validation error
            raise HTTPException(status_code=400, detail=str(e))

        target_item_id = xed_input.target_item_id
        affecting_item_id = xed_input.affecting_item_id
        try:
            xed_price_change = float(xed_input.xed_price_change.strip())
            if not (-1 < xed_price_change < 10):
                raise ValueError("Percentage change for XED should be reasonable.")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid format for XED price change: {str(e)}. Expect a single float.")

        if target_item_id == affecting_item_id:
            raise HTTPException(status_code=400, detail="Target and affecting items cannot be the same for XED.")

        sim_data = engine.run_xed_simulation_set(target_item_id, affecting_item_id, xed_price_change)
        if not sim_data:
            raise HTTPException(status_code=500, detail=f"Could not generate simulation data for XED between {target_item_id} and {affecting_item_id}.")

        xed_result = calculate_xed_from_simulation_data(sim_data)
        if not xed_result: # Should not happen if sim_data is valid, but defensive
             raise HTTPException(status_code=500, detail="Failed to calculate XED from simulation data.")

        return XEDResponseData(type="XED", data=xed_result)

    else:
        raise HTTPException(status_code=400, detail=f"Invalid elasticity type: {elasticity_type}. Must be 'PED' or 'XED'.")
