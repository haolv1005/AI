# backend/database.py
import sqlite3
import os
import threading
from datetime import datetime
from pathlib import Path

thread_local = threading.local()

class Database:
    def __init__(self, db_path="data/testcase.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _get_connection(self):
        if not hasattr(thread_local, "connection"):
            thread_local.connection = sqlite3.connect(self.db_path)
            thread_local.connection.row_factory = sqlite3.Row
        return thread_local.connection
    
    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                output_filename TEXT NOT NULL,
                output_path TEXT NOT NULL,
                summary TEXT,
                decision_table TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    
    def add_record(self, original_filename, file_path, output_filename, output_path, summary, decision_table):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO records (
                original_filename, file_path, 
                output_filename, output_path, 
                summary, decision_table
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (original_filename, file_path, output_filename, output_path, summary, decision_table))
        conn.commit()
        return cursor.lastrowid
    
    def get_records(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM records ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def add_knowledge_file(self, filename, file_path):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO knowledge_files (filename, file_path)
            VALUES (?, ?)
        ''', (filename, file_path))
        conn.commit()
        return cursor.lastrowid
    
    def get_knowledge_files(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM knowledge_files ORDER BY uploaded_at DESC')
        return [dict(row) for row in cursor.fetchall()]