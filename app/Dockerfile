FROM python:3.12-slim
# pip in a container runs as root by design; its warnings about that, and about its own new versions, are noise
# that shows up red in `planetai update` and hides the lines that matter.
ENV PIP_ROOT_USER_ACTION=ignore PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements*.txt ./
# requirements-packs.txt is written by `planetai packs` from the `pip:` lists of code packs (gitignored)
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ -s requirements-packs.txt ]; then pip install --no-cache-dir -r requirements-packs.txt; fi
# every module, not a list — a list silently omits new files and the app dies on import (v0.4.1)
COPY *.py ./
COPY static ./static
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
