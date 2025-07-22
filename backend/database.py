# backend/database.py
import sqlite3
import os
import threading
from pathlib import Path

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
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                output_filename TEXT NOT NULL,
                output_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 定义要添加的列
        columns_to_add = [
            ('summary', 'TEXT'),
            ('requirement_analysis', 'TEXT'),
            ('decision_table', 'TEXT'),
            ('test_cases', 'TEXT'),
            ('test_validation', 'TEXT')
        ]
        
        # 获取现有的列
        cursor.execute("PRAGMA table_info(records)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # 添加缺失的列
        for column, column_type in columns_to_add:
            if column not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE records ADD COLUMN {column} {column_type}")
                    print(f"添加了新列: {column}")
                except Exception as e:
                    print(f"添加列 {column} 失败: {str(e)}")
        
        # 创建知识文件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    
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
        cursor.execute('''
            INSERT INTO knowledge_files (filename, file_path)
            VALUES (?, ?)
        ''', (filename, file_path))
        conn.commit()
        return cursor.lastrowid
    
    def get_knowledge_files(self):
        """获取所有知识文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
        return [dict(row) for row in cursor.fetchall()]