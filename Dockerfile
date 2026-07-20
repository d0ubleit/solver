FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install Python deps + the package itself
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Run as non-root
RUN useradd --create-home --shell /bin/bash solver \
    && chown -R solver:solver /app
USER solver

# Default env vars
ENV DATABASE_URL=sqlite+aiosqlite:///data/solver.db
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "solver.main"]
