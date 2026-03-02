FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry install --only main --no-root

# Copy project files
COPY . /app

# Collect static
# RUN poetry run python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run Django dev
CMD ["poetry", "run", "gunicorn", "archives.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]