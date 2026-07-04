FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY risk_analyzers.py .
COPY infra_risk ./infra_risk
COPY llm_reasoner.py .
COPY llm ./llm
CMD ["python", "app.py"]
