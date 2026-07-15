FROM python:3.11-slim

# Install git as a system dependency for GitPython
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source directories and files
COPY app.py config.py models.py ./
COPY routes ./routes
COPY services ./services
COPY utils ./utils

# Port the service listens on
EXPOSE 8003

# Run service using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
