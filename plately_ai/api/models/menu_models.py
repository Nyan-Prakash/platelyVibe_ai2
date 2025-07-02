# plately_ai/api/models/menu_models.py

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Optional, Dict, Any

# --- Menu Psychology Tool (`/menu-psychology`) ---

class MenuPsychologyItem(BaseModel):
    id: Optional[str] = None
    name: str
    price: float = Field(..., ge=0) # Price can be 0
    description: Optional[str] = None
    category: Optional[str] = None
    # Allow any other fields as they might be present in uploaded JSON
    # but are not strictly used by the current analyzer
    extra_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="extraFields")

    class Config:
        extra = 'allow' # Allow extra fields not explicitly defined

class MenuPsychologyRequest(BaseModel):
    # User can provide menu data directly as a list of items
    # File upload will be handled separately by FastAPI's UploadFile,
    # and its content parsed into List[MenuPsychologyItem] in the route.
    menu_data: List[MenuPsychologyItem]


class MenuPsychologySuggestion(BaseModel):
    principle: str
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    suggestion: str

class MenuPsychologyResponse(BaseModel):
    suggestions: List[MenuPsychologySuggestion]
    # We might also return the processed menu or some summary if needed
    # processed_menu_item_count: Optional[int] = None


# --- Dish Visuals Tool (`/dish-visuals`) ---
# Request model for this will likely be handled by FastAPI's Form data parsing
# for dish_name, description, style_prompt, and UploadFile for the image.
# So, a specific Pydantic model for the multipart form might not be strictly needed here
# unless we want to group text fields.

class DishVisualsForm(BaseModel): # Used if we decide to parse form fields into a model
    dish_name: str = Field(..., min_length=1)
    description: Optional[str] = ""
    style_prompt: Optional[str] = "studio quality, appetizing, high resolution"
    # The image file will be handled as UploadFile directly in the path operation

class DishVisualsResponse(BaseModel):
    generated_image_url: Optional[HttpUrl] = None # Validate if it's a URL
    message: str
    input_dish_name: str
    input_description: Optional[str] = None
    input_style_prompt: Optional[str] = None
    image_used_for_inspiration: Optional[bool] = False # True if an image was uploaded and notionally used

# Note: If the mock generator for dish visuals always returns placeholder.com URLs,
# HttpUrl validation might fail if those aren't "real" enough.
# For now, keeping HttpUrl, can be changed to str if needed.
# Update: Placeholder.com URLs are valid HttpUrls.
# Example: "https://via.placeholder.com/512x512.png?text=Mock+Dish+Image+1" is a valid HttpUrl.
