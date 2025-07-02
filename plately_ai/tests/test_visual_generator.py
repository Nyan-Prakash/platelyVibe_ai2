# plately_ai/tests/test_visual_generator.py

import unittest
import os
from plately_ai.visual_generator.generator import DishImageGenerator

class TestDishImageGenerator(unittest.TestCase):

    def setUp(self):
        # Store original env var state
        self.original_mock_flag = os.environ.get('USE_MOCK_IMAGE_GENERATOR')
        self.original_api_key = os.environ.get('IMAGE_GENERATION_API_KEY')

    def tearDown(self):
        # Restore original env var state
        if self.original_mock_flag is None:
            if 'USE_MOCK_IMAGE_GENERATOR' in os.environ: # Check before popping
                os.environ.pop('USE_MOCK_IMAGE_GENERATOR')
        else:
            os.environ['USE_MOCK_IMAGE_GENERATOR'] = self.original_mock_flag

        if self.original_api_key is None:
            if 'IMAGE_GENERATION_API_KEY' in os.environ: # Check before popping
                os.environ.pop('IMAGE_GENERATION_API_KEY')
        else:
            os.environ['IMAGE_GENERATION_API_KEY'] = self.original_api_key

    def test_initialization_mock_mode_by_env_var(self):
        os.environ['USE_MOCK_IMAGE_GENERATOR'] = 'true'
        if 'IMAGE_GENERATION_API_KEY' in os.environ: # Ensure no API key for this test
            del os.environ['IMAGE_GENERATION_API_KEY']

        generator = DishImageGenerator() # No API key passed
        self.assertTrue(os.environ.get("USE_MOCK_IMAGE_GENERATOR", "false").lower() == "true")
        # In mock mode, even without API key, it should not raise ValueError
        try:
            url = generator.generate_image_from_prompt("Test Dish")
            self.assertIsNotNone(url) # Expect a mock URL
            self.assertTrue(any(mock_url_part in url for mock_url_part in ["placeholder.com", "picsum.photos"])) # Example check
        except ValueError:
            self.fail("DishImageGenerator raised ValueError in mock mode when it shouldn't have.")

    def test_initialization_no_api_key_and_no_mock_flag_raises_error(self):
        if 'USE_MOCK_IMAGE_GENERATOR' in os.environ:
            del os.environ['USE_MOCK_IMAGE_GENERATOR']
        if 'IMAGE_GENERATION_API_KEY' in os.environ:
            del os.environ['IMAGE_GENERATION_API_KEY']

        with self.assertRaisesRegex(ValueError, "API key for image generation service is required"):
            generator = DishImageGenerator() # No API key, no explicit mock mode
            # The error should be raised when generate_image_from_prompt is called without key and not in mock mode
            generator.generate_image_from_prompt("Test Dish")

    def test_initialization_with_api_key_not_mock_by_default(self):
        # Ensure mock flag is not set or is false
        if 'USE_MOCK_IMAGE_GENERATOR' in os.environ:
            del os.environ['USE_MOCK_IMAGE_GENERATOR']
        # os.environ['USE_MOCK_IMAGE_GENERATOR'] = 'false' # or simply ensure it's not 'true'

        os.environ['IMAGE_GENERATION_API_KEY'] = 'test_key_123'
        generator = DishImageGenerator() # API key from env

        # This will attempt a real API call if api_base_url is set, or fail if not.
        # Since we don't have a real API base URL for testing, we expect it to print errors or return None,
        # but not use the mock URLs unless USE_MOCK_IMAGE_GENERATOR was true.
        # The generate_image_from_prompt method returns None if the real API call fails and it's not in mock mode.
        # It also prints errors to stdout.
        # If api_base_url is None (default), it returns None without trying requests.post
        self.assertIsNone(generator.api_base_url) # By default it's None
        url = generator.generate_image_from_prompt("Test Dish")
        self.assertIsNone(url) # Expect None as no real API call can be made successfully

    def test_mock_image_generation_specific_keywords(self):
        os.environ['USE_MOCK_IMAGE_GENERATOR'] = 'true'
        generator = DishImageGenerator()

        url_burger = generator.generate_image_from_prompt("A big burger")
        self.assertIn("Burger", url_burger)

        url_pizza = generator.generate_image_from_prompt("Pepperoni pizza")
        self.assertIn("Pizza", url_pizza)

        url_salad = generator.generate_image_from_prompt("Fresh garden salad")
        self.assertIn("Salad", url_salad)

        url_pasta = generator.generate_image_from_prompt("Creamy pasta dish")
        self.assertIn("Pasta", url_pasta)

        url_random = generator.generate_image_from_prompt("Some other food")
        self.assertTrue(any(mock_url_part in url_random for mock_url_part in generator.mock_image_urls))


    def test_process_uploaded_image_mock_mode(self):
        os.environ['USE_MOCK_IMAGE_GENERATOR'] = 'true'
        generator = DishImageGenerator()

        class MockFileStorage:
            def __init__(self, filename="test_image.jpg"):
                self.filename = filename
            def save(self, dst):
                # In a real scenario, this would save the file.
                # For the mock, we don't need to actually create a file.
                pass # Simulate saving

        mock_file = MockFileStorage("my_dish.jpg")
        url = generator.process_uploaded_image(
            image_file_storage=mock_file,
            dish_name="My Uploaded Steak",
            description="A juicy steak from upload.",
            style_prompt="Make it look professional."
        )
        self.assertIsNotNone(url)
        # In mock mode, process_uploaded_image still falls back to text-based mock selection for now
        self.assertTrue(any(mock_url_part in url for mock_url_part in generator.mock_image_urls))
        # Could be more specific if mock logic for `process_uploaded_image` was different.
        # For instance, if it always returned a specific "uploaded image mock".


    # Placeholder for a test that would use a mock API (e.g. using unittest.mock.patch or requests_mock)
    # This is more involved and requires mocking the `requests.post` call itself.
    # @unittest.skip("Real API call mocking not implemented in this basic test suite")
    # def test_real_api_call_structure_mocked_response(self):
    #     os.environ['IMAGE_GENERATION_API_KEY'] = 'fake_api_key'
    #     if 'USE_MOCK_IMAGE_GENERATOR' in os.environ: # Ensure not in explicit mock mode
    #         del os.environ['USE_MOCK_IMAGE_GENERATOR']

    #     generator = DishImageGenerator(api_base_url="https://fakeapi.example.com/generate")

    #     with unittest.mock.patch('requests.post') as mock_post:
    #         mock_response = unittest.mock.Mock()
    #         # Example DALL-E like successful response
    #         mock_response.json.return_value = {"created": 1678886400, "data": [{"url": "https://generated.example.com/image.png"}]}
    #         mock_response.status_code = 200
    #         def raise_for_status(): pass # No-op for success
    #         mock_response.raise_for_status = raise_for_status
    #         mock_post.return_value = mock_response

    #         url = generator.generate_image_from_prompt("A test prompt")
    #         self.assertEqual(url, "https://generated.example.com/image.png")
    #         mock_post.assert_called_once()
    #         # Further assertions can be made on the payload of the call to mock_post.call_args


if __name__ == '__main__':
    unittest.main()
