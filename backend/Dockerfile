FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    XDG_CONFIG_HOME=/tmp/.config \
    XDG_CACHE_HOME=/tmp/.cache

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libreoffice \
        libreoffice-writer \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Fail the image build early if the headless office runtime needed for DOCX
# coordinate extraction and report rendering is missing or not executable.
RUN soffice --headless --version

COPY . .

RUN addgroup --system prism \
    && adduser --system --ingroup prism prism \
    && mkdir -p /app/storage/uploads \
    && mkdir -p /tmp/.config /tmp/.cache \
    && chown -R prism:prism /app /tmp/.config /tmp/.cache

USER prism

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://0.0.0.0:8000/health', timeout=2)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
