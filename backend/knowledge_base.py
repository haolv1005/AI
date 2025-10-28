# backend/knowledge_base.py
import os
import pandas as pd
import numpy as np
import traceback
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Tuple, Dict, Union
from .database import Database
import re

class KnowledgeBase:
    def __init__(self, kb_dir="E:/sm-ai/data/knowledge_base", db_path=None):
        self.kb_dir = os.path.normpath(kb_dir)
        self.KB_FILES_DIR = os.path.join(self.kb_dir, "files")
        self.index_path = os.path.join(self.kb_dir, "faiss_index")
        self.db_path = db_path  # 保存数据库路径
        
        # 确保目录存在
        os.makedirs(self.KB_FILES_DIR, exist_ok=True)
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.index_path, exist_ok=True)
        
        self._embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        self._vectorstore = None
        self._init_vectorstore()
    
    def _init_vectorstore(self):
        """修改初始化逻辑，避免空列表错误"""
        try:
            index_file = os.path.join(self.index_path, "index.faiss")
            if os.path.exists(index_file):
                self._vectorstore = FAISS.load_local(
                    self.index_path, 
                    self._embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"成功加载知识库索引，包含 {len(self._vectorstore.index_to_docstore_id)} 个文档块")
            else:
                # 创建一个虚拟文档来初始化索引，避免空列表错误
                dummy_doc = Document(
                    page_content="系统初始化文档",
                    metadata={"source": "system", "type": "initialization"}
                )
                self._vectorstore = FAISS.from_documents([dummy_doc], self._embeddings)
                self._vectorstore.save_local(self.index_path)
                print("创建新的知识库索引（包含初始化文档）")
        except Exception as e:
            print(f"初始化向量库失败: {str(e)}")
            # 备用方案：使用虚拟文档创建
            try:
                dummy_doc = Document(
                    page_content="系统初始化文档",
                    metadata={"source": "system", "type": "initialization"}
                )
                self._vectorstore = FAISS.from_documents([dummy_doc], self._embeddings)
                print("使用备用方案创建知识库索引")
            except Exception as e2:
                print(f"备用方案也失败: {str(e2)}")
                self._vectorstore = None

    def _excel_to_documents(self, file_path: str) -> List[Document]:
        """将Excel文件转换为文档列表"""
        try:
            documents = []
            
            # 读取Excel文件
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                # 跳过空表
                if df.empty:
                    continue
                
                # 处理每个工作表
                for index, row in df.iterrows():
                    # 构建文档内容
                    content = f"工作表: {sheet_name}\n行号: {index+1}\n"
                    
                    # 添加列数据
                    for col_name, value in row.items():
                        if pd.isna(value):
                            value = "空值"
                        content += f"{col_name}: {value}\n"
                    
                    # 添加元数据
                    metadata = {
                        "source": os.path.basename(file_path),
                        "sheet": sheet_name,
                        "row": index + 1,
                        "type": "excel_data"
                    }
                    
                    documents.append(Document(page_content=content, metadata=metadata))
            
            return documents
            
        except Exception as e:
            print(f"处理Excel文件失败: {str(e)}")
            return []

    def _text_to_documents(self, text: str, filename: str) -> List[Document]:
        """将文本分割为适当大小的块"""
        if not text or text.strip() == "":
            return []
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
        )
        
        chunks = splitter.split_text(text)
        return [
            Document(
                page_content=chunk,
                metadata={
                    "source": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "type": "text_chunk"
                }
            )
            for i, chunk in enumerate(chunks) if chunk.strip() != ""
        ]

    def add_document(self, file_path: str) -> bool:
        """添加文档到知识库"""
        try:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            
            documents = []
            
            # 根据文件类型处理
            if ext in ['.xlsx', '.xls']:
                # Excel文件处理
                documents = self._excel_to_documents(file_path)
            elif ext in ['.txt', '.csv']:
                # 文本文件处理
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                documents = self._text_to_documents(text, filename)
            elif ext in ['.docx', '.pdf']:
                # Word/PDF文件处理
                from .document_processor import DocumentProcessor
                if ext == '.docx':
                    text = DocumentProcessor.read_word(file_path)
                else:
                    text = DocumentProcessor.read_pdf(file_path)
                documents = self._text_to_documents(text, filename)
            else:
                print(f"不支持的文件类型: {ext}")
                return False
            
            if not documents:
                print(f"未从文件 {filename} 中提取到内容")
                return False
            
            # 检查当前索引是否只有初始化文档
            current_docs_count = len(self._vectorstore.index_to_docstore_id) if self._vectorstore else 0
            
            # 添加到向量存储
            if current_docs_count == 1 and self._is_initialization_doc_only():
                # 如果只有初始化文档，重新创建索引
                self._vectorstore = FAISS.from_documents(documents, self._embeddings)
            else:
                # 正常添加文档
                self._vectorstore.add_documents(documents)
            
            self._vectorstore.save_local(self.index_path)
            
            print(f"成功添加 {len(documents)} 个文档块到知识库: {filename}")
            return True
            
        except Exception as e:
            print(f"添加文档到知识库失败: {str(e)}")
            traceback.print_exc()
            return False

    def _is_initialization_doc_only(self) -> bool:
        """检查是否只有初始化文档"""
        if not self._vectorstore:
            return False
        
        try:
            # 获取所有文档
            all_docs = self._vectorstore.similarity_search("", k=10)
            if len(all_docs) == 1:
                doc = all_docs[0]
                return (doc.page_content == "系统初始化文档" and 
                        doc.metadata.get("source") == "system")
            return False
        except:
            return False

    def search(self, query: str, k: int = 5) -> List[Tuple[str, Dict]]:
        """搜索知识库"""
        if not self._vectorstore:
            return []
        
        try:
            # 如果是初始化文档，返回空结果
            if self._is_initialization_doc_only() and query.strip():
                return []
            
            # 执行相似度搜索
            docs = self._vectorstore.similarity_search(query, k=k)
            
            # 过滤掉初始化文档
            filtered_docs = []
            for doc in docs:
                if not (doc.page_content == "系统初始化文档" and doc.metadata.get("source") == "system"):
                    filtered_docs.append(doc)
            
            # 格式化结果
            results = []
            for doc in filtered_docs:
                content = doc.page_content
                metadata = doc.metadata
                
                # 如果是Excel数据，尝试提取更结构化的信息
                if metadata.get('type') == 'excel_data':
                    test_case_patterns = [
                        r'测试用例[名称|标题][:：]\s*(.+)',
                        r'用例[名称|标题][:：]\s*(.+)',
                        r'测试步骤[:：]\s*(.+)',
                        r'预期结果[:：]\s*(.+)'
                    ]
                    
                    extracted_info = {}
                    for pattern in test_case_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            key = re.search(r'([^:：]+)[:：]', pattern).group(1)
                            extracted_info[key] = matches[0]
                    
                    if extracted_info:
                        content = f"提取的测试信息:\n" + "\n".join([f"{k}: {v}" for k, v in extracted_info.items()]) + f"\n\n原始内容:\n{content}"
                
                results.append((content, metadata))
            
            return results
            
        except Exception as e:
            print(f"知识库搜索失败: {str(e)}")
            return []

    def rebuild_index(self):
        """完全重建知识库索引 - 修复版本"""
        try:
            # 删除现有索引文件
            index_files = [os.path.join(self.index_path, f) for f in os.listdir(self.index_path) 
                          if f.startswith("index.")]
            for file_path in index_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除索引文件: {file_path}")
            
            # 重新添加所有文件
            kb_files = [f for f in os.listdir(self.KB_FILES_DIR) 
                       if not f.startswith('.') and os.path.isfile(os.path.join(self.KB_FILES_DIR, f))]
            
            if not kb_files:
                print("知识库中没有文件，创建空索引")
                # 使用虚拟文档创建索引
                dummy_doc = Document(
                    page_content="系统初始化文档",
                    metadata={"source": "system", "type": "initialization"}
                )
                self._vectorstore = FAISS.from_documents([dummy_doc], self._embeddings)
                self._vectorstore.save_local(self.index_path)
                print("已创建空知识库索引")
                return True
            
            success_count = 0
            documents = []
            
            # 首先收集所有文档
            for filename in kb_files:
                file_path = os.path.join(self.KB_FILES_DIR, filename)
                print(f"处理文件: {filename}")
                
                ext = os.path.splitext(filename)[1].lower()
                file_documents = []
                
                # 根据文件类型处理
                if ext in ['.xlsx', '.xls']:
                    file_documents = self._excel_to_documents(file_path)
                elif ext in ['.txt', '.csv']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    file_documents = self._text_to_documents(text, filename)
                elif ext in ['.docx', '.pdf']:
                    from .document_processor import DocumentProcessor
                    if ext == '.docx':
                        text = DocumentProcessor.read_word(file_path)
                    else:
                        text = DocumentProcessor.read_pdf(file_path)
                    file_documents = self._text_to_documents(text, filename)
                
                if file_documents:
                    documents.extend(file_documents)
                    success_count += 1
                    print(f"成功处理 {filename}，添加 {len(file_documents)} 个文档块")
                else:
                    print(f"无法从 {filename} 提取内容")
            
            if documents:
                # 使用所有文档创建新索引
                self._vectorstore = FAISS.from_documents(documents, self._embeddings)
                self._vectorstore.save_local(self.index_path)
                print(f"知识库索引重建完成，成功添加 {success_count}/{len(kb_files)} 个文件，共 {len(documents)} 个文档块")
            else:
                print("没有可用的文档内容，创建空索引")
                dummy_doc = Document(
                    page_content="系统初始化文档",
                    metadata={"source": "system", "type": "initialization"}
                )
                self._vectorstore = FAISS.from_documents([dummy_doc], self._embeddings)
                self._vectorstore.save_local(self.index_path)
            
            return True
            
        except Exception as e:
            print(f"重建索引失败: {str(e)}")
            traceback.print_exc()
            return False

    def get_all_documents(self) -> List[Dict]:
        """获取知识库中的所有文档内容 - 修复版本"""
        try:
            if not self.db_path:
                # 如果没有提供db_path，使用默认路径
                default_db_path = "E:/sm-ai/data/testcase.db"
                db = Database(db_path=default_db_path)
            else:
                db = Database(db_path=self.db_path)
            
            return db.get_knowledge_documents()
        except Exception as e:
            print(f"获取知识库文档失败: {str(e)}")
            return []

    def get_index_status(self) -> Dict:
        """获取索引状态信息"""
        status = {
            "index_exists": False,
            "document_count": 0,
            "file_count": 0,
            "has_real_content": False
        }
    
        try:
            # 检查索引文件是否存在
            index_files = [f for f in os.listdir(self.index_path) 
                          if f.startswith("index.")]
            status["index_exists"] = len(index_files) > 0
            
            # 获取文档数量
            if self._vectorstore:
                total_count = len(self._vectorstore.index_to_docstore_id)
                # 如果只有初始化文档，实际文档数为0
                if self._is_initialization_doc_only():
                    status["document_count"] = 0
                    status["has_real_content"] = False
                else:
                    status["document_count"] = total_count
                    status["has_real_content"] = total_count > 0
            
            # 获取文件数量
            if os.path.exists(self.KB_FILES_DIR):
                kb_files = [f for f in os.listdir(self.KB_FILES_DIR) 
                           if not f.startswith('.') and os.path.isfile(os.path.join(self.KB_FILES_DIR, f))]
                status["file_count"] = len(kb_files)
        
        except Exception as e:
            print(f"获取索引状态失败: {str(e)}")
        
        return status
        
        return status
    def delete_knowledge_file(self, file_id: int):
        """删除知识库文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 先获取文件路径
        cursor.execute("SELECT file_path FROM knowledge_files WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        if not result:
            return False
        file_path = result[0]
        
        # 删除记录
        cursor.execute("DELETE FROM knowledge_files WHERE id = ?", (file_id,))
        
        conn.commit()
        
        # 尝试删除物理文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"删除物理文件失败: {str(e)}")
        
        return True