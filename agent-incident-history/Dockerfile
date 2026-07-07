FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py embeddings.py seed_incidents.py generate_fake_incidents.py ./
COPY incident_history ./incident_history
COPY incident_seeding ./incident_seeding
CMD ["python", "app.py"]
