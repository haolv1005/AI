# backend/qa_logger.py - 简化版
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

class QALogger:
    def __init__(self, log_dir: str = "E:/sm-ai/log"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._init_daily_log()
    
    def _init_daily_log(self):
        """初始化当天的日志文件"""
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(self.log_dir, f"qa_log_{today}.json")
        
        # 如果日志文件不存在，创建空列表
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def log_qa(self, question: str, answer: str, reference_count: int = 0) -> str:
        """
        记录问答记录（简化版，无点赞/踩）
        """
        try:
            # 读取现有日志
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 生成记录ID
            record_id = f"QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(logs):04d}"
            
            # 创建记录（简化，无点赞/踩字段）
            record = {
                "id": record_id,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "question": question,
                "answer": answer,
                "reference_count": reference_count
            }
            
            # 添加记录
            logs.append(record)
            
            # 保存日志
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            return record_id
            
        except Exception as e:
            print(f"记录问答失败: {str(e)}")
            return f"ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def get_record(self, record_id: str) -> Optional[Dict]:
        """获取指定记录"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            for record in logs:
                if record["id"] == record_id:
                    return record
            return None
        except:
            return None
    
    def get_daily_stats(self) -> Dict:
        """获取当日统计（简化版）"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            if not logs:
                return {
                    "total_qa": 0
                }
            
            total_qa = len(logs)
            
            return {
                "total_qa": total_qa
            }
        except:
            return {}