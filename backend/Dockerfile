FROM python:3.11-slim

# System deps for OCR + PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps with binary wheels (no source compilation)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefer-binary -r requirements.txt

COPY . .

RUN mkdir -p /tmp/uploads /tmp/reports

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
