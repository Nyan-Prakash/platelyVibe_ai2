# plately_ai/run.py

import os
from app import create_app # Import the factory function from plately_ai/app/__init__.py

# Create an application instance using the factory
# You can pass configuration options here if needed, or rely on environment variables
# e.g., app = create_app(os.environ.get('FLASK_CONFIG') or 'default')
app = create_app()

if __name__ == '__main__':
    # Get host and port from environment variables with defaults
    # HOST = os.environ.get('FLASK_RUN_HOST', '127.0.0.1') # Default Flask host
    HOST = os.environ.get('FLASK_RUN_HOST', '0.0.0.0') # Make it accessible for Docker
    PORT = int(os.environ.get('FLASK_RUN_PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1' # '1' for True, '0' for False

    # Note: For production, use a proper WSGI server like Gunicorn or uWSGI
    # instead of Flask's built-in development server.
    app.run(host=HOST, port=PORT, debug=DEBUG)
