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




    @staticmethod
    def get_file_preview(file_path: str) -> str:
            """获取文件的安全预览，最多显示指定字符数"""
            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    return "文件不存在"
                
                # 根据文件类型处理
                ext = os.path.splitext(file_path)[1].lower()
                
                # 处理文本文件
                text_extensions = ['.txt', '.csv', '.log', '.ini', '.cfg', '.py', '.js', '.html', '.css', '.json', '.xml']
                if ext in text_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            
                            return f.read()
                    except UnicodeDecodeError:
                        # 如果UTF-8解码失败，尝试其他编码
                        try:
                            with open(file_path, 'r', encoding='latin-1') as f:
                                
                                return f.read()
                        except:
                            return "<无法解码的文本内容>"
                
                # 处理Excel文件
                elif ext in ['.xlsx', '.xls']:
                    try:
                        df = pd.read_excel(file_path)
                        return df.to_string()
                    except Exception as e:
                        return f"<Excel文件预览失败: {str(e)}"
                
                # 处理Word文档
                elif ext == '.docx':
                    try:
                        doc = docx.Document(file_path)
                        return "\n".join([para.text for para in doc.paragraphs])
                    except Exception as e:
                        return f"<Word文档预览失败: {str(e)}"
                
                # 处理PDF文档
                elif ext == '.pdf':
                    try:
                        with open(file_path, 'rb') as file:
                            reader = PdfReader(file)
                            text = ""
                            for page in reader.pages:
                                page_text = page.extract_text()
                                if page_text: 
                                    text += page_text + "\n"
                            return text
                    except Exception as e:
                        return f"<PDF文档预览失败: {str(e)}"
                
                # 其他文件类型
                else:
                    try:
                # 尝试作为二进制文件读取
                        with open(file_path, 'rb') as f:
                            return f"<二进制文件预览> 大小: {os.path.getsize(file_path)} 字节"
                    except:
                        return f"<{ext.upper()[1:]} 文件 - 预览不可用>"
                    
            except Exception as e:
                return f"预览错误: {str(e)}"