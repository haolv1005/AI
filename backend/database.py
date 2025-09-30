# backend/database.py
import sqlite3
import os
import threading
import traceback
from pathlib import Path
from typing import List
from typing import List, Tuple, Dict, Union
thread_local = threading.local()

class Database:
    def __init__(self, db_path="E:/sm-ai/data/testcase.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _get_connection(self):
        if not hasattr(thread_local, "connection"):
            thread_local.connection = sqlite3.connect(self.db_path)
            thread_local.connection.row_factory = sqlite3.Row
        return thread_local.connection
    
    def _create_tables(self):
        """创建或更新数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建记录表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        
        
        # 定义要添加的列
        
    
    def add_record(self, original_filename, file_path, output_filename, output_path, 
                   summary=None, requirement_analysis=None, decision_table=None, 
                   test_cases=None, test_validation=None):
        """添加记录到数据库（新流程所需字段）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO records (
                original_filename, file_path, 
                output_filename, output_path, 
                summary, requirement_analysis, decision_table,
                test_cases, test_validation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            original_filename, file_path, 
            output_filename, output_path, 
            summary, requirement_analysis, decision_table,
            test_cases, test_validation
        ))
        conn.commit()
        return cursor.lastrowid
    
    def get_records(self):
        """获取所有记录（包括新流程的所有字段）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM records ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def add_knowledge_file(self, filename, file_path):
        """添加知识文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查文件是否已存在
            cursor.execute("SELECT id FROM knowledge_files WHERE file_path = ?", (file_path,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"文件已存在，跳过添加: {file_path}")
                return True
            
            # 添加新记录
            cursor.execute('''
                INSERT INTO knowledge_files (filename, file_path)
                VALUES (?, ?)
            ''', (filename, file_path))
            conn.commit()
            print(f"成功添加知识文件记录: {filename} -> {file_path}")
            return True
        except Exception as e:
            print(f"添加知识文件记录失败: {str(e)}")
            print(traceback.format_exc())
            return False
    
    def get_knowledge_documents(self) -> List[Dict]:
        """获取知识库文档列表，添加详细日志"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
            records = []
            
            for row in cursor.fetchall():
                record = dict(row)
                record['exists'] = os.path.exists(record['file_path'])
                records.append(record)
            
            print(f"从数据库获取到 {len(records)} 条知识文件记录")
            return records
        except Exception as e:
            print(f"获取知识库文档失败: {str(e)}")
            print(traceback.format_exc())
            return []
    
    def get_knowledge_documents(self) -> List[Dict]:
        """获取知识库文档列表，添加详细日志"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
            records = []
            
            for row in cursor.fetchall():
                record = dict(row)
                record['exists'] = os.path.exists(record['file_path'])
                records.append(record)
            
            print(f"从数据库获取到 {len(records)} 条知识文件记录")
            return records
        except Exception as e:
            print(f"获取知识库文档失败: {str(e)}")
            print(traceback.format_exc())
            return []
    

        """获取所有知识文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    # 在Database类中添加新方法
    # 在Database类中添加新方法
    def get_knowledge_documents(self) -> List[Dict]:
        """获取知识库文档列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取所有知识文件
        cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
        records = []
        
        # 为每个文件添加文档计数
        for row in cursor.fetchall():
            record = dict(row)
            record['exists'] = os.path.exists(record['file_path'])
            records.append(record)
    
        return records
        
        

    def get_vector_documents(self) -> List[Dict]:
        """获取所有向量文档及关联文件信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vd.id, vd.content, vd.metadata, 
                kf.filename, kf.file_path, kf.uploaded_at
            FROM vector_documents vd
            JOIN knowledge_files kf ON vd.file_id = kf.id
            ORDER BY kf.uploaded_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    # 在Database类中添加删除方法
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
