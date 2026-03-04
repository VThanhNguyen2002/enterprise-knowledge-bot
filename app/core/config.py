import os
from dotenv import load_dotenv

# Chỉ load file .env đúng 1 lần tại đây
load_dotenv(override=True)

class Settings:
    HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    LLM_MODEL = os.getenv("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
    
    # Ép kiểu dữ liệu cho an toàn
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
    RETRIEVER_K = int(os.getenv("RETRIEVER_K", 2))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))

settings = Settings()