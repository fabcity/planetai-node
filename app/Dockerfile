FROM python:3.12-slim
WORKDIR /app
COPY requirements*.txt ./
# requirements-packs.txt is written by `planetai packs` from the `pip:` lists of code packs (gitignored)
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ -s requirements-packs.txt ]; then pip install --no-cache-dir -r requirements-packs.txt; fi
# every module, not a list — a list silently omits new files and the app dies on import (v0.4.1)
COPY *.py ./
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
