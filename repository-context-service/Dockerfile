FROM python:3.11-slim

# Install git as a system dependency for GitPython
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Pre-download the embedding model during image build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy source directories and files
COPY app.py config.py models.py ./
COPY routes ./routes
COPY services ./services
COPY utils ./utils

# Port the service listens on
EXPOSE 8003

# Run service using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
