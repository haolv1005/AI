# backend/knowledge_base.py
import os
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from typing import List  # 添加导入

class KnowledgeBase:
    KB_FILES_DIR = "data/knowledge_base/files"
    
    def __init__(self, kb_dir="data/knowledge_base"):
        self.kb_dir = os.path.normpath(kb_dir)
        self.index_path = os.path.join(self.kb_dir, "faiss_index")
        os.makedirs(self.KB_FILES_DIR, exist_ok=True)
        os.makedirs(self.kb_dir, exist_ok=True)
        
        self._embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        self._vectorstore = self._init_vectorstore()
    
    def _init_vectorstore(self):
        try:
            if os.path.exists(os.path.join(self.index_path, "index.faiss")):
                return FAISS.load_local(self.index_path, self._embeddings)
            return FAISS.from_documents(
                [Document(page_content="初始化")], self._embeddings
            )
        except Exception:
            return FAISS.from_documents(
                [Document(page_content="初始化")], self._embeddings
            )
    
    def _excel_to_text(self, file_path):
        excel_data = pd.read_excel(file_path, sheet_name=None)
        documents = []
        
        for sheet_name, df in excel_data.items():
            # 优化表格转换格式
            content = f"<表格: {sheet_name}>\n"
            content += f"<列名>: {', '.join(df.columns.astype(str))}\n"
            content += f"<示例数据>: \n"
            
            for idx, row in df.head(3).iterrows():
                row_data = ", ".join(f"{col}:{val}" for col, val in zip(df.columns, row.values))
                content += f"- 行{idx+1}: {row_data}\n"
            
            # 添加结构化标记
            content += "<表格结束>"
            documents.append(Document(
                page_content=content, 
                metadata={"source": os.path.basename(file_path)}
            ))
        return documents
    
    def add_document(self, file_path):
        """添加文档到知识库并保存到固定位置"""
        filename = os.path.basename(file_path)
        kb_file_path = os.path.join(self.KB_FILES_DIR, filename)
        
        # 保存到知识库专属目录
        if not os.path.exists(kb_file_path):
            with open(file_path, 'rb') as src, open(kb_file_path, 'wb') as dest:
                dest.write(src.read())
        
        # 根据文件类型处理内容
        ext = os.path.splitext(kb_file_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            documents = self._excel_to_text(kb_file_path)
        elif ext == '.csv':
            # CSV处理逻辑（简化）
            documents = [Document(page_content="CSV内容", metadata={"source": filename})]
        else:
            # 其他文件类型处理
            documents = [Document(page_content="文件内容", metadata={"source": filename})]
        
        # 更新向量库
        new_vs = FAISS.from_documents(documents, self._embeddings)
        self._vectorstore.merge_from(new_vs)
        self._vectorstore.save_local(self.index_path)
        return True
    
    def search(self, query, k=3, full_content=False):
        if not self._vectorstore:
            return []
    
        docs = self._vectorstore.similarity_search(query, k=k)
        
        # 根据参数返回完整内容或摘要
        if full_content:
            return [doc.page_content for doc in docs]
        else:
            return [f"结果 {i}: {doc.page_content[:200]}..." for i, doc in enumerate(docs, 1)]