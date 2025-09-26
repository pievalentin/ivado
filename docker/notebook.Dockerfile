FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip && pip install uv

COPY . /app
RUN uv pip install --system .

CMD ["uv", "run", "python", "-m", "notebook", "--NotebookApp.allow_origin='*'", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.ip=0.0.0.0", "--NotebookApp.port=8888", "--NotebookApp.notebook_dir=/app/notebooks"]

