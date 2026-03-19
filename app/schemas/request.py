import re
from pydantic import BaseModel, field_validator

class QuestionRequest(BaseModel):
    question: str

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if len(v) > 2000:
            raise ValueError("Câu hỏi quá dài (tối đa 2000 ký tự).")
        
        dangerous_patterns = [
            r'(?i)ignore.*instructions?',
            r'(?i)system\s*prompt',
            r'(?i)bỏ\s*qua.*hướng\s*dẫn',
            r'(?i)quên.*đi',
            r'(?i)execute|system\(',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError("Phát hiện nội dung không an toàn. Yêu cầu bị từ chối.")
        return v.strip()