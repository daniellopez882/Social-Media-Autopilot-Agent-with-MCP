# Python 3.12: crewai declares <3.14, and on 3.14 the previous code silently
# fell back to mock mode (see app/config.py) rather than failing to install.
FROM python:3.12-slim AS build

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 10001 socialpilot

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --chown=socialpilot:socialpilot app/ ./app/
COPY --chown=socialpilot:socialpilot social_media_prompts.py index.html ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BIND_HOST=0.0.0.0 \
    PORT=8000

USER socialpilot
EXPOSE 8000

# The process refuses to start on an invalid configuration (production with
# MOCK_MODE, or no API key), so a container that is up is one that passed
# preflight. The health check then only has to reach the API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

CMD ["sh", "-c", "uvicorn app.main:app --host ${BIND_HOST} --port ${PORT}"]
