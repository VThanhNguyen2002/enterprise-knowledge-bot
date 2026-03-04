import os
import logging
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from app.core.config import settings

# Setup công cụ ghi log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        # Biến nội bộ, ban đầu gán rỗng để server khởi động nhanh
        self._embeddings = None
        self._vector_store = None
        self._llm = None
        self._prompt = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            logger.info(f"Đang tải Embedding model: {settings.EMBEDDING_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        return self._embeddings

    @property
    def vector_store(self):
        if self._vector_store is None:
            logger.info(f"Đang kết nối ChromaDB tại: {settings.CHROMA_PATH}")
            self._vector_store = Chroma(
                embedding_function=self.embeddings, 
                persist_directory=settings.CHROMA_PATH
            )
        return self._vector_store

    @property
    def llm(self):
        if self._llm is None:
            logger.info(f"Đang tải LLM model: {settings.LLM_MODEL}")
            self._llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                base_url="https://router.huggingface.co/v1",
                api_key=settings.HF_TOKEN,
                max_tokens=256,
                temperature=settings.LLM_TEMPERATURE,
            )
        return self._llm

    @property
    def prompt(self):
        if self._prompt is None:
            template = """Bạn là trợ lý AI nội bộ của công ty. Hãy trả lời câu hỏi dựa trên ngữ cảnh sau. Nếu không biết, hãy nói là không biết, đừng tự bịa ra.
Ngữ cảnh: {context}
Câu hỏi: {question}
Trả lời:"""
            self._prompt = PromptTemplate.from_template(template)
        return self._prompt

    def ingest_document(self, file_path: str):
        try:
            # Kiểm tra an toàn (Validation)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
            if not file_path.endswith('.txt'):
                raise ValueError("Hệ thống hiện chỉ hỗ trợ upload file .txt")

            logger.info(f"Bắt đầu xử lý tài liệu: {file_path}")
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()

            splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
            chunks = splitter.split_documents(docs)

            self.vector_store.add_documents(chunks)
            logger.info(f"Lưu thành công {len(chunks)} đoạn vào Database.")
            return f"Đã xử lý thành công {len(chunks)} đoạn văn bản từ {file_path}"
        except Exception as e:
            logger.error(f"Lỗi Ingestion: {str(e)}")
            raise e

    def chat(self, question: str):
        try:
            logger.info(f"Nhận câu hỏi: {question}")
            retriever = self.vector_store.as_retriever(search_kwargs={"k": settings.RETRIEVER_K})
            rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
            answer = rag_chain.invoke(question)
            logger.info("Đã phản hồi câu hỏi thành công.")
            return answer
        except Exception as e:
            logger.error(f"Lỗi Chatbot: {str(e)}")
            raise e

# Khởi tạo instance duy nhất để dùng chung cho toàn bộ app
rag_service = RAGService()