# plately_ai/tests/test_api_endpoints.py

import unittest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import io # For creating in-memory file for uploads

# Adjust the import path based on your project structure.
# If 'plately_ai' is the root package recognised by pytest/unittest discovery:
from plately_ai.main import app # Import the FastAPI app instance

# If running tests from the project root, Python might need plately_ai in its path.
# This can be handled by PYTHONPATH or how the test runner is invoked.
# For example, if project root is `.../PlatelyAI/` and tests are in `.../PlatelyAI/plately_ai/tests/`,
# and main app is in `.../PlatelyAI/plately_ai/main.py`.
# Running `python -m unittest discover plately_ai/tests` from `PlatelyAI` root should work.

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Ensure the upload directory exists for tests that might write files,
        # though TestClient might not always hit the physical disk for UploadFile mocks.
        # The app startup in main.py should create `instance/uploads_data`.
        # We can also override app.state.upload_folder for tests if needed.
        # For now, assume main.py's startup logic handles it.

        # Sample menu data for convenience
        cls.sample_menu_item_data = [
            {'id': 'burger_classic', 'name': 'Classic Burger', 'price': 12.00},
            {'id': 'pizza_pepperoni', 'name': 'Pepperoni Pizza', 'price': 15.00},
        ]
        # app.state.simulation_engine is initialized with sample data in main.py,
        # so we can use those item IDs.

    def test_root_page_get(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers['content-type'])
        self.assertIn("Interactive Pricing Dashboard", response.text)

    def test_simulate_price_change_api(self):
        payload = {"item_id": "burger_classic", "new_price": 13.50}
        response = self.client.post("/api/v1/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['changed_item_id'], "burger_classic")
        self.assertAlmostEqual(data['new_price_for_changed_item'], 13.50)
        self.assertIn("comparison_table", data)
        self.assertTrue(len(data['comparison_table']) > 0)

    def test_simulate_price_change_api_invalid_item(self):
        payload = {"item_id": "non_existent_item", "new_price": 10.00}
        response = self.client.post("/api/v1/simulate", json=payload)
        self.assertEqual(response.status_code, 404) # As per simulation_api.py logic
        self.assertIn("not found", response.json()['detail'].lower())

    def test_simulate_price_change_api_invalid_price(self):
        payload = {"item_id": "burger_classic", "new_price": -5.00} # Pydantic model ge=0
        response = self.client.post("/api/v1/simulate", json=payload)
        self.assertEqual(response.status_code, 422) # Unprocessable Entity due to Pydantic validation
        # Check for detail in response if needed, it's a list of errors from Pydantic

    def test_calculate_ped_api(self):
        payload = {
            "type": "PED",
            "item_id_vary": "burger_classic",
            "ped_price_changes": "-0.1,0.1,0.25"
        }
        response = self.client.post("/api/v1/calculate-elasticities", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], "PED")
        self.assertEqual(data['item_id'], "burger_classic")
        self.assertTrue(len(data['data']) == 4) # Baseline + 3 changes
        self.assertIn('ped_value', data['data'][1]) # Check one of the scenario points

    def test_calculate_ped_api_invalid_format(self):
        payload = {
            "type": "PED",
            "item_id_vary": "burger_classic",
            "ped_price_changes": "invalid-string"
        }
        response = self.client.post("/api/v1/calculate-elasticities", json=payload)
        self.assertEqual(response.status_code, 400) # Custom validation in route
        self.assertIn("Invalid format for PED price changes", response.json()['detail'])

    def test_calculate_xed_api(self):
        payload = {
            "type": "XED",
            "target_item_id": "pizza_pepperoni",
            "affecting_item_id": "burger_classic",
            "xed_price_change": "0.15"
        }
        response = self.client.post("/api/v1/calculate-elasticities", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], "XED")
        self.assertEqual(data['data']['target_item_id'], "pizza_pepperoni")
        self.assertEqual(data['data']['affecting_item_id'], "burger_classic")
        self.assertIn('xed_value', data['data'])

    def test_calculate_xed_api_same_item(self):
        payload = {
            "type": "XED",
            "target_item_id": "burger_classic",
            "affecting_item_id": "burger_classic",
            "xed_price_change": "0.1"
        }
        response = self.client.post("/api/v1/calculate-elasticities", json=payload)
        self.assertEqual(response.status_code, 400) # As per logic in simulation_api.py
        self.assertIn("cannot be the same", response.json()['detail'].lower())


    def test_menu_psychology_analyze_api_json_input(self):
        menu_data = [{"name": "Test Item", "price": 9.99, "description": "A test description."}]
        # FastAPI TestClient expects form data for `Form` fields.
        # The endpoint /api/v1/menu-psychology/analyze uses Form for menu_data_json_str
        response = self.client.post(
            "/api/v1/menu-psychology/analyze",
            data={"menu_data_json": json.dumps(menu_data)} # Send as form data
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggestions", data)
        self.assertTrue(len(data['suggestions']) > 0) # Expect some suggestions

    def test_menu_psychology_analyze_api_file_upload(self):
        menu_data = [{"name": "File Item", "price": 19.95, "category": "Mains"}]
        json_bytes = io.BytesIO(json.dumps(menu_data).encode('utf-8'))

        response = self.client.post(
            "/api/v1/menu-psychology/analyze",
            files={"menu_file": ("test_menu.json", json_bytes, "application/json")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggestions", data)
        self.assertTrue(len(data['suggestions']) > 0)
        # Example: check for a specific suggestion if predictable
        # found_price_format_sug = any(sug['principle'] == "Price Formatting (Charming Prices)" and sug['item_name'] == "File Item" for sug in data['suggestions'])
        # self.assertTrue(found_price_format_sug)


    def test_dish_visuals_generate_api_text_only(self):
        response = self.client.post(
            "/api/v1/dish-visuals/generate",
            data={
                "dish_name": "Test Visual Dish",
                "description": "A delicious dish from test.",
                "style_prompt": "photorealistic"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("generated_image_url", data)
        self.assertTrue(data['generated_image_url'].startswith("https://via.placeholder.com")) # Mock URL
        self.assertEqual(data['input_dish_name'], "Test Visual Dish")

    def test_dish_visuals_generate_api_with_image_upload(self):
        # Create a dummy image file in memory
        image_bytes = io.BytesIO(b"fakeimagedata") # Content doesn't matter for mock generator

        response = self.client.post(
            "/api/v1/dish-visuals/generate",
            data={
                "dish_name": "Uploaded Visual Dish",
                "description": "Dish with an uploaded image.",
                "style_prompt": "enhance quality"
            },
            files={"dish_image": ("test_image.jpg", image_bytes, "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("generated_image_url", data)
        self.assertTrue(data['generated_image_url'].startswith("https://via.placeholder.com"))
        self.assertEqual(data['input_dish_name'], "Uploaded Visual Dish")
        self.assertTrue(data['image_used_for_inspiration'])


    # Test HTML page routes (basic check that they load)
    def test_menu_psychology_page_get(self):
        response = self.client.get("/menu-psychology")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers['content-type'])

    def test_dish_visuals_page_get(self):
        response = self.client.get("/dish-visuals")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers['content-type'])


if __name__ == "__main__":
    unittest.main()
