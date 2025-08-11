FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-nor libjpeg62-turbo libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tesseract datasettbane (kan variere per distro/versjon)
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

CMD ["python", "app.py"]
