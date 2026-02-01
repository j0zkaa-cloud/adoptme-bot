FROM python:3.9-slim

# Nainstalujeme závislosti pro systém
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Nastavíme složku
WORKDIR /app

# Zkopírujeme soubory
COPY . .

# Nainstalujeme Python knihovny
RUN pip install --no-cache-dir -r requirements.txt

# Nainstalujeme Playwright a Prohlížeč
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

# Spustíme bota
CMD ["python", "main.py"]
