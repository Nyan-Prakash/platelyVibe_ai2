# plately_ai/main.py

from fastapi import FastAPI, Request, HTTPException, UploadFile # Added UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import json # Added for /menu-psychology POST in main, if needed (though logic moved)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define base path for the project
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Plately AI")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- App Configuration ---
class AppConfig:
    IMAGE_GENERATION_API_KEY = os.environ.get("IMAGE_GENERATION_API_KEY")
    IMAGE_GENERATION_API_URL = os.environ.get("IMAGE_GENERATION_API_URL")

app_config = AppConfig()

# --- Service Initialization ---
SAMPLE_MENU_ITEMS_MAIN = [
    {'id': 'burger_classic', 'name': 'Classic Burger', 'price': 12.00},
    {'id': 'pizza_pepperoni', 'name': 'Pepperoni Pizza', 'price': 15.00},
    {'id': 'salad_caesar', 'name': 'Caesar Salad', 'price': 10.00},
    {'id': 'pasta_carbonara', 'name': 'Carbonara Pasta', 'price': 14.00},
    {'id': 'coke_soda', 'name': 'Coke', 'price': 2.50}
]

try:
    from .simulation.simulation_engine import SimulationEngine
    app.state.simulation_engine = SimulationEngine(
        menu_items=list(SAMPLE_MENU_ITEMS_MAIN),
        num_agents=100
    )
    logger.info("SimulationEngine initialized successfully.")
except ValueError as e:
    logger.critical(f"Error initializing SimulationEngine: {e}")
    app.state.simulation_engine = None

try:
    from .visual_generator.generator import DishImageGenerator
    app.state.dish_image_generator = DishImageGenerator(
        api_key=app_config.IMAGE_GENERATION_API_KEY,
        api_base_url=app_config.IMAGE_GENERATION_API_URL
    )
    logger.info("DishImageGenerator initialized.")
    if not app_config.IMAGE_GENERATION_API_KEY and not os.environ.get("USE_MOCK_IMAGE_GENERATOR"):
        logger.warning("DishImageGenerator: No API key, not in explicit mock mode. Will default to mock or error.")
    elif os.environ.get("USE_MOCK_IMAGE_GENERATOR", "false").lower() == "true":
        logger.info("DishImageGenerator is in MOCK mode via USE_MOCK_IMAGE_GENERATOR.")
except Exception as e:
    logger.critical(f"Error initializing DishImageGenerator: {e}")
    app.state.dish_image_generator = None

# --- Static files and Templates ---
# Path to the old 'app' directory which contains 'static' and 'templates'
# This structure is kept from the Flask app for template/static locations.
flask_app_dir = BASE_DIR / "app"

if (flask_app_dir / "static").exists():
    app.mount("/static", StaticFiles(directory=flask_app_dir / "static"), name="static")
    logger.info(f"Mounted static files from {flask_app_dir / 'static'}")
else:
    logger.warning(f"Static directory not found at {flask_app_dir / 'static'}. Static files may not be served.")


if (flask_app_dir / "templates").exists():
    templates = Jinja2Templates(directory=flask_app_dir / "templates")
    app.state.templates = templates # Make templates accessible via app.state
    logger.info(f"Jinja2Templates configured for directory: {flask_app_dir / 'templates'}")
else:
    logger.warning(f"Templates directory not found at {flask_app_dir / 'templates'}. HTML pages will not work.")
    app.state.templates = None


# --- Upload Folder Configuration ---
UPLOAD_FOLDER_NAME_MAIN = "uploads_data"
upload_dir = BASE_DIR / "instance" / UPLOAD_FOLDER_NAME_MAIN
if not upload_dir.exists():
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory created at: {upload_dir}")
    except Exception as e:
        logger.error(f"Error creating upload directory {upload_dir}: {e}")
app.state.upload_folder = str(upload_dir)


# --- API Routers ---
from plately_ai.api.routers import simulation_api, menu_analysis_api, pages_router

app.include_router(simulation_api.router, prefix="/api/v1", tags=["Simulation & Elasticity"])
app.include_router(menu_analysis_api.router, prefix="/api/v1", tags=["Menu Analysis & Visuals"])

# --- Page Serving Router ---
# This router now handles GET and POST for the HTML pages.
app.include_router(pages_router.router, tags=["Pages"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
