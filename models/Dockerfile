# The forecasting model, kept out of the app image on purpose: torch is a gigabyte the node does not otherwise need.
FROM python:3.12-slim
WORKDIR /app
# CPU wheels only: the default index would pull a CUDA build several times the size.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY core.py server.py pull.py ./
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
