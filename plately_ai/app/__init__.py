# plately_ai/app/__init__.py
import os
from flask import Flask

# Placeholder initializations for services used in routes
# In a real app, these would be properly initialized and configured.
class MockSimulationEngine:
    def __init__(self):
        self.menu_items_master_list = [{"id": "item1", "name": "Placeholder Item", "price": 10.0}]
    def reset_menu_to_master(self): pass
    def run_simulation_step(self): return {}
    def analyze_results(self, choices): return {"total_revenue": 0, "demand_per_item": {}, "revenue_per_item": {}}
    def run_price_scenario(self, item_id, new_price): return {"total_revenue": 0, "demand_per_item": {}, "revenue_per_item": {}}
    def run_ped_simulation_set(self, item_id, changes): return []
    def run_xed_simulation_set(self, target_id, affecting_id, change): return []

class MockDishImageGenerator:
    def generate_image_from_prompt(self, dish_name, description, style_prompt, existing_image_path=None):
        # In a real scenario, this would call an image generation API or model
        print(f"Mock generating image for: {dish_name} - {description} - {style_prompt}")
        if existing_image_path:
            print(f"With existing image: {existing_image_path}")
        return "static/placeholder_dish_image.png" # Return a path to a placeholder or a mock URL

def create_app(config_name=None):
    """
    Application factory function.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Configuration setup
    # app.config.from_object('config.default') # Example: load default config
    # app.config.from_pyfile('config.py', silent=True) # Example: load instance config
    # Or load directly:
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'your_default_secret_key'),
        UPLOAD_FOLDER=os.path.join(app.root_path, '..', 'uploads_data'), # Path relative to plately_ai/app
        # Add other configurations as needed
    )

    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions or services and attach to app context
    # These would be real initializations in a full application
    app.simulation_engine = MockSimulationEngine()
    app.dish_image_generator = MockDishImageGenerator()
    # Example for a database:
    # from .extensions import db
    # db.init_app(app)

    # Register blueprints
    from .routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # Example: Register another blueprint
    # from .auth import bp as auth_blueprint
    # app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # Add a simple health check route
    @app.route('/health')
    def health():
        return "OK"

    return app
