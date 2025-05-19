# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Ensure any old version of google-adk is removed before installing from requirements
RUN pip uninstall -y google-adk || true

# Install build tools and critical pre-dependencies
RUN pip install --no-cache-dir setuptools wheel
RUN pip install --no-cache-dir aiohttp

# Install remaining requirements, allowing pip to use build isolation if needed
RUN pip install --no-cache-dir -r requirements.txt
    
# Ensure the correct google-adk version is installed as a final step
RUN pip uninstall -y google-adk || true
RUN pip install --no-cache-dir google-adk==0.2.0

# Add the Gemini API Key as an environment variable
# The value used here should be the actual API key you have provided.
ENV GEMINI_API_KEY="AIzaSyAOgdJnkn09hlOAgXNUVAvPcRNhbg_7RUQ"

# Copy the rest of the application's code into the container at /app
COPY . /app/

# (Optional) If your application runs on a specific port, you can expose it
# EXPOSE 8000

# (Optional) Define a default command to run when the container starts
# For example, if you had a main.py to run your web server:
# CMD ["python", "src/instabids/main.py"]
# For now, we'll leave CMD commented out, as we'll likely execute scripts manually.
