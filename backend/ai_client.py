import openai
from typing import List, Dict, Tuple, Optional
import re

class AIClient:
    def __init__(self, model_name="deepseek-coder-v2", base_url="http://localhost:11434/v1", knowledge_base=None):
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key="ollama"  # Ollama 不需要真实 API 密钥
        )
        self.model_name = model_name
        self.default_max_tokens = 16384
        self.knowledge_base = knowledge_base
    
    def generate_text(self, messages: List[Dict[str, str]], temperature=0.7, max_tokens=16384) -> str:
        max_tokens = max_tokens or self.default_max_tokens
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def generate_summary(self, text: str, prompt: str) -> str:
        """生成文档总结（优化版）"""
        system_content = """你是一个专业的软件测试分析师，请根据需求文档内容生成结构化摘要：
1. **功能模块识别**：
   - 列出所有主要功能模块和子功能
   - 标注每个功能的测试优先级（高/中/低）

2. **测试点深度分析**：
   - 等价类划分：为每个输入参数明确划分有效/无效等价类
   - 边界值提取：识别所有边界条件（最小值/最大值/空值），列出具体边界值
   - 业务规则：解析所有条件判断逻辑（如：如果...则...）

3. **多维验证要素**：
   - 用户角色矩阵：列出所有用户角色及其权限差异，识别跨角色交互场景
   - 数据流验证：描述关键数据输入/输出流程，提取数据验证规则
   - 非功能需求：提取性能/安全/兼容性要求，标注特殊测试类型

4. **知识库整合**：关联知识库中相似功能的历史测试点

请使用以下格式组织摘要：
[功能模块1]
- 功能描述: [简洁说明]
- 等价类: 
  ✓ 有效: [类名1] 值范围[范围说明]
  ✓ 无效: [类名2] 值范围[范围说明]
- 边界值: 
  ✓ 最小值: [具体值]
  ✓ 最大值: [具体值]
  ✓ 特殊值: [空值/零值/越界值]
- 业务规则: [条件判断逻辑]
- 测试优先级: [高/中/低]
[功能模块2]..."""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"文档内容：{text}\n附加要求：{prompt}"}
        ]
        return self.generate_text(messages)
    
    def generate_requirement_analysis(self, summary: str) -> Tuple[str, str]:
        """生成需求分析点并进行验证（优化版）"""
        # 生成需求分析点
        analysis_content = """您作为资深测试分析师，请执行：
1. 基于文档总结，归纳所有测试点
2. 应用等价类划分法：明确每个功能模块的有效/无效等价类
3. 应用边界值法：提取所有边界条件（最小值/最大值/特殊值）

结构化输出格式：
| 功能点ID | 功能描述 | 等价类 | 边界值 | 业务规则 |
|---|---|---|---|---|
| FP001 | [描述] | 有效: [范围]<br>无效: [范围] | 最小值: [值]<br>最大值: [值] | [规则描述] |"""

        analysis_messages = [
            {"role": "system", "content": analysis_content},
            {"role": "user", "content": f"文档总结：{summary}"}
        ]
        requirement_analysis = self.generate_text(analysis_messages)
        
        # 验证需求分析点
        validation_content = """作为质量保障专家，请验证需求分析点：
1. 检查是否有遗漏的功能点
2. 确认边界值是否完整（含所有极端情况）
3. 检查等价类划分是否覆盖所有输入场景
4. 标记不明确/冲突点：[编号]问题描述

输出格式：
[验证结果]
完整度: [百分比]% (缺漏X处)
问题列表:
1. [模块]缺失[具体功能]
2. [参数]边界值未包含[值]
...
[修订建议]"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"原始总结：{summary}\n需求分析点：{requirement_analysis}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        return requirement_analysis, validation_report


        """生成决策表，整合知识库内容（优化版）"""
        # 检索知识库（保持不变）...
        
        # 决策表生成提示词
        system_content = """您作为高级测试架构师，请基于需求分析点生成测试决策表：
1. **条件分析**：
   - 功能点标识：引用分析中的功能点编号（如FP001）
   - 等价类状态：有效/无效（对应分析中的等价类划分）
   - 边界值状态：正常/边界/越界（对应分析中的边界值）
   - 用户角色：管理员/普通用户等（需覆盖所有角色）

2. **知识库整合**：
   - 自动关联相似功能的历史用例
   - 应用行业标准：等价类划分/边界值分析/因果图
   - 规避历史缺陷：引用知识库中记录的常见问题点

3. **输出格式**（表格）：
| 组合ID | 功能点 | 等价类 | 边界状态 | 用户角色 | 预期动作 | 优先级 | 知识库参考 |
|---|---|---|---|---|---|---|---|
| 1 | FP001 | 有效 | 正常 | 管理员 | 成功处理 | P0 | KB-001 |

4. **特殊要求**：
   - 必须覆盖分析中的所有功能点
   - 每个功能点需包含所有等价类组合
   - 边界状态需包含：正常/边界/越界三种情况"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求分析点：{requirement_analysis}\n{knowledge_context}\n附加要求：{prompt}"}
        ]
        return self.generate_text(messages)

    def generate_decision_table(self, requirement_analysis: str, prompt: str) -> str:
        """生成决策表，整合知识库内容（修复版）"""
        # 安全处理知识库检索
        knowledge_context = ""
        if self.knowledge_base:
            try:
                # 假设knowledge_base有search方法，返回文本结果列表
                knowledge_results = self.knowledge_base.search(requirement_analysis, k=3, full_content=True)
                knowledge_context = "\n".join([f"知识库参考 {i+1}:\n{res}" for i, res in enumerate(knowledge_results)])
            except Exception as e:
                print(f"知识库搜索失败: {str(e)}")
                knowledge_context = "知识库检索失败，将仅基于需求分析生成决策表"
        else:
            knowledge_context = "未配置知识库，将仅基于需求分析生成决策表"
        
        # 决策表生成提示词
        system_content = """您作为高级测试架构师，请基于需求分析点生成测试决策表：
1. **条件分析**：
   - 功能点标识：引用分析中的功能点编号（如FP001）
   - 等价类状态：有效/无效（对应分析中的等价类划分）
   - 边界值状态：正常/边界/越界（对应分析中的边界值）
   - 用户角色：管理员/普通用户等（需覆盖所有角色）

2. **知识库整合**：
   - 自动关联相似功能的历史用例
   - 应用行业标准：等价类划分/边界值分析/因果图
   - 规避历史缺陷：引用知识库中记录的常见问题点

3. **输出格式**（表格）：
| 组合ID | 功能点 | 等价类 | 边界状态 | 用户角色 | 预期动作 | 优先级 | 知识库参考 |
|---|---|---|---|---|---|---|---|
| 1 | FP001 | 有效 | 正常 | 管理员 | 成功处理 | P0 | KB-001 |

4. **特殊要求**：
   - 必须覆盖分析中的所有功能点
   - 每个功能点需包含所有等价类组合
   - 边界状态需包含：正常/边界/越界三种情况"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求分析点：{requirement_analysis}\n{knowledge_context}\n附加要求：{prompt}"}
        ]
        return self.generate_text(messages)
    
    def generate_test_cases(self, decision_table: str, requirement_text: str, prompt: str) -> Tuple[str, str]:
        """生成测试用例并验证（优化版）"""
        # 生成测试用例
        testcase_content = """您作为资深测试工程师，请根据决策表生成测试用例：
1. **用例结构**：
   - 用例ID: [决策表ID]_[序号] (如：DT001_01)
   - 用例标题: 功能点+等价类+边界状态组合
   - 前置条件: 执行测试前的系统状态
   - 测试步骤: 清晰、可执行的操作序列
   - 测试数据: 具体输入值（必须包含边界值）
   - 预期结果: 可验证的系统响应
   - 优先级: 继承决策表的优先级 (P0/P1/P2)

2. **覆盖要求**：
   - 每个决策表行至少生成1个测试用例
   - 边界值测试必须包含：最小值/最大值/空值/零值/越界值
   - 为每个无效等价类生成错误场景用例

输出格式（表格）：
| 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 关联决策 |
|---|---|---|---|---|---|---|---|
| DT001_01 | 登录-有效等价类-最小值测试 | 1.系统正常启动<br>2.测试账户已创建 | 1.打开功能页<br>2.输入最小值参数 | 年龄=0 | 1.成功处理<br>2.显示结果页 | P0 | DT-001 |"""

        testcase_messages = [
            {"role": "system", "content": testcase_content},
            {"role": "user", "content": f"决策表：{decision_table}\n附加要求：{prompt}"}
        ]
        test_cases = self.generate_text(testcase_messages)
        
        # 验证测试用例
        validation_content = """作为测试质量审核员，请验证测试用例：
1. 对比原始需求文档，检查是否有相悖点
2. 确认是否覆盖所有决策表条目
3. 检查边界值场景是否完整
4. 标记遗漏的需求点：[编号]需求描述

输出格式：
[验证结果]
覆盖率: [百分比]% (缺失X处)
冲突点列表:
1. [功能]与[需求编号]冲突
...
[补充用例]
| 用例ID | 用例标题 | ... | (格式同测试用例表)"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"原始需求文档片段：{requirement_text[:1000]}...\n测试用例：{test_cases}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        # 提取补充用例并合并（保持不变）...
        #return test_cases, validation_report
        
        # 提取补充用例并合并
        if "[补充用例]" in validation_report:
            supplement_start = validation_report.index("[补充用例]") + len("[补充用例]")
            supplement = validation_report[supplement_start:].strip()
            test_cases += "\n\n" + supplement
        
        return test_cases, validation_report
    
    def extract_tabular_data(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取表格数据（用于Excel生成）"""
        table_data = []
        lines = text.strip().split('\n')
        
        # 寻找表格开始
        header_index = -1
        for i, line in enumerate(lines):
            if '|' in line and '---' in line:
                header_index = i - 1  # 上一行是表头
                break
        
        if header_index < 1 or header_index + 1 >= len(lines):
            return []
        
        # 解析表头
        headers = [h.strip() for h in lines[header_index].split('|') if h.strip()]
        
        # 解析数据行
        for i in range(header_index + 2, len(lines)):
            if '|' not in line:
                continue
            values = [v.strip() for v in lines[i].split('|') if v.strip()]
            if len(values) == len(headers):
                table_data.append(dict(zip(headers, values)))
        
        return table_data