import pandas as pd
from datetime import datetime
import os
from typing import Dict

class TestCaseGenerator:
    def __init__(self, output_dir="E:/sm-ai/data/outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_excel(self, test_cases: str, original_filename: str) -> str:
        try:
        # 解析 AI 生成的测试用例文本为 DataFrame
        # 这里假设测试用例是以特定格式返回的，可能需要根据实际情况调整
            test_case_list = []
            for line in test_cases.split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                # 确保有足够的数据列
                    if len(parts) >= 3:
                        test_case_list.append({
                            "用例ID": parts[0],
                            "用例标题": parts[1] if len(parts) > 1 else "",
                            "前置条件": parts[2] if len(parts) > 2 else "",
                            "测试步骤": parts[3] if len(parts) > 3 else "",
                            "测试数据": parts[4] if len(parts) > 4 else "",
                            "预期结果": parts[5] if len(parts) > 5 else "",
                            "优先级": parts[6] if len(parts) > 6 else "中",
                            "状态": "未执行"
                        })
            
            df = pd.DataFrame(test_case_list)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(original_filename))[0]
            output_file = f"{base_name}_测试用例_{timestamp}.xlsx"
            output_path = os.path.join(self.output_dir, output_file)
            
            df.to_excel(output_path, index=False)
            return output_path
        except Exception as e:
            raise RuntimeError(f"生成Excel失败: {str(e)}")
    # 在Database类中添加删除方法
    def delete_knowledge_file(self, file_id: int):
        """删除知识库文件记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 先获取文件路径
        cursor.execute("SELECT file_path FROM knowledge_files WHERE id = ?", (file_id,))
        file_path = cursor.fetchone()[0]
        
        # 删除记录
        cursor.execute("DELETE FROM knowledge_files WHERE id = ?", (file_id,))
        
        # 删除向量文档
        cursor.execute("DELETE FROM vector_documents WHERE source = ?", (file_path,))
        
        conn.commit()
        return True
