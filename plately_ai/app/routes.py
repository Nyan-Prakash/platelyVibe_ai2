# plately_ai/app/routes.py

from flask import render_template, request, jsonify, current_app, flash, url_for, redirect
import os
import json
from werkzeug.utils import secure_filename

# Assuming these are importable from the plately_ai package root
# (e.g., plately_ai/simulation, plately_ai/menu_psychology)
# If 'app' is a blueprint, these might need adjustment (e.g. from ..simulation import)
# For now, assuming a simple app structure where 'plately_ai' is in PYTHONPATH.
from simulation.simulation_engine import SimulationEngine
from menu_psychology.analyzer import MenuPsychologyAnalyzer
from visual_generator.generator import DishImageGenerator


# --- Helper for file uploads (similar to what was in FastAPI version) ---
UPLOAD_FOLDER_NAME_ROUTES = 'uploads_data' # Should match what's in app/__init__.py app.config['UPLOAD_FOLDER']
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg'}
ALLOWED_EXTENSIONS_JSON = {'json'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


# --- Page Serving Routes & API-like endpoints ---

@current_app.route('/', methods=['GET'])
def index():
    """
    Main pricing dashboard page.
    """
    sim_engine = current_app.simulation_engine
    if not sim_engine:
        flash("Pricing simulation engine is not available. Please check configuration.", "error")
        return render_template('index.html', menu_items=[], simulation_engine_error=True)

    menu_for_display = sim_engine.menu_items_master_list
    return render_template('index.html', menu_items=menu_for_display, simulation_engine_error=False)


@current_app.route('/simulate', methods=['POST'])
def simulate_price_change_flask():
    """
    Handles price simulation requests from the main dashboard.
    This was previously /api/v1/simulate in FastAPI.
    """
    sim_engine = current_app.simulation_engine
    if not sim_engine:
        return jsonify({"error": "Simulation engine not available."}), 503

    req_data = request.get_json()
    if not req_data or 'item_id' not in req_data or 'new_price' not in req_data:
        return jsonify({"error": "Invalid request. Missing 'item_id' or 'new_price'."}), 400

    item_id_to_change = req_data['item_id']
    try:
        new_price = float(req_data['new_price'])
        if new_price < 0:
            return jsonify({"error": "Price cannot be negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid price format. Price must be a non-negative number."}), 400

    original_menu = sim_engine.menu_items_master_list

    sim_engine.reset_menu_to_master()
    baseline_choices = sim_engine.run_simulation_step()
    baseline_results = sim_engine.analyze_results(baseline_choices)

    scenario_results = sim_engine.run_price_scenario(item_id_to_change, new_price)

    if scenario_results is None:
        item_exists = any(item['id'] == item_id_to_change for item in original_menu)
        if not item_exists:
            return jsonify({"error": f"Item with ID '{item_id_to_change}' not found."}), 404
        return jsonify({"error": f"Failed to run scenario for item {item_id_to_change}. Price might be invalid."}), 400

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
            "name": name, "original_price": current_original_price, "scenario_price": scenario_price_val,
            "baseline_demand": baseline_results["demand_per_item"].get(name, 0),
            "scenario_demand": scenario_results["demand_per_item"].get(name, 0),
            "baseline_revenue": baseline_results["revenue_per_item"].get(name, 0),
            "scenario_revenue": scenario_results["revenue_per_item"].get(name, 0)
        })

    elasticities = {}
    if original_changed_item_price is not None and original_changed_item_price > 0 and new_price != original_changed_item_price:
        percentage_change_price_changed_item = (new_price - original_changed_item_price) / original_changed_item_price
        if percentage_change_price_changed_item != 0:
            for item_data in comparison_data:
                if item_data['name'] == changed_item_name: continue
                q1, q2 = item_data['baseline_demand'], item_data['scenario_demand']
                if q1 > 0:
                    elasticities[item_data['name']] = round(((q2 - q1) / q1) / percentage_change_price_changed_item, 3)
                elif q2 > 0 :
                     elasticities[item_data['name']] = "Inf (New Demand)"
                else:
                    elasticities[item_data['name']] = 0.0

    return jsonify({
        "message": f"Simulation complete for {changed_item_name} at ${new_price:.2f}",
        "baseline_total_revenue": baseline_results["total_revenue"],
        "scenario_total_revenue": scenario_results["total_revenue"],
        "comparison_table": comparison_data,
        "cross_price_elasticities_with_changed_item": elasticities,
        "changed_item_id": item_id_to_change,
        "new_price_for_changed_item": new_price
    })


@current_app.route('/calculate-elasticities', methods=['POST'])
def calculate_elasticities_flask():
    """
    Handles elasticity calculations.
    This was previously /api/v1/calculate-elasticities in FastAPI.
    """
    sim_engine = current_app.simulation_engine
    if not sim_engine:
        return jsonify({"error": "Simulation engine not available."}), 503

    from simulation.elasticity_calculator import (
        calculate_ped_from_simulation_data,
        calculate_xed_from_simulation_data
    )

    req_data = request.get_json()
    if not req_data or 'type' not in req_data:
        return jsonify({"error": "Missing 'type' (PED or XED) in request."}), 400

    elasticity_type = req_data['type'].upper()
    results = None
    error_message = None

    if elasticity_type == 'PED':
        item_id_vary = req_data.get('item_id_vary')
        ped_price_changes_str = req_data.get('ped_price_changes', "-0.2,-0.1,0.1,0.2")
        try:
            ped_price_changes = [float(x.strip()) for x in ped_price_changes_str.split(',')]
            if not ped_price_changes or not all(-1 < x < 10 for x in ped_price_changes):
                 raise ValueError("Percentage changes for PED should be reasonable (e.g., >-1, <10) and list not empty.")
        except ValueError as e:
            return jsonify({"error": f"Invalid format for PED price changes: {e}. Expect comma-separated numbers."}), 400

        if not item_id_vary:
            error_message = "Missing 'item_id_vary' for PED calculation."
        else:
            sim_data = sim_engine.run_ped_simulation_set(item_id_vary, ped_price_changes)
            if sim_data:
                ped_results = calculate_ped_from_simulation_data(sim_data)
                item_info = next((item for item in sim_engine.menu_items_master_list if item['id'] == item_id_vary), None)
                item_name = item_info['name'] if item_info else item_id_vary
                results = {"type": "PED", "item_name": item_name, "item_id":item_id_vary, "data": ped_results}
            else:
                error_message = f"Could not generate simulation data for PED of item {item_id_vary}."

    elif elasticity_type == 'XED':
        target_item_id = req_data.get('target_item_id')
        affecting_item_id = req_data.get('affecting_item_id')
        xed_price_change_str = req_data.get('xed_price_change', "0.1")
        try:
            xed_price_change = float(xed_price_change_str)
            if not (-1 < xed_price_change < 10):
                raise ValueError("Percentage change for XED should be reasonable.")
        except ValueError:
            return jsonify({"error": "Invalid format for XED price change. Expect a single number."}), 400

        if not target_item_id or not affecting_item_id:
            error_message = "Missing 'target_item_id' or 'affecting_item_id' for XED."
        elif target_item_id == affecting_item_id:
            error_message = "Target and affecting items cannot be the same for XED."
        else:
            sim_data = sim_engine.run_xed_simulation_set(target_item_id, affecting_item_id, xed_price_change)
            if sim_data:
                xed_result = calculate_xed_from_simulation_data(sim_data)
                results = {"type": "XED", "data": xed_result}
            else:
                error_message = f"Could not generate simulation data for XED between {target_item_id} and {affecting_item_id}."
    else:
        error_message = f"Invalid elasticity type: {elasticity_type}. Must be 'PED' or 'XED'."

    if error_message:
        return jsonify({"error": error_message}), 400 if "Missing" in error_message or "Invalid" in error_message else 500

    return jsonify(results)


@current_app.route('/menu-psychology', methods=['GET', 'POST'])
def menu_psychology_tool_flask():
    """
    Page for menu psychology analysis. Form submits to itself.
    """
    suggestions = None
    submitted_json_text = None

    if request.method == 'POST':
        menu_data_json_str = request.form.get('menu_data_json')
        menu_file = request.files.get('menu_file')
        parsed_menu_data = None

        submitted_json_text = menu_data_json_str # For re-populating textarea

        if menu_file and menu_file.filename and allowed_file(menu_file.filename, ALLOWED_EXTENSIONS_JSON):
            try:
                json_string = menu_file.read().decode('utf-8')
                parsed_menu_data = json.loads(json_string)
                submitted_json_text = json_string # Show uploaded content if successfully parsed
                flash(f"Menu file '{secure_filename(menu_file.filename)}' processed.", "success")
            except json.JSONDecodeError:
                flash("Invalid JSON in uploaded file.", "error")
            except Exception as e:
                flash(f"Error processing file: {str(e)}", "error")
        elif menu_data_json_str:
            try:
                parsed_menu_data = json.loads(menu_data_json_str)
                flash("Pasted JSON data processed.", "success")
            except json.JSONDecodeError:
                flash("Invalid JSON data in text area.", "error")
        else:
            flash("No menu data provided.", "warning")

        if parsed_menu_data:
            if not isinstance(parsed_menu_data, list) or \
               not all(isinstance(item, dict) and 'name' in item and 'price' in item for item in parsed_menu_data):
                flash("Invalid menu data structure. List of items with 'name' and 'price' expected.", "error")
            else:
                analyzer = MenuPsychologyAnalyzer(parsed_menu_data)
                suggestions = analyzer.analyze()

    return render_template('menu_psychology.html', suggestions=suggestions, submitted_json=submitted_json_text)


@current_app.route('/dish-visuals', methods=['GET', 'POST'])
def dish_visuals_tool_flask():
    """
    Page for AI-powered dish visual generation. Form submits to itself.
    """
    context = {
        "generated_image_url": None,
        "submitted_dish_name": None, "submitted_description": None, "submitted_style_prompt": None
    }
    img_generator = current_app.dish_image_generator

    if request.method == 'POST':
        dish_name = request.form.get('dish_name')
        description = request.form.get('description', "")
        style_prompt = request.form.get('style_prompt', "studio quality, appetizing, high resolution")
        uploaded_image_file = request.files.get('dish_image')

        context.update({
            "submitted_dish_name": dish_name,
            "submitted_description": description,
            "submitted_style_prompt": style_prompt
        })

        if not dish_name:
            flash("Dish name is required.", "error")
        elif not img_generator:
            flash("Dish image generator is not available.", "error")
        else:
            saved_image_path = None
            try:
                if uploaded_image_file and uploaded_image_file.filename and allowed_file(uploaded_image_file.filename, ALLOWED_EXTENSIONS_IMAGES):
                    filename = secure_filename(uploaded_image_file.filename)
                    # Ensure UPLOAD_FOLDER is correctly configured on app
                    upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads') # Fallback just in case
                    if not os.path.exists(upload_folder): os.makedirs(upload_folder, exist_ok=True)
                    saved_image_path = os.path.join(upload_folder, filename)
                    uploaded_image_file.save(saved_image_path)
                    flash(f"Image '{filename}' uploaded.", "info")

                generated_url = img_generator.generate_image_from_prompt(
                    dish_name, description, style_prompt, existing_image_path=saved_image_path
                )

                if generated_url:
                    context["generated_image_url"] = generated_url
                    flash("Dish visual generated (mock)!", "success")
                else:
                    flash("Failed to generate dish visual.", "warning")

                # Clean up uploaded file if temporary (optional)
                # if saved_image_path and os.path.exists(saved_image_path):
                #     os.remove(saved_image_path)
            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")
                current_app.logger.error(f"Error in dish visuals: {e}")

    return render_template('dish_visuals.html', **context)
