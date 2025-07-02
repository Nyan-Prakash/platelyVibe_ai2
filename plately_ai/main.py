# plately_ai/main.py

from fastapi import FastAPI, Request, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import json

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define base path for the project
# __file__ is /app/plately_ai/main.py in Docker if project root is plately_ai
# If main.py is /app/main.py, then BASE_DIR is /app
# Assuming main.py is at the root of the copied content in /app for `python -m uvicorn main:app`
BASE_DIR = Path(__file__).resolve().parent # This will be /app if main.py is /app/main.py

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
    # Changed from .simulation to simulation - assuming 'simulation' is a top-level package/dir in PYTHONPATH
    from simulation.simulation_engine import SimulationEngine
    app.state.simulation_engine = SimulationEngine(
        menu_items=list(SAMPLE_MENU_ITEMS_MAIN),
        num_agents=100
    )
    logger.info("SimulationEngine initialized successfully.")
except ImportError:
    logger.critical("Failed to import SimulationEngine. Check PYTHONPATH and module structure.")
    app.state.simulation_engine = None
except ValueError as e: # Catching specific error from SimulationEngine init
    logger.critical(f"Error initializing SimulationEngine: {e}")
    app.state.simulation_engine = None


try:
    # Changed from .visual_generator to visual_generator
    from visual_generator.generator import DishImageGenerator
    app.state.dish_image_generator = DishImageGenerator(
        api_key=app_config.IMAGE_GENERATION_API_KEY,
        api_base_url=app_config.IMAGE_GENERATION_API_URL
    )
    logger.info("DishImageGenerator initialized.")
    if not app_config.IMAGE_GENERATION_API_KEY and not os.environ.get("USE_MOCK_IMAGE_GENERATOR"):
        logger.warning("DishImageGenerator: No API key, not in explicit mock mode. Will default to mock or error.")
    elif os.environ.get("USE_MOCK_IMAGE_GENERATOR", "false").lower() == "true":
        logger.info("DishImageGenerator is in MOCK mode via USE_MOCK_IMAGE_GENERATOR.")
except ImportError:
    logger.critical("Failed to import DishImageGenerator. Check PYTHONPATH and module structure.")
    app.state.dish_image_generator = None
except Exception as e: # Catching other init errors
    logger.critical(f"Error initializing DishImageGenerator: {e}")
    app.state.dish_image_generator = None

# --- Static files and Templates ---
# Path to the old 'app' directory structure which contains 'static' and 'templates'
# This is relative to where main.py is. If main.py is at /app/main.py,
# and templates are in /app/app/templates:
# static_dir = BASE_DIR / "app" / "static"
# templates_dir = BASE_DIR / "app" / "templates"
# This assumes 'app' is a subdirectory containing static/templates, relative to main.py's location.
# If your project root (the one mapped to /app in Docker) has:
# /main.py
# /app/templates/
# /app/static/
# Then BASE_DIR is the project root, and flask_app_dir should be BASE_DIR / "app"
# If main.py is inside a plately_ai package like /plately_ai/main.py and this plately_ai is project root:
# BASE_DIR would be /app/plately_ai. Then templates_dir = BASE_DIR.parent / "app" / "templates"

# Let's assume the structure copied to /app is:
# /app/main.py
# /app/api/
# /app/simulation/
# /app/app/templates/  <-- templates are here
# /app/app/static/    <-- static files are here

# Based on `flask_app_dir = BASE_DIR / "app"` from previous version of main.py and that main.py was in `plately_ai` package.
# If main.py is now at the root of /app, then BASE_DIR is /app.
# The templates and static files are in a subfolder named "app" (e.g. /app/app/templates)
# This seems like the most likely structure if `plately_ai` was the old project root package.
# And now the content of `plately_ai` is copied to `/app`.
# So, main.py is at `/app/main.py`.
# The old Flask app's "app" folder (`plately_ai/app/`) is now at `/app/app/`.

app_subfolder_for_flask_structure = BASE_DIR / "app"

if (app_subfolder_for_flask_structure / "static").exists():
    app.mount("/static", StaticFiles(directory=app_subfolder_for_flask_structure / "static"), name="static")
    logger.info(f"Mounted static files from {app_subfolder_for_flask_structure / 'static'}")
else:
    logger.warning(f"Static directory not found at {app_subfolder_for_flask_structure / 'static'}. Static files may not be served.")


if (app_subfolder_for_flask_structure / "templates").exists():
    templates = Jinja2Templates(directory=app_subfolder_for_flask_structure / "templates")
    app.state.templates = templates
    logger.info(f"Jinja2Templates configured for directory: {app_subfolder_for_flask_structure / 'templates'}")
else:
    logger.warning(f"Templates directory not found at {app_subfolder_for_flask_structure / 'templates'}. HTML pages will not work.")
    app.state.templates = None


# --- Upload Folder Configuration ---
# UPLOAD_FOLDER_NAME_MAIN = "uploads_data" # This was in old main.py, not used by FastAPI directly
# upload_dir = BASE_DIR / "instance" / UPLOAD_FOLDER_NAME_MAIN # old main.py had this outside `plately_ai` package
# For FastAPI, if main.py is /app/main.py, then BASE_DIR is /app.
# We want uploads in /app/instance/uploads_data
instance_dir = BASE_DIR / "instance"
upload_dir_path = instance_dir / "uploads_data"

if not upload_dir_path.exists():
    try:
        upload_dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory created at: {upload_dir_path}")
    except Exception as e:
        logger.error(f"Error creating upload directory {upload_dir_path}: {e}")
app.state.upload_folder = str(upload_dir_path)


# --- API Routers ---
# Changed from plately_ai.api.routers to api.routers
try:
    from api.routers import simulation_api, menu_analysis_api, pages_router
    app.include_router(simulation_api.router, prefix="/api/v1", tags=["Simulation & Elasticity"])
    app.include_router(menu_analysis_api.router, prefix="/api/v1", tags=["Menu Analysis & Visuals"])
    app.include_router(pages_router.router, tags=["Pages"]) # Page serving router
    logger.info("API and Page routers included successfully.")
except ImportError as e:
    logger.critical(f"Failed to import routers: {e}. Check PYTHONPATH and module structure. 'api' should be a directory at the same level as main.py (e.g. /app/api and /app/main.py)")


if __name__ == "__main__":
    import uvicorn
    # Uvicorn needs to be able to find 'main:app'.
    # If main.py is at /app/main.py, this command is run from /app.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # Added reload for local dev convenience. Docker CMD should not use reload for prod.
