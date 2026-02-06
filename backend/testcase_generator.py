import pandas as pd
from datetime import datetime
import os
import re
from typing import Dict, List
import json

class TestCaseGenerator:
    def __init__(self, output_dir="E:/sm-ai/data/outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_excel(self, test_cases: str, original_filename: str) -> str:
        try:
            # 尝试使用新的解析方法
            test_case_list = self._parse_enhanced_test_cases(test_cases)
            
            # 创建DataFrame
            df = pd.DataFrame(test_case_list)
            
            # 确保必要的列存在
            required_columns = ['用例ID', '用例标题', '前置条件', '测试步骤', '测试数据', '预期结果', '优先级']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # 重新排列列顺序
            columns_order = ['用例ID', '用例标题', '前置条件', '测试步骤', '测试数据', 
                           '预期结果', '优先级', '状态', '执行人', '执行时间', '备注']
            
            # 添加缺失的列
            for col in columns_order:
                if col not in df.columns:
                    if col in ['状态', '执行人', '执行时间']:
                        df[col] = ''
                    elif col == '备注':
                        df[col] = '智能问答生成'
            
            # 按指定顺序排列列
            df = df[columns_order]
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(original_filename))[0]
            output_file = f"{base_name}_测试用例_{timestamp}.xlsx"
            output_path = os.path.join(self.output_dir, output_file)
            
            # 保存到Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='测试用例', index=False)
                
                # 添加统计信息工作表
                stats_df = self._generate_statistics(df)
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            
            return output_path
        except Exception as e:
            raise RuntimeError(f"生成Excel失败: {str(e)}")
    
    def _parse_enhanced_test_cases(self, test_cases: str) -> List[Dict]:
        """增强的测试用例解析方法"""
        test_case_list = []
        
        try:
            print(f"开始解析测试用例，内容长度: {len(test_cases)}")
            
            # 方法1: 解析Markdown表格格式
            test_case_list = self._parse_markdown_table(test_cases)
            
            # 方法2: 如果没有解析到，尝试其他格式
            if not test_case_list:
                test_case_list = self._parse_text_format(test_cases)
            
            # 方法3: 如果还是没有，使用备用方案
            if not test_case_list:
                test_case_list = self._parse_fallback_test_cases(test_cases)
            
            print(f"成功解析到 {len(test_case_list)} 个测试用例")
            
        except Exception as e:
            print(f"解析测试用例时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            test_case_list = self._parse_fallback_test_cases(test_cases)
        
        return test_case_list
    
    def _parse_markdown_table(self, content: str) -> List[Dict]:
        """解析Markdown表格格式的测试用例"""
        test_case_list = []
        
        try:
            lines = content.split('\n')
            in_table = False
            table_header = []
            table_data = []
            
            for line in lines:
                line = line.strip()
                
                # 检测表格开始
                if line.startswith('|') and ('用例ID' in line or '测试用例' in line):
                    in_table = True
                    # 解析表头
                    table_header = [cell.strip() for cell in line.split('|')[1:-1]]
                    continue
                
                # 检测表格分隔线
                if in_table and line.startswith('|') and '---' in line:
                    continue
                
                # 解析表格数据行
                if in_table and line.startswith('|') and line.endswith('|'):
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    
                    # 确保单元格数量与表头匹配
                    if len(cells) >= len(table_header):
                        row_data = {}
                        for i, header in enumerate(table_header):
                            if i < len(cells):
                                row_data[header] = cells[i]
                            else:
                                row_data[header] = ''
                        
                        # 将中文列名映射到标准列名
                        mapped_case = self._map_column_names(row_data)
                        if mapped_case:
                            test_case_list.append(mapped_case)
                    else:
                        # 单元格不足，使用已有数据
                        row_data = {}
                        for i in range(len(table_header)):
                            if i < len(cells):
                                row_data[table_header[i]] = cells[i]
                            else:
                                row_data[table_header[i]] = ''
                        
                        mapped_case = self._map_column_names(row_data)
                        if mapped_case:
                            test_case_list.append(mapped_case)
                
                # 表格结束
                elif in_table and not line.startswith('|'):
                    in_table = False
        
        except Exception as e:
            print(f"解析Markdown表格失败: {str(e)}")
        
        return test_case_list
    
    def _map_column_names(self, row_data: Dict) -> Dict:
        """将中文列名映射到标准列名"""
        column_mapping = {
            '用例ID': ['用例ID', 'ID', '测试用例ID', 'Case ID'],
            '用例标题': ['用例标题', '标题', '测试用例标题', 'Case Title'],
            '前置条件': ['前置条件', '前提条件', 'Precondition'],
            '测试步骤': ['测试步骤', '步骤', '操作步骤', 'Test Steps'],
            '测试数据': ['测试数据', '数据', '输入数据', 'Test Data'],
            '预期结果': ['预期结果', '期望结果', 'Expected Result'],
            '优先级': ['优先级', '优先级别', 'Priority'],
            '备注': ['备注', '说明', '注释', 'Remark']
        }
        
        mapped_case = {
            '用例ID': '',
            '用例标题': '',
            '前置条件': '',
            '测试步骤': '',
            '测试数据': '',
            '预期结果': '',
            '优先级': 'P1',
            '状态': '未执行',
            '执行人': '',
            '执行时间': '',
            '备注': '智能问答生成'
        }
        
        # 遍历映射关系
        for standard_col, possible_names in column_mapping.items():
            for name in possible_names:
                if name in row_data and row_data[name]:
                    mapped_case[standard_col] = row_data[name]
                    break
        
        # 如果用例ID为空，生成一个
        if not mapped_case['用例ID'] and mapped_case['用例标题']:
            # 从标题生成ID
            title_hash = hash(mapped_case['用例标题']) % 10000
            mapped_case['用例ID'] = f"TC-{abs(title_hash):04d}"
        
        # 确保至少有一个标识
        if mapped_case['用例ID'] or mapped_case['用例标题']:
            return mapped_case
        
        return None
    
    def _parse_text_format(self, content: str) -> List[Dict]:
        """解析文本格式的测试用例"""
        test_case_list = []
        
        try:
            # 分割不同的测试用例
            sections = re.split(r'测试用例\s*\d+[\.:：]|\n---\n|\n###\s+', content)
            
            for section in sections:
                if not section.strip():
                    continue
                
                test_case = self._extract_test_case_from_text(section)
                if test_case:
                    test_case_list.append(test_case)
        
        except Exception as e:
            print(f"解析文本格式失败: {str(e)}")
        
        return test_case_list
    
    def _extract_test_case_from_text(self, text: str) -> Dict:
        """从文本中提取单个测试用例"""
        try:
            test_case = {
                '用例ID': '',
                '用例标题': '',
                '前置条件': '',
                '测试步骤': '',
                '测试数据': '',
                '预期结果': '',
                '优先级': 'P1',
                '状态': '未执行',
                '执行人': '',
                '执行时间': '',
                '备注': '文本解析生成'
            }
            
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 提取用例ID
                if re.match(r'^(?:用例)?ID[：:]', line):
                    match = re.search(r'ID[：:]\s*(.+)', line)
                    if match:
                        test_case['用例ID'] = match.group(1).strip()
                
                # 提取标题
                elif re.match(r'^(?:用例)?标题[：:]', line):
                    match = re.search(r'标题[：:]\s*(.+)', line)
                    if match:
                        test_case['用例标题'] = match.group(1).strip()
                
                # 提取前置条件
                elif re.match(r'^前置条件[：:]', line):
                    match = re.search(r'前置条件[：:]\s*(.+)', line)
                    if match:
                        test_case['前置条件'] = match.group(1).strip()
                
                # 提取测试步骤
                elif re.match(r'^测试步骤[：:]', line):
                    match = re.search(r'测试步骤[：:]\s*(.+)', line, re.DOTALL)
                    if match:
                        test_case['测试步骤'] = match.group(1).strip()
                
                # 提取测试数据
                elif re.match(r'^测试数据[：:]', line):
                    match = re.search(r'测试数据[：:]\s*(.+)', line)
                    if match:
                        test_case['测试数据'] = match.group(1).strip()
                
                # 提取预期结果
                elif re.match(r'^预期结果[：:]', line):
                    match = re.search(r'预期结果[：:]\s*(.+)', line, re.DOTALL)
                    if match:
                        test_case['预期结果'] = match.group(1).strip()
                
                # 提取优先级
                elif re.match(r'^优先级[：:]', line):
                    match = re.search(r'优先级[：:]\s*(.+)', line)
                    if match:
                        test_case['优先级'] = match.group(1).strip()
            
            # 如果标题为空但内容有，生成标题
            if not test_case['用例标题'] and text.strip():
                # 取前50个字符作为标题
                preview = text.strip()[:50]
                test_case['用例标题'] = f"测试用例: {preview}..."
            
            # 如果ID为空，生成ID
            if not test_case['用例ID']:
                title_hash = hash(test_case['用例标题']) % 10000
                test_case['用例ID'] = f"TC-{abs(title_hash):04d}"
            
            return test_case
            
        except Exception as e:
            print(f"提取测试用例信息失败: {str(e)}")
            return None
    
    def _parse_fallback_test_cases(self, test_cases: str) -> List[Dict]:
        """备用解析方案"""
        test_case_list = []
        
        try:
            # 简单解析，每10行作为一个测试用例
            lines = test_cases.split('\n')
            
            for i in range(0, len(lines), 10):
                if i + 10 <= len(lines):
                    test_case_text = '\n'.join(lines[i:i+10])
                    
                    # 提取关键信息
                    title_match = re.search(r'用例[标题|名称][:：]\s*(.+)', test_cases)
                    title = title_match.group(1) if title_match else f"测试用例 {i//10 + 1}"
                    
                    test_case_list.append({
                        '用例ID': f"TC-{i//10 + 1:03d}",
                        '用例标题': title,
                        '前置条件': '见测试用例文档',
                        '测试步骤': '1. 准备测试环境\n2. 执行测试\n3. 验证结果',
                        '测试数据': '见测试用例文档',
                        '预期结果': '功能正常',
                        '优先级': 'P1',
                        '状态': '未执行',
                        '执行人': '',
                        '执行时间': '',
                        '备注': '智能问答生成，需要人工完善'
                    })
            
            # 如果什么都没解析到，至少创建一个测试用例
            if not test_case_list:
                test_case_list.append({
                    '用例ID': 'TC-001',
                    '用例标题': '智能问答生成的测试用例',
                    '前置条件': '系统正常运行',
                    '测试步骤': '请参考生成的测试用例文档',
                    '测试数据': '请参考生成的测试用例文档',
                    '预期结果': '功能符合预期',
                    '优先级': 'P1',
                    '状态': '未执行',
                    '执行人': '',
                    '执行时间': '',
                    '备注': '由智能问答系统生成'
                })
        
        except Exception as e:
            print(f"备用解析方案出错: {str(e)}")
        
        return test_case_list
    
    def _generate_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成统计信息"""
        stats_data = []
        
        # 优先级统计
        if '优先级' in df.columns:
            priority_counts = df['优先级'].value_counts().to_dict()
            for priority, count in priority_counts.items():
                stats_data.append({
                    '统计项': f'{priority}优先级用例数',
                    '数值': count,
                    '百分比': f'{count/len(df)*100:.1f}%'
                })
        
        # 状态统计
        if '状态' in df.columns:
            status_counts = df['状态'].value_counts().to_dict()
            for status, count in status_counts.items():
                stats_data.append({
                    '统计项': f'{status}状态用例数',
                    '数值': count,
                    '百分比': f'{count/len(df)*100:.1f}%'
                })
        
        # 总体统计
        stats_data.append({
            '统计项': '总用例数',
            '数值': len(df),
            '百分比': '100%'
        })
        
        stats_data.append({
            '统计项': '生成时间',
            '数值': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '百分比': '-'
        })
        
        stats_data.append({
            '统计项': '数据来源',
            '数值': '智能问答生成',
            '百分比': '-'
        })
        
        return pd.DataFrame(stats_data)
    
    # 为了向后兼容，添加旧的解析方法