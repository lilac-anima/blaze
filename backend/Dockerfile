FROM python:3.12-slim

WORKDIR /app

# Copy project metadata and source before editable installation
COPY pyproject.toml .
COPY backend/ backend/

# Install dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Expose the API port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
