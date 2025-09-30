# backend/knowledge_base.py
import os
import pandas as pd
import numpy as np
import traceback  # 添加这一行以导入 traceback 模块
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Tuple, Dict, Union
from .database import Database
class KnowledgeBase:
    def __init__(self, kb_dir="E:/sm-ai/data/knowledge_base"):
        self.kb_dir = os.path.normpath(kb_dir)
        self.KB_FILES_DIR = os.path.join(self.kb_dir, "files")
        self.index_path = os.path.join(self.kb_dir, "faiss_index")
        
        # 确保目录存在
        os.makedirs(self.KB_FILES_DIR, exist_ok=True)
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.index_path, exist_ok=True)
        
        self._embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        self._vectorstore = None
        self._init_vectorstore()
    
    # 修改后的 _init_vectorstore 方法
    def _init_vectorstore(self):
        # 修改初始化逻辑，确保正确加载索引
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
                # 初始化为空索引
                self._vectorstore = FAISS.from_documents([], self._embeddings)
                # self._vectorstore.save_local(self.index_path)
                print("创建新的空知识库索引")
        except Exception as e:
            print(f"初始化向量库失败: {str(e)}")
            self._vectorstore = FAISS.from_documents([], self._embeddings)

    def _excel_to_text(self, file_path: str) -> List[Document]:
        """专门处理包含固定列名的Excel文件"""
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None)
            documents = []
            for sheet_name, df in excel_data.items():
            # 跳过空表
                if df.empty:
                    continue
            for index, row in df.iterrows():
                # 构建该行的文本表示
                content = f"工作表: {sheet_name}, 行号: {index+1}\n"
                for col_name, value in row.items():
                    # 处理NaN值
                    if pd.isna(value):
                        value = "空"
                    content += f"{col_name}: {value}\n"
                
                # 添加元数据
                metadata = {
                    "source": os.path.basename(file_path),
                    "sheet": sheet_name,
                    "columns": ", ".join(df.columns),
                    "row_count": len(df)
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
        
            return documents
        except Exception as e:
            print(f"处理Excel文件失败: {str(e)}")
            return []

    def _chunk_document(self, text: str, filename: str, chunk_size=500):
        """将长文本分割为适当大小的块"""
        if not text or text.strip() == "":
            return []
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
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
                    "total_chunks": len(chunks)
                }
            )
            for i, chunk in enumerate(chunks) if chunk.strip() != ""
        ]
    
    def add_document(self, file_path: str, ai_client=None) -> bool:
            """添加文档到知识库并保存到固定位置"""
            # ... 前面代码不变 ...
            
            # 保存到知识库专属目录
            kb_file_path = os.path.join(self.KB_FILES_DIR, os.path.basename(file_path))
            os.makedirs(os.path.dirname(kb_file_path), exist_ok=True)
            
            try:
                with open(file_path, 'rb') as src, open(kb_file_path, 'wb') as dest:
                    dest.write(src.read())
                print(f"文件已保存到知识库: {kb_file_path}")
            except Exception as e:
                print(f"保存文件到知识库失败: {str(e)}")
                return False
            
            # 添加到知识库后，保存到数据库
            filename = os.path.basename(file_path)
            try:
                # 使用主数据库实例
                from . import database  # 避免循环导入
                db = database.Database(db_path=DB_PATH)  # 使用全局DB_PATH
                
                if not db.add_knowledge_file(filename, kb_file_path):
                    print(f"警告: 数据库添加文件记录失败: {filename}")
            except Exception as e:
                print(f"保存知识文件到数据库失败: {str(e)}")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, Dict]]:
        if not self._vectorstore:
            return []
        
        try:
            # 1. 直接向量相似度搜索
            docs = self._vectorstore.similarity_search(query, k=k)
            return [(doc.page_content, doc.metadata) for doc in docs]
        except Exception as e:
            print(f"知识库搜索失败: {str(e)}")
            return []
        
    def rebuild_index(self):
        """完全重建知识库索引"""
        try:
            # 删除现有索引文件
            index_file = os.path.join(self.index_path, "index.faiss")
            pkl_file = os.path.join(self.index_path, "index.pkl")
            for file_path in [index_file, pkl_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除索引文件: {file_path}")
            
            # 重新初始化空索引
            self._vectorstore = FAISS.from_documents(
                [Document(page_content="初始化知识库")], 
                self._embeddings
            )
            self._vectorstore.save_local(self.index_path)
            print("已重置知识库索引")
            
            # 重新添加所有文件
            for filename in os.listdir(self.KB_FILES_DIR):
                file_path = os.path.join(self.KB_FILES_DIR, filename)
                print(f"重新添加文件到知识库: {filename}")
                self.add_document(file_path)
                
            print("知识库索引重建完成")
            return True
        except Exception as e:
            print(f"重建索引失败: {str(e)}")
            return False




    def get_all_documents(self) -> List[Dict]:
        """获取知识库中的所有文档内容"""
        try:
            # 使用绝对路径实例化Database
            db = Database()
            return db.get_knowledge_documents()
        except Exception as e:
            print(f"获取知识库文档失败: {str(e)}")
            return []
    def get_index_status(self) -> Dict:
        """获取索引状态信息"""
        status = {
            "index_exists": False,
            "document_count": 0,
            "file_count": 0
        }
    
        try:
            # 检查索引文件是否存在
            index_file = os.path.join(self.index_path, "index.faiss")
            status["index_exists"] = os.path.exists(index_file)
            
            # 获取文档数量
            if self._vectorstore:
                status["document_count"] = len(self._vectorstore.index_to_docstore_id)
            
            # 获取文件数量
            if os.path.exists(self.KB_FILES_DIR):
                status["file_count"] = len(os.listdir(self.KB_FILES_DIR))
        
        except Exception as e:
            print(f"获取索引状态失败: {str(e)}")
        
        return status