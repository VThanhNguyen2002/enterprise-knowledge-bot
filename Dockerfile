FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Cài đặt thư viện hệ thống cần thiết cho ChromaDB
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Cài đặt Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8000

# Chạy Uvicorn với 2 workers để tối ưu hiệu suất cho máy ảo 2 cores
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]