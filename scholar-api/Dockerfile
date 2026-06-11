FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "scholar.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
