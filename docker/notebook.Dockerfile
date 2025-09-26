FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip && pip install uv

COPY . /app
RUN uv pip install --system .

CMD ["uv", "run", "python", "-m", "notebook", "--allow-root", "--ServerApp.allow_origin='*'", "--ServerApp.token=''", "--ServerApp.password=''", "--ServerApp.ip=0.0.0.0", "--ServerApp.port=8888", "--ServerApp.root_dir=/app/notebooks"]

