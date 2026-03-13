FROM python:3.11-slim

# تثبيت الأدوات المطلوبة للتحويل
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# تثبيت مكتبات بايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]