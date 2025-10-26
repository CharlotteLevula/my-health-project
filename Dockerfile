# Use a Python base image, usually a stable slim version
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files (app.py, auth files, .env, etc.)
# NOTE: We rely on volumes for tokens/env, but copy the code
COPY . .

# Expose the port Streamlit uses
EXPOSE 8501

# Command to run the Streamlit application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
