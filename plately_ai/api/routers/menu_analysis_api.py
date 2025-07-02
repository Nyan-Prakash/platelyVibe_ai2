# plately_ai/api/routers/menu_analysis_api.py

from fastapi import APIRouter, HTTPException, Request, Depends, File, UploadFile, Form
from typing import List, Optional
import json
import os
from werkzeug.utils import secure_filename # Still useful for filename sanitization

from plately_ai.api.models.menu_models import (
    MenuPsychologyItem, MenuPsychologyResponse, MenuPsychologySuggestion,
    DishVisualsResponse
)
from plately_ai.menu_psychology.analyzer import MenuPsychologyAnalyzer
from plately_ai.visual_generator.generator import DishImageGenerator

router = APIRouter()

# --- Helper for services ---
def get_dish_image_generator(request: Request) -> DishImageGenerator:
    generator = request.app.state.dish_image_generator
    if not generator:
        raise HTTPException(status_code=503, detail="Dish image generator is not available.")
    return generator

def get_upload_folder(request: Request) -> str:
    folder = request.app.state.upload_folder
    if not folder or not os.path.exists(folder): # Ensure it was created
        # This should ideally be handled at app startup, but as a fallback:
        os.makedirs(folder, exist_ok=True)
        # raise HTTPException(status_code=500, detail="Upload folder not configured or does not exist.")
    return folder


# --- Allowed File Check (similar to Flask) ---
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg'}
ALLOWED_EXTENSIONS_JSON = {'json'}

def allowed_image_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMAGES

def allowed_json_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_JSON


# --- Endpoints ---

# Helper function to encapsulate menu psychology analysis logic
async def _perform_menu_psychology_analysis(
    menu_data_json_str: Optional[str],
    menu_file: Optional[UploadFile]
) -> List[Dict[str, Any]]: # Returns list of suggestion dicts
    parsed_menu_data: Optional[List[Dict]] = None

    if menu_file and menu_file.filename:
        if not allowed_json_file(menu_file.filename):
            raise HTTPException(status_code=400, detail="Invalid file type for menu. Please upload a JSON file.")
        try:
            contents = await menu_file.read()
            parsed_menu_data = json.loads(contents.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in uploaded file. Please check the file format.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing uploaded file: {str(e)}")
        finally:
            if menu_file: # Ensure it's checked because it's Optional
                await menu_file.close()
    elif menu_data_json_str:
        try:
            parsed_menu_data = json.loads(menu_data_json_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data provided in text area. Please check the format.")
    else:
        raise HTTPException(status_code=400, detail="No menu data provided. Please paste JSON or upload a file.")

    if not parsed_menu_data:
        raise HTTPException(status_code=400, detail="Menu data could not be parsed.")

    validated_menu_items: List[MenuPsychologyItem] = []
    if not isinstance(parsed_menu_data, list):
        raise HTTPException(status_code=400, detail="Invalid menu data structure: root must be a list.")

    for i, item_dict in enumerate(parsed_menu_data):
        try:
            item_model = MenuPsychologyItem(**item_dict)
            validated_menu_items.append(item_model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid data for menu item at index {i}: {str(e)}")

    menu_for_analyzer = [item.model_dump(by_alias=True) for item in validated_menu_items]
    analyzer = MenuPsychologyAnalyzer(menu_for_analyzer)
    return analyzer.analyze() # This returns list of dicts


@router.post(
    "/menu-psychology/analyze",
    response_model=MenuPsychologyResponse,
    summary="Analyzes menu data for psychological insights via API."
)
async def analyze_menu_psychology_api(
    menu_data_json_str: Optional[str] = Form(None, alias="menu_data_json"),
    menu_file: Optional[UploadFile] = File(None, alias="menu_file")
):
    suggestions_dict_list = await _perform_menu_psychology_analysis(menu_data_json_str, menu_file)
    pydantic_suggestions = [MenuPsychologySuggestion(**sug) for sug in suggestions_dict_list]
    return MenuPsychologyResponse(suggestions=pydantic_suggestions)


# Helper function for dish visual generation logic
async def _generate_dish_visual_logic(
    dish_name: str,
    description: Optional[str],
    style_prompt: Optional[str],
    dish_image: Optional[UploadFile],
    image_generator: DishImageGenerator,
    upload_folder: str
) -> Dict[str, Any]: # Returns dict suitable for DishVisualsResponse
    generated_image_url_str: Optional[str] = None
    image_used_for_inspiration = False
    saved_image_path_for_generator: Optional[str] = None

    if dish_image and dish_image.filename:
        if not allowed_image_file(dish_image.filename):
            raise HTTPException(status_code=400, detail="Invalid image file type. Allowed: png, jpg, jpeg.")

        filename = secure_filename(dish_image.filename)
        saved_image_path = os.path.join(upload_folder, filename)

        try:
            with open(saved_image_path, "wb") as buffer:
                buffer.write(await dish_image.read())
            image_used_for_inspiration = True
            saved_image_path_for_generator = saved_image_path # Pass this to generator
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded image: {str(e)}")
        finally:
            await dish_image.close()

    # Call the generator
    generated_image_url_str = image_generator.generate_image_from_prompt(
        dish_name, description or "", style_prompt or "studio quality, appetizing, high resolution",
        existing_image_path=saved_image_path_for_generator
    )

    # Clean up if needed (decided to keep files for simplicity in earlier step)
    # if saved_image_path_for_generator and os.path.exists(saved_image_path_for_generator):
    #     os.remove(saved_image_path_for_generator)

    message = "Dish visual generated successfully (using MOCK)!" if generated_image_url_str else "Failed to generate dish visual."
    if generated_image_url_str and "placeholder.com" not in generated_image_url_str and image_generator.api_key:
        message = "Dish visual generated successfully!"

    return {
        "generated_image_url": generated_image_url_str,
        "message": message,
        "input_dish_name": dish_name,
        "input_description": description,
        "input_style_prompt": style_prompt,
        "image_used_for_inspiration": image_used_for_inspiration
    }


@router.post(
    "/dish-visuals/generate",
    response_model=DishVisualsResponse,
    summary="Generates a dish visual via API."
)
async def generate_dish_visual_api(
    dish_name: str = Form(...),
    description: Optional[str] = Form(""),
    style_prompt: Optional[str] = Form("studio quality, appetizing, high resolution"),
    dish_image: Optional[UploadFile] = File(None),
    image_generator: DishImageGenerator = Depends(get_dish_image_generator),
    upload_folder: str = Depends(get_upload_folder)
):
    result_data = await _generate_dish_visual_logic(
        dish_name, description, style_prompt, dish_image, image_generator, upload_folder
    )
    return DishVisualsResponse(**result_data)
