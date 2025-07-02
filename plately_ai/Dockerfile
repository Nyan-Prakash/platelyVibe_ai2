# plately_ai/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# This includes the 'app' package, 'simulation', 'menu_psychology', 'visual_generator', 'run.py', etc.
COPY . .
# If specific subdirectories need to be copied:
# COPY app ./app
# COPY simulation ./simulation
# COPY menu_psychology ./menu_psychology
# COPY visual_generator ./visual_generator
# COPY run.py .
# COPY instance ./instance # If you have default instance configs; user data should ideally be volumes

# Make port 5000 available to the world outside this container
# FastAPI/Uvicorn default port is 8000
EXPOSE 8000

# Define environment variables
# USE_MOCK_IMAGE_GENERATOR is used by DishImageGenerator
ENV USE_MOCK_IMAGE_GENERATOR=true
# PYTHONUNBUFFERED ensures that Python output (like print statements) is sent straight to terminal
ENV PYTHONUNBUFFERED=1
# For Uvicorn reloading in development (alternative to --reload flag if preferred)
# ENV UVICORN_RELOAD=1


# Create a non-root user to run the application for better security
# Using /app as WORKDIR for consistency with original setup
WORKDIR /app
RUN useradd --create-home --home-dir /home/appuser --no-log-init --system --uid 1001 appuser \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app
# The chown and chmod above assume files are already in /app.
# It's often better to COPY files after creating user and setting WORKDIR as user.

# Re-copy application code as the appuser to ensure correct ownership from the start
# This assumes the WORKDIR /app is intended for the application code.
COPY --chown=appuser:appuser . .

# Switch to the non-root user
USER appuser


# Command to run the application when the container launches
# Using Uvicorn to run the FastAPI application (`app` instance in `plately_ai/main.py`)
# `--host 0.0.0.0` makes the server accessible from outside the container.
# `--port 8000` is the standard port for Uvicorn.
# `--reload` can be added for development to auto-reload on code changes (mount code volume in docker-compose).
# For production, remove --reload and consider more workers if appropriate.
CMD ["uvicorn", "plately_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
# To enable reload for development, you could use a separate CMD or an entrypoint script:
# CMD ["uvicorn", "plately_ai.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
