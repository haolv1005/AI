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
            {"role": "system", "content": " 你是一个专业的软件测试分析师，请根据以下需求文档内容生成结构化摘要，重点关注测试相关信息：。"},
            {"role": "system", "content": " 1. **功能模块识别**：列出所有主要功能模块和子功能,标注每个功能的优先级（高/中/低）"},
            {"role": "system", "content": " 2. **业务规则提取**：提取所有条件判断逻辑（如：如果...则...）,识别所有边界条件（如：最小值、最大值、空值处理）"},
            {"role": "system", "content": " 3. **用户角色与权限**：列出所有用户角色及其权限差异,识别跨角色交互场景"},
            {"role": "system", "content": " 4. **数据流分析**：描述关键数据输入/输出流程,识别数据验证规则"},
            {"role": "system", "content": " 5. **非功能需求**：提取性能、安全、兼容性等要求,标注特殊测试需求（如：压力测试、安全测试）"},
            {"role": "system", "content": " 请使用以下格式组织摘要：[功能模块1]- 功能描述: - 业务规则: - 输入数据: - 输出数据: - 边界条件: - 测试优先级: [功能模块2]..."},
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
            {"role": "system", "content": "1. **条件分析**：列出所有输入条件（至少包含：用户角色、输入数据、系统状态）为每个条件定义可能取值（如：管理员/普通用户、有效数据/无效数据）"},
            {"role": "system", "content": "2. **动作定义**：列出所有可能的系统响应（成功处理、错误提示、权限拒绝等）定义边界条件的处理方式"},
            {"role": "system", "content": "3. **知识库整合**：参考{enhanced_prompt}的类似功能测试案例应用行业标准测试模式（如：等价类划分、边界值分析）考虑历史缺陷中的常见问题点"},
            {"role": "system", "content": "4. **决策表结构**：使用表格形式呈现列：条件组合（所有可能组合）行：条件项 + 动作项"},
            {"role": "system", "content": "5. **特殊要求**：确保覆盖所有有效和无效组合标记高风险场景为每个决策添加测试优先级（P0/P1/P2）"},
             {"role": "system", "content": "请使用以下格式：| 条件组合# | 用户角色 | 输入数据 | 系统状态 | → | 预期动作 | 测试优先级 | 知识库参考 ||---|---|---|---|---|---|---|---|| 1 | 管理员 | 有效数据 | 正常 | → | 成功处理 | P0 | KB-2023-001 || 2 | 普通用户 | 无效数据 | 超载 | → | 错误提示 | P1 | KB-2023-005 |"},
            {"role": "user", "content": f"文档总结：{summary}\n\n请根据以下要求生成决策表：{prompt}"}
        ]
        
        return self.generate_text(messages)
    def generate_test_cases(self, decision_table: str, prompt: str) -> str:

        messages = [
            {"role": "system", "content": "你是一个资深测试工程师，请根据决策表生成详细的测试用例："},
            {"role": "system", "content": "1. **用例结构**：用例ID: 模块_功能_序号用例标题:简洁描述测试场景前置条件: 执行测试前的系统状态测试步骤: 清晰、可执行的操作序列测试数据: 具体输入值（包括边界值）预期结果: 可验证的系统响应优先级: 继承决策表的优先级关联需求: 链接到原始需求"},
            {"role": "system", "content": "2. **覆盖要求**：为决策表中的每个条件组合生成至少一个用例包含正向和负向测试场景添加边界值测试用例"},
            {"role": "system", "content": "3. **特殊场景**：跨模块交互场景并发测试场景错误恢复场景"},
            {"role": "system", "content": "4. **输出格式**：使用表格形式呈现准备Excel兼容格式"},
            {"role": "system", "content": "请使用以下格式：| 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 关联需求 ||---|---|---|---|---|---|---|---|| LOGIN_001 | 管理员正常登录 | 1. 系统已启动2. 管理员账号已注册 | 1. 打开登录页2. 输入用户名3. 输入密码4. 点击登录 | 用户名: admin密码: P@ssw0rd | 1. 跳转到仪表盘2. 显示欢迎消息 | P0 | REQ-001 || LOGIN_002 | 错误密码登录 | 1. 系统已启动2. 管理员账号已注册 | ... | 密码: wrong | 1. 显示错误提示2. 停留在登录页 | P1 | REQ-001 |"},
            {"role": "user", "content": f"决策表：{decision_table}\n\n请根据以下要求生成测试用例：{prompt}"}
        ]
        return self.generate_text(messages)