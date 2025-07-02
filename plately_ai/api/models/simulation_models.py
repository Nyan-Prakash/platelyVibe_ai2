# plately_ai/api/models/simulation_models.py

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional

# --- Shared/Base Models ---

class MenuItemBase(BaseModel):
    id: str
    name: str
    price: float = Field(..., gt=0) # Price must be greater than 0

class MenuItemInDB(MenuItemBase):
    # Could include other DB specific fields if we had a DB
    pass


# --- Price Simulation Endpoint (`/simulate`) ---

class PriceSimulationRequest(BaseModel):
    item_id: str
    new_price: float = Field(..., ge=0) # New price can be 0, but not negative

class DemandRevenueItem(BaseModel):
    name: str
    original_price: float
    scenario_price: float
    baseline_demand: int
    scenario_demand: int
    baseline_revenue: float
    scenario_revenue: float

class PriceSimulationResponse(BaseModel):
    message: str
    baseline_total_revenue: float
    scenario_total_revenue: float
    comparison_table: List[DemandRevenueItem]
    cross_price_elasticities_with_changed_item: Dict[str, Any] # Could be float or string "N/A"
    changed_item_id: str
    new_price_for_changed_item: float


# --- Elasticity Calculation Endpoint (`/calculate-elasticities`) ---

class ElasticityBaseRequest(BaseModel):
    type: str # "PED" or "XED"

class PEDRequest(ElasticityBaseRequest):
    type: str = "PED"
    item_id_vary: str
    ped_price_changes: str # Comma-separated list of floats, e.g., "-0.2,-0.1,0.1,0.2"

    @validator('ped_price_changes')
    def validate_ped_price_changes_format(cls, value):
        try:
            changes = [float(x.strip()) for x in value.split(',')]
            if not changes:
                raise ValueError("PED price changes list cannot be empty.")
            if not all(-1 < x < 10 for x in changes): # Allow up to 1000% increase, down to -99%
                 raise ValueError("Percentage changes for PED should be reasonable (e.g., between >-1 and <10).")
            return value # Return original string for the route to parse again, or parse here and store list
        except ValueError as e:
            raise ValueError(f"Invalid format for PED price changes: {str(e)}. Expect comma-separated floats.")


class XEDRequest(ElasticityBaseRequest):
    type: str = "XED"
    target_item_id: str
    affecting_item_id: str
    xed_price_change: str # Single float as string, e.g., "0.1"

    @validator('xed_price_change')
    def validate_xed_price_change_format(cls, value):
        try:
            change = float(value.strip())
            if not (-1 < change < 10):
                 raise ValueError("Percentage change for XED should be reasonable (e.g., between >-1 and <10).")
            return value # Return original string
        except ValueError as e:
            raise ValueError(f"Invalid format for XED price change: {str(e)}. Expect a single float.")


class PEDDataPoint(BaseModel):
    percentage_change_price: float
    original_price: float
    new_price: float
    original_demand: int
    new_demand: int
    ped_value: Optional[float] # Can be None or math.inf

class PEDResponseData(BaseModel):
    type: str = "PED"
    item_name: str
    item_id: str
    data: List[PEDDataPoint]

class XEDResponseDataDetail(BaseModel):
    target_item_name: str
    target_item_id: str
    affecting_item_name: str
    affecting_item_id: str
    q_target_base: int
    q_target_scenario: int
    p_affecting_base: float
    p_affecting_scenario: float
    percentage_change_p_affecting: float
    xed_value: Optional[float] # Can be None or math.inf

class XEDResponseData(BaseModel):
    type: str = "XED"
    data: XEDResponseDataDetail

# Generic error model
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
