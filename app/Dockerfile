FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
CMD ["gunicorn", "-w", "1", "--threads", "32", "-b", "0.0.0.0:8000", "server:app"]
