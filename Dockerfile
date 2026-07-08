FROM python:3.11.7-slim-bullseye

WORKDIR /app

# ── System deps + Google Chrome ───────────────────────────────────────────────
# Chrome (channel='chrome') bypasses Cloudflare TLS fingerprinting better than
# bundled Playwright Chromium. Install it from Google's official apt repo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    wget \
    gnupg \
    ca-certificates \
    curl \
    # Chrome runtime deps
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    fonts-liberation \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# ── Python packages ───────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's bundled Chromium as fallback
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# ── App code ──────────────────────────────────────────────────────────────────
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Run headless in Docker — no display available
ENV ECOURTS_HEADLESS=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
