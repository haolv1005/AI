# backend/database.py - 恢复QA记录功能
import sqlite3
import os
import threading
import traceback
from pathlib import Path
from typing import List, Dict
import time

thread_local = threading.local()

class Database:
    def __init__(self, db_path="E:/sm-ai/data/testcase.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _get_connection(self):
        """获取数据库连接（线程安全）"""
        if not hasattr(thread_local, "connection"):
            thread_local.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
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
                original_filename TEXT,
                file_path TEXT,
                output_filename TEXT,
                output_path TEXT,
                summary TEXT,
                requirement_analysis TEXT,
                decision_table TEXT,
                test_cases TEXT,
                test_validation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建知识文件表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建智能问答记录表（简化版）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                reference_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print(f"数据库表已创建/检查完成，路径: {self.db_path}")
    
    def add_qa_record(self, question: str, answer: str, reference_count: int = 0) -> int:
        """添加智能问答记录（简化版）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO qa_history (question, answer, reference_count)
                VALUES (?, ?, ?)
            ''', (question, answer, reference_count))
            conn.commit()
            record_id = cursor.lastrowid
            print(f"成功添加问答记录，ID: {record_id}")
            return record_id
        except Exception as e:
            print(f"添加问答记录失败: {str(e)}")
            print(traceback.format_exc())
            conn.rollback()
            return -1
    
    def get_qa_records(self, limit: int = 100) -> List[Dict]:
        """获取智能问答记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM qa_history 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取问答记录失败: {str(e)}")
            print(traceback.format_exc())
            return []
    
    def delete_qa_record(self, record_id: int) -> bool:
        """删除智能问答记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM qa_history WHERE id = ?", (record_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"删除问答记录失败: {str(e)}")
            print(traceback.format_exc())
            conn.rollback()
            return False
    
    def add_knowledge_file(self, filename, file_path):
        """添加知识文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            print(f"尝试添加知识文件: {filename} -> {file_path}")
            
            # 检查文件是否已存在
            cursor.execute("SELECT id FROM knowledge_files WHERE file_path = ?", (file_path,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"文件已存在，ID: {existing['id']}")
                return True
            
            # 添加新记录
            cursor.execute('''
                INSERT INTO knowledge_files (filename, file_path)
                VALUES (?, ?)
            ''', (filename, file_path))
            conn.commit()
            
            file_id = cursor.lastrowid
            print(f"成功添加知识文件记录，ID: {file_id}, 文件名: {filename}")
            return True
        except Exception as e:
            print(f"添加知识文件记录失败: {str(e)}")
            print(traceback.format_exc())
            conn.rollback()
            return False
    
    def get_knowledge_documents(self) -> List[Dict]:
        """获取知识库文档列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
            rows = cursor.fetchall()
            
            records = []
            for row in rows:
                record = dict(row)
                # 检查文件是否存在
                file_path = record.get('file_path', '')
                if file_path:
                    record['exists'] = os.path.exists(file_path)
                else:
                    record['exists'] = False
                
                # 获取文件大小
                if record['exists']:
                    try:
                        size = os.path.getsize(file_path)
                        # 格式化文件大小
                        if size < 1024:
                            record['size_str'] = f"{size} B"
                        elif size < 1024 * 1024:
                            record['size_str'] = f"{size/1024:.2f} KB"
                        else:
                            record['size_str'] = f"{size/(1024*1024):.2f} MB"
                    except:
                        record['size_str'] = "未知大小"
                else:
                    record['size_str'] = "文件不存在"
                
                records.append(record)
            
            print(f"从数据库获取到 {len(records)} 条知识文件记录")
            return records
        except Exception as e:
            print(f"获取知识库文档失败: {str(e)}")
            print(traceback.format_exc())
            return []
    
    def add_record(self, original_filename, file_path, output_filename, output_path, 
                   summary=None, requirement_analysis=None, decision_table=None, 
                   test_cases=None, test_validation=None):
        """添加记录到数据库"""
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
        """获取所有记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM records ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    
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
                print(f"已删除物理文件: {file_path}")
            except Exception as e:
                print(f"删除物理文件失败: {str(e)}")
        
        return True
    
    def delete_record(self, record_id: int):
        """删除记录及其相关文件"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取文件路径
            cursor.execute("SELECT output_path FROM records WHERE id = ?", (record_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            output_path = result[0]
            
            # 删除记录
            cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
            conn.commit()
            
            # 尝试删除输出文件
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    print(f"已删除输出文件: {output_path}")
                except Exception as e:
                    print(f"删除输出文件失败: {str(e)}")
            
            return True
        except Exception as e:
            print(f"删除记录失败: {str(e)}")
            conn.rollback()
            return False