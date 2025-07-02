# plately_ai/api/routers/pages_router.py

from fastapi import APIRouter, Request, HTTPException, UploadFile
from fastapi.templating import Jinja2Templates # Will get this from app.state
import logging
import os # For os.path.exists
import json # For json.dumps in menu_psychology if we decide to re-populate from file

logger = logging.getLogger(__name__)
router = APIRouter()

# Note: The Jinja2Templates instance and SimulationEngine are expected to be on `request.app.state`.

@router.get("/", include_in_schema=False)
async def serve_pricing_dashboard_page(request: Request):
    """Serves the main pricing dashboard page (index.html)."""
    templates = request.app.state.templates
    if not templates:
        logger.error("Templates not configured for / route.")
        raise HTTPException(status_code=500, detail="Internal server error: Templates not configured.")

    simulation_engine = request.app.state.simulation_engine
    simulation_engine_error = not simulation_engine
    menu_items_list = simulation_engine.menu_items_master_list if simulation_engine else []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "menu_items": menu_items_list,
        "simulation_results": None,
        "simulation_engine_error": simulation_engine_error
    })

@router.get("/menu-psychology", include_in_schema=False)
@router.post("/menu-psychology", include_in_schema=False) # Keep POST here for form submission to the page
async def serve_menu_psychology_page(request: Request):
    """Serves the menu psychology tool page and handles its form submission."""
    templates = request.app.state.templates
    if not templates:
        logger.error("Templates not configured for /menu-psychology route.")
        raise HTTPException(status_code=500, detail="Internal server error: Templates not configured.")

    context = {
        "request": request,
        "suggestions": None,
        "submitted_json": None,
        "error_detail": None
    }

    if request.method == "POST":
        form_data = await request.form()
        menu_data_json_str = form_data.get("menu_data_json")
        menu_file = form_data.get("menu_file")

        if isinstance(menu_file, UploadFile) and not menu_file.filename: # type: ignore
            menu_file = None

        suggestions_dict_list = []
        context["submitted_json"] = menu_data_json_str

        try:
            from plately_ai.api.routers.menu_analysis_api import _perform_menu_psychology_analysis, MenuPsychologySuggestion
            # Make sure UploadFile is correctly typed for _perform_menu_psychology_analysis if it expects it
            suggestions_dict_list = await _perform_menu_psychology_analysis(menu_data_json_str, menu_file) # type: ignore
            context["suggestions"] = [MenuPsychologySuggestion(**sug) for sug in suggestions_dict_list] if suggestions_dict_list else None
        except HTTPException as he:
            context["error_detail"] = he.detail
            logger.error(f"Error during menu psychology POST on page route: {he.detail}")
        except Exception as e:
            context["error_detail"] = f"An unexpected error occurred: {str(e)}"
            logger.error(f"Unexpected error during menu psychology POST on page route: {str(e)}")

    return templates.TemplateResponse("menu_psychology.html", context)


@router.get("/dish-visuals", include_in_schema=False)
@router.post("/dish-visuals", include_in_schema=False)
async def serve_dish_visuals_page(request: Request):
    """Serves the dish visuals generator page and handles its form submission."""
    templates = request.app.state.templates
    if not templates:
        logger.error("Templates not configured for /dish-visuals route.")
        raise HTTPException(status_code=500, detail="Internal server error: Templates not configured.")

    context = {
        "request": request,
        "generated_image_url": None,
        "submitted_dish_name": None,
        "submitted_description": None,
        "submitted_style_prompt": None,
        "error_detail": None
    }

    if request.method == "POST":
        form_data = await request.form()
        dish_name = form_data.get("dish_name")
        description = form_data.get("description", "")
        style_prompt = form_data.get("style_prompt", "studio quality, appetizing, high resolution")
        dish_image_upload = form_data.get("dish_image") # type: ignore

        context.update({
            "submitted_dish_name": dish_name,
            "submitted_description": description,
            "submitted_style_prompt": style_prompt
        })

        if not dish_name:
            context["error_detail"] = "Dish name is required."
        else:
            try:
                from plately_ai.api.routers.menu_analysis_api import _generate_dish_visual_logic

                image_generator = request.app.state.dish_image_generator
                upload_folder_path = request.app.state.upload_folder

                if not image_generator:
                     raise HTTPException(status_code=503, detail="Dish image generator service is not available.")
                if not upload_folder_path or not os.path.exists(upload_folder_path): # type: ignore
                    raise HTTPException(status_code=500, detail="Upload folder not configured or missing.")

                if isinstance(dish_image_upload, UploadFile) and not dish_image_upload.filename: # type: ignore
                    dish_image_upload = None

                result_data = await _generate_dish_visual_logic(
                    dish_name, description, style_prompt, dish_image_upload, # type: ignore
                    image_generator, upload_folder_path # type: ignore
                )
                context["generated_image_url"] = result_data.get("generated_image_url")
                if not context["generated_image_url"] and "error" not in (result_data.get("message","").lower()):
                     context["error_detail"] = result_data.get("message","Failed to generate visual.")
                elif result_data.get("message") and "error" in result_data.get("message","").lower(): # If message contains error
                     context["error_detail"] = result_data.get("message")


            except HTTPException as he:
                context["error_detail"] = he.detail
                logger.error(f"Error during dish visuals POST on page route: {he.detail}")
            except Exception as e:
                context["error_detail"] = f"An unexpected error occurred: {str(e)}"
                logger.error(f"Unexpected error during dish visuals POST on page route: {str(e)}")

    return templates.TemplateResponse("dish_visuals.html", context)
