FROM python:3.12-slim

WORKDIR /app

# Install dependencies first.
# Docker caches this layer — so if requirements.txt hasn't changed,
# it won't reinstall everything on every build. Much faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend and frontend code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Move into the backend folder before starting the server
WORKDIR /app/backend

# Cloud Run uses port 8080 by default
EXPOSE 8080

# Use shell form so $PORT env variable is read at runtime
# Cloud Run injects PORT — we use it directly instead of hardcoding 8080
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
