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
# This initial copy makes files available for chown in the RUN useradd step
COPY . .

# FastAPI/Uvicorn default port is 8000
EXPOSE 8000

# Define environment variables
ENV USE_MOCK_IMAGE_GENERATOR=true
ENV PYTHONUNBUFFERED=1

# Create a non-root user to run the application for better security
# and set up /app directory with correct ownership and permissions.
# The WORKDIR /app is already set.
RUN useradd --create-home --home-dir /home/appuser --no-log-init --system --uid 1001 appuser \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app
# Note: The above chown assumes files are already in /app from the COPY . . command.

# It's good practice to COPY application code after setting up the user and WORKDIR
# to ensure correct permissions from the start, especially if WORKDIR was user's home.
# However, since WORKDIR is /app and we chown /app, the previous COPY . . followed by chown is acceptable.
# If we wanted to be more explicit and copy into the user's final workdir as user:
# USER appuser
# WORKDIR /app # Or /home/appuser/app if preferred
# COPY --chown=appuser:appuser . . # This would be the main code copy as appuser

# For this setup, the current structure is:
# 1. WORKDIR /app
# 2. COPY . . (as root)
# 3. RUN useradd... && chown -R appuser:appuser /app (change ownership of /app and its contents)
# This is fine. The redundant `COPY --chown=appuser:appuser . .` from the previous version has been removed.

# Switch to the non-root user
USER appuser
WORKDIR /app # Ensure this is the final WORKDIR

# Set PYTHONPATH so Python can find modules within /app
# This is crucial if main.py is at /app/main.py and imports from /app/api etc.
# Or if uvicorn is run with `plately_ai.main:app` and plately_ai is in /app/plately_ai
# For `python -m uvicorn main:app` where main.py is at /app/main.py,
# Python automatically adds the script's directory (/app) to sys.path.
# So, this ENV PYTHONPATH might be redundant but doesn't harm.
ENV PYTHONPATH=/app

# Command to run the application when the container launches
# Using `python -m uvicorn` ensures uvicorn is run as a module,
# which can help with path discovery similar to local execution.
# `main:app` assumes main.py is in the WORKDIR (/app).
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# For development reload, the command will be overridden in docker-compose.yml
# to add `--reload`.
# Example production command (no reload, more workers):
# CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
