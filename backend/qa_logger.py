# backend/qa_logger.py
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback

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
        记录问答记录
        
        Args:
            question: 用户问题
            answer: AI回答
            reference_count: 参考数量
            
        Returns:
            记录ID
        """
        try:
            # 读取现有日志
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 生成记录ID
            record_id = f"QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(logs):04d}"
            
            # 创建记录
            record = {
                "id": record_id,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "question": question,
                "answer": answer,
                "reference_count": reference_count,
                "upvotes": 0,
                "downvotes": 0,
                "feedback": []  # 存储详细的反馈记录
            }
            
            # 添加记录
            logs.append(record)
            
            # 保存日志
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            # 更新每日统计
            self._update_daily_stats()
            
            return record_id
            
        except Exception as e:
            print(f"记录问答失败: {str(e)}")
            return f"ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def add_feedback(self, record_id: str, feedback_type: str, user_ip: str = "unknown") -> bool:
        """
        添加反馈（点赞/踩）
        
        Args:
            record_id: 记录ID
            feedback_type: 'upvote' 或 'downvote'
            user_ip: 用户标识（用于防止重复投票）
            
        Returns:
            是否成功
        """
        try:
            # 读取日志
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 查找记录
            for record in logs:
                if record["id"] == record_id:
                    # 检查用户是否已经反馈过
                    for fb in record.get("feedback", []):
                        if fb.get("user") == user_ip:
                            # 用户已经反馈过，可以修改原来的反馈
                            old_type = fb.get("type")
                            if old_type == feedback_type:
                                return False  # 相同反馈，不重复记录
                            else:
                                # 修改反馈类型
                                if old_type == "upvote":
                                    record["upvotes"] = max(0, record.get("upvotes", 0) - 1)
                                elif old_type == "downvote":
                                    record["downvotes"] = max(0, record.get("downvotes", 0) - 1)
                                fb["type"] = feedback_type
                                fb["timestamp"] = datetime.now().isoformat()
                    
                    # 添加新反馈
                    feedback_entry = {
                        "user": user_ip,
                        "type": feedback_type,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if "feedback" not in record:
                        record["feedback"] = []
                    record["feedback"].append(feedback_entry)
                    
                    # 更新统计
                    if feedback_type == "upvote":
                        record["upvotes"] = record.get("upvotes", 0) + 1
                    elif feedback_type == "downvote":
                        record["downvotes"] = record.get("downvotes", 0) + 1
                    
                    # 保存日志
                    with open(self.log_file, 'w', encoding='utf-8') as f:
                        json.dump(logs, f, ensure_ascii=False, indent=2)
                    
                    # 更新每日统计
                    self._update_daily_stats()
                    
                    return True
            
            return False  # 记录未找到
            
        except Exception as e:
            print(f"添加反馈失败: {str(e)}")
            return False
    
    def _update_daily_stats(self):
        """更新每日统计Excel文件"""
        try:
            # 读取当天所有日志
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            if not logs:
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(logs)
            
            # 添加问题长度、答案长度等统计信息
            df['question_length'] = df['question'].apply(len)
            df['answer_length'] = df['answer'].apply(len)
            
            # 计算反馈率
            df['feedback_rate'] = df.apply(
                lambda row: ((row.get('upvotes', 0) + row.get('downvotes', 0)) / 
                           max(1, row['reference_count'])), axis=1
            )
            
            # 计算净反馈（点赞-踩）
            df['net_feedback'] = df.apply(
                lambda row: row.get('upvotes', 0) - row.get('downvotes', 0), axis=1
            )
            
            # 保存为Excel
            excel_file = self.log_file.replace('.json', '.xlsx')
            df.to_excel(excel_file, index=False)
            
            # 生成汇总统计
            self._generate_summary_stats(df)
            
        except Exception as e:
            print(f"更新统计失败: {str(e)}")
    
    def _generate_summary_stats(self, df: pd.DataFrame):
        """生成汇总统计"""
        try:
            summary = {
                "统计日期": datetime.now().strftime("%Y-%m-%d"),
                "总问答数": len(df),
                "总点赞数": df['upvotes'].sum(),
                "总点踩数": df['downvotes'].sum(),
                "平均点赞数": df['upvotes'].mean(),
                "平均点踩数": df['downvotes'].mean(),
                "最高点赞记录": df.loc[df['upvotes'].idxmax()]['id'] if not df.empty else "无",
                "最高点赞数": df['upvotes'].max() if not df.empty else 0,
                "平均问题长度": df['question_length'].mean(),
                "平均答案长度": df['answer_length'].mean(),
                "平均参考数量": df['reference_count'].mean(),
                "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 保存汇总统计
            summary_file = os.path.join(self.log_dir, f"summary_{datetime.now().strftime('%Y%m%d')}.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            # 生成Excel汇总
            summary_df = pd.DataFrame([summary])
            summary_excel = os.path.join(self.log_dir, f"summary_{datetime.now().strftime('%Y%m%d')}.xlsx")
            summary_df.to_excel(summary_excel, index=False)
            
        except Exception as e:
            print(f"生成汇总统计失败: {str(e)}")
    
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
        """获取当日统计"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            if not logs:
                return {
                    "total_qa": 0,
                    "total_upvotes": 0,
                    "total_downvotes": 0,
                    "avg_upvotes": 0,
                    "avg_downvotes": 0
                }
            
            total_qa = len(logs)
            total_upvotes = sum(r.get("upvotes", 0) for r in logs)
            total_downvotes = sum(r.get("downvotes", 0) for r in logs)
            
            return {
                "total_qa": total_qa,
                "total_upvotes": total_upvotes,
                "total_downvotes": total_downvotes,
                "avg_upvotes": total_upvotes / max(1, total_qa),
                "avg_downvotes": total_downvotes / max(1, total_qa),
                "feedback_rate": (total_upvotes + total_downvotes) / max(1, total_qa)
            }
        except:
            return {}
    
    def get_question_frequency(self, days: int = 7) -> Dict:
        """获取问题频率统计"""
        try:
            all_logs = []
            date_format = "%Y%m%d"
            
            # 获取最近days天的日志
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                log_file = os.path.join(self.log_dir, f"qa_log_{date.strftime(date_format)}.json")
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                    all_logs.extend(logs)
            
            # 统计问题频率
            question_count = {}
            for log in all_logs:
                question = log.get("question", "")
                if question:
                    question_count[question] = question_count.get(question, 0) + 1
            
            # 按频率排序
            sorted_questions = sorted(question_count.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "total_unique_questions": len(question_count),
                "most_frequent_questions": sorted_questions[:10],  # 前10个最常问的问题
                "question_frequency": dict(sorted_questions)
            }
        except Exception as e:
            print(f"获取问题频率失败: {str(e)}")
            return {}
    
    def export_monthly_report(self, year: int = None, month: int = None):
        """导出月度报告"""
        try:
            if year is None:
                year = datetime.now().year
            if month is None:
                month = datetime.now().month
            
            # 查找该月的所有日志文件
            monthly_logs = []
            for day in range(1, 32):
                try:
                    date = datetime(year, month, day)
                    log_file = os.path.join(self.log_dir, f"qa_log_{date.strftime('%Y%m%d')}.json")
                    if os.path.exists(log_file):
                        with open(log_file, 'r', encoding='utf-8') as f:
                            logs = json.load(f)
                        monthly_logs.extend(logs)
                except ValueError:
                    break  # 无效日期
            
            if not monthly_logs:
                return False
            
            # 创建月度报告
            df = pd.DataFrame(monthly_logs)
            report_file = os.path.join(self.log_dir, f"monthly_report_{year:04d}_{month:02d}.xlsx")
            
            # 使用Excel写入器创建多个工作表
            with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
                # 原始数据
                df.to_excel(writer, sheet_name='原始数据', index=False)
                
                # 每日统计
                daily_stats = df.groupby('date').agg({
                    'id': 'count',
                    'upvotes': 'sum',
                    'downvotes': 'sum',
                    'reference_count': 'mean'
                }).rename(columns={'id': '问答数量'})
                daily_stats.to_excel(writer, sheet_name='每日统计')
                
                # 问题频率
                question_freq = df['question'].value_counts().head(20)
                question_freq.to_excel(writer, sheet_name='热门问题')
                
                # 反馈统计
                feedback_stats = pd.DataFrame({
                    '指标': ['总问答数', '总点赞数', '总点踩数', '平均点赞数', '平均点踩数', '反馈率'],
                    '数值': [
                        len(df),
                        df['upvotes'].sum(),
                        df['downvotes'].sum(),
                        df['upvotes'].mean(),
                        df['downvotes'].mean(),
                        (df['upvotes'].sum() + df['downvotes'].sum()) / len(df)
                    ]
                })
                feedback_stats.to_excel(writer, sheet_name='反馈统计', index=False)
            
            return True
            
        except Exception as e:
            print(f"导出月度报告失败: {str(e)}")
            return False