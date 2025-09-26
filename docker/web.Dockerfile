FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip && pip install uv

COPY . /app
RUN uv pip install --system .

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]

