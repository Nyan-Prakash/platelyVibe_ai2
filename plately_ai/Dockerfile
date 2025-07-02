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
COPY . .

# Flask default development server runs on port 5000
EXPOSE 5000

# Define environment variables
ENV USE_MOCK_IMAGE_GENERATOR=true
ENV PYTHONUNBUFFERED=1
# Flask specific environment variables can be set here or in docker-compose.yml
# For example, to run in development mode:
# ENV FLASK_APP=run.py # Often set if using `flask run` command, but we use `python run.py`
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1


# Create a non-root user to run the application
RUN useradd --create-home --home-dir /home/appuser --no-log-init --system --uid 1001 appuser \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app

# Switch to the non-root user
USER appuser
WORKDIR /app # Ensure this is the final WORKDIR, where run.py is located

# Command to run the application when the container launches
# run.py should handle app.run(host='0.0.0.0')
CMD ["python", "run.py"]
