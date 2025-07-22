import openai
from typing import List, Dict
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

        messages = [
            {"role": "system", "content": "你是一个专业的软件测试分析师，请根据需求文档内容生成结构化摘要，重点关注测试相关信息："},
            {"role": "system", "content": "1. **功能模块识别**：列出所有主要功能模块和子功能，标注每个功能的测试优先级（高/中/低）"},
            {"role": "system", "content": "2. **测试点深度分析**："},
            {"role": "system", "content": "   - 等价类划分：为每个输入参数明确划分有效/无效等价类"},
            {"role": "system", "content": "   - 边界值提取：识别所有边界条件（最小值/最大值/空值），列出具体边界值"},
            {"role": "system", "content": "   - 业务规则：解析所有条件判断逻辑（如：如果...则...）"},
            {"role": "system", "content": "3. **多维验证要素**："},
            {"role": "system", "content": "   - 用户角色矩阵：列出所有用户角色及其权限差异，识别跨角色交互场景"},
            {"role": "system", "content": "   - 数据流验证：描述关键数据输入/输出流程，提取数据验证规则"},
            {"role": "system", "content": "   - 非功能需求：提取性能/安全/兼容性要求，标注特殊测试类型"},
            {"role": "system", "content": "4. **知识库整合**：关联知识库中相似功能的历史测试点"},
            {"role": "system", "content": "请使用以下格式组织摘要："},
            {"role": "system", "content": "[功能模块1]"},
            {"role": "system", "content": "- 功能描述: [简洁说明]"},
            {"role": "system", "content": "- 等价类: "},
            {"role": "system", "content": "  ✓ 有效: [类名1] 值范围[范围说明]"},
            {"role": "system", "content": "  ✓ 无效: [类名2] 值范围[范围说明]"},
            {"role": "system", "content": "- 边界值: "},
            {"role": "system", "content": "  ✓ 最小值: [具体值]"},
            {"role": "system", "content": "  ✓ 最大值: [具体值]"},
            {"role": "system", "content": "  ✓ 特殊值: [空值/零值/越界值]"},
            {"role": "system", "content": "- 业务规则: [条件判断逻辑]"},
            {"role": "system", "content": "- 测试优先级: [高/中/低]"},
            {"role": "system", "content": "[功能模块2]..."},
            {"role": "user", "content": f"文档内容：{text}\n\n请根据以下要求总结文档：{prompt}"}
            
        ]
        return self.generate_text(messages)
    def generate_decision_table(self, summary: str, prompt: str) -> str:
        knowledge_context = ""
        if self.knowledge_base:
            try:
                knowledge_results = self.knowledge_base.search(summary, k=3)
                knowledge_context = "\n".join(knowledge_results)
            except Exception as e:
                print(f"知识库搜索失败: {str(e)}")
        
        enhanced_prompt = f"""
        {prompt}
        
        {knowledge_context and "知识库参考内容:" or ""}
        {knowledge_context}
        """
        
        messages = [
            {"role": "system", "content": "你是一个高级测试架构师，请基于需求摘要和知识库内容生成完整的测试决策表："},
            {"role": "system", "content": "1. **条件分析**："},
            {"role": "system", "content": "   - 功能点标识：引用总结中的功能点编号（如FP001）"},
            {"role": "system", "content": "   - 等价类状态：有效/无效（对应总结中的等价类划分）"},
            {"role": "system", "content": "   - 边界值状态：正常/边界/越界（对应总结中的边界值）"},
            {"role": "system", "content": "   - 用户角色：管理员/普通用户等（需覆盖所有角色）"},
            {"role": "system", "content": "   - 系统状态：正常/超载/故障等"},

            {"role": "system", "content": "2. **动作定义**："},
            {"role": "system", "content": "   - 预期输出：成功处理/错误提示/权限拒绝等"},
            {"role": "system", "content": "   - 边界处理：明确边界值的具体响应（如：最小值→特殊提示）"},
            {"role": "system", "content": "   - 错误代码：为每种无效场景分配唯一错误码"},

            {"role": "system", "content": "3. **知识库整合**："},
            {"role": "system", "content": "   - 自动关联相似功能的历史用例（知识库ID）"},
            {"role": "system", "content": "   - 应用行业标准：等价类划分/边界值分析/因果图"},
            {"role": "system", "content": "   - 规避历史缺陷：引用知识库中记录的常见问题点"},

            {"role": "system", "content": "4. **决策表结构**：使用表格形式呈现，包含："},
            {"role": "system", "content": "   | 组合ID | 功能点 | 等价类 | 边界状态 | 用户角色 | 系统状态 | → | 预期动作 | 错误码 | 优先级 | 知识库参考 |"},
            {"role": "system", "content": "   |---|---|---|---|---|---|---|---|---|---|---|"},
            {"role": "system", "content": "   | 1 | FP001 | 有效 | 正常 | 管理员 | 正常 | → | 成功处理 | - | P0 | KB-2023-001 |"},
            {"role": "system", "content": "   | 2 | FP001 | 无效 | 越界 | 普通用户 | 超载 | → | 错误提示 | E1001 | P1 | KB-2023-005 |"},

            {"role": "system", "content": "5. **特殊要求**："},
            {"role": "system", "content": "   - 必须覆盖总结中的所有功能点"},
            {"role": "system", "content": "   - 每个功能点需包含所有等价类组合"},
            {"role": "system", "content": "   - 边界状态需包含：正常/边界/越界三种情况"},
            {"role": "system", "content": "   - 高风险场景标注为P0（核心功能）"},
            {"role": "system", "content": "   - 为空值/零值等特殊边界分配独立测试行"},

            {"role": "user", "content": f"文档总结：{summary}\n\n请根据以下要求生成决策表：{prompt}"}
        ]
        
        return self.generate_text(messages)
    def generate_test_cases(self, decision_table: str, prompt: str) -> str:

        messages = [
            {"role": "system", "content": "你是一个资深测试工程师，请根据决策表生成详细的测试用例："},
            {"role": "system", "content": "1. **用例结构**："},
            {"role": "system", "content": "   - 用例ID: [决策表ID]_[序号] (如：DT001_01)"},
            {"role": "system", "content": "   - 用例标题: 功能点+等价类+边界状态组合 (如：FP001-有效等价类-边界值测试)"},
            {"role": "system", "content": "   - 前置条件: 执行测试前的系统状态（包含特殊状态）"},
            {"role": "system", "content": "   - 测试步骤: 清晰、可执行的操作序列（包含边界值操作）"},
            {"role": "system", "content": "   - 测试数据: 具体输入值（必须包含边界值具体数值）"},
            {"role": "system", "content": "   - 预期结果: 可验证的系统响应（包含边界值响应细节）"},
            {"role": "system", "content": "   - 优先级: 继承决策表的优先级 (P0/P1/P2)"},
            {"role": "system", "content": "   - 关联决策: 决策表组合ID (如：DT-001)"},
            {"role": "system", "content": "   - 边界值参数: 标记使用的边界参数及具体值"},

            {"role": "system", "content": "2. **覆盖要求**："},
            {"role": "system", "content": "   - 每个决策表行至少生成1个测试用例"},
            {"role": "system", "content": "   - 边界值测试必须包含：最小值/最大值/空值/零值/越界值"},
            {"role": "system", "content": "   - 为每个无效等价类生成错误场景用例"},
            {"role": "system", "content": "   - 包含正向(PASS)和负向(FAIL)场景"},

            {"role": "system", "content": "3. **特殊场景强化**："},
            {"role": "system", "content": "   - 边界值组合场景：同时触发多个边界条件"},
            {"role": "system", "content": "   - 状态迁移场景：系统状态变化时的边界行为"},
            {"role": "system", "content": "   - 错误恢复场景：边界值导致的异常后的恢复流程"},
            {"role": "system", "content": "   - 并发边界场景：多用户同时操作边界值"},

            {"role": "system", "content": "4. **输出格式**：使用表格形式呈现，准备Excel兼容格式"},
            {"role": "system", "content": "请使用以下格式："},
            {"role": "system", "content": "| 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 关联决策 | 边界值参数 |"},
            {"role": "system", "content": "|---|---|---|---|---|---|---|---|---|"},
            {"role": "system", "content": "| DT001_01 | FP001-有效等价类-最小值测试 | 1.系统正常启动<br>2.测试账户已创建 | 1.打开功能页<br>2.输入最小值参数<br>3.提交表单 | 年龄=0 | 1.成功处理<br>2.显示结果页 | P0 | DT-001 | 年龄=0 |"},
            {"role": "system", "content": "| DT001_02 | FP001-无效等价类-越界测试 | 1.系统正常启动<br>2.测试账户已创建 | 1.打开功能页<br>2.输入越界值<br>3.提交表单 | 年龄=151 | 1.显示错误提示<br>2.错误码:E1001 | P1 | DT-001 | 年龄=151 |"},

            {"role": "user", "content": f"决策表：{decision_table}\n\n请根据以下要求生成测试用例：{prompt}"}
        ]
        return self.generate_text(messages)