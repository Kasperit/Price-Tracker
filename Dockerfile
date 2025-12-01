# Multi-stage build for smaller image
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Python backend
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api/ ./api/
COPY database/ ./database/
COPY scrapers/ ./scrapers/
COPY config.py .
COPY scheduler.py .
COPY run_scraper.py .

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./static

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV DATABASE_URL=sqlite:///./data/price_tracker.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
