from typing import Union
import docx
from PyPDF2 import PdfReader
import os
import pandas as pd
class DocumentProcessor:
    @staticmethod
    def read_word(file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    
    @staticmethod
    def read_pdf(file_path: str) -> str:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    @staticmethod
    def read_file(file_path: str) -> str:
        if file_path.endswith('.docx'):
            return DocumentProcessor.read_word(file_path)
        elif file_path.endswith('.pdf'):
            return DocumentProcessor.read_pdf(file_path)
        else:
            raise ValueError("Unsupported file format")
    # 添加新方法



