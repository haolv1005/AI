import openai
from typing import List, Dict, Tuple, Optional
import re
import traceback
import datetime
import jieba  # 需要安装: pip install jieba
import os

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
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI生成失败: {str(e)}")
            return f"生成失败: {str(e)}"
    
    # 第一步：生成文档总结
    def enhanced_generate_summary_step(self, text: str) -> str:
        """第一步：全面需求文档分析，不删减内容"""
        system_content = """作为专业软件测试分析师，请分析上传的需求文档，按以下结构化格式输出分析结果：

        # [主功能模块名称]

        ## [子功能模块1名称]
        **用户角色**：[主态/客态/游客/登录用户/管理员/房主等]
        **场景分析**：
        - **情况A**：[场景条件描述]
        - 操作A：[具体操作] → 等价类：[有效/无效操作类型]
        - 操作B：[具体操作] → 等价类：[有效/无效操作类型]
        **边界值考虑**：[相关数据项的边界条件描述]

        ## [子功能模块2名称]
        **用户角色**：[主态/客态/游客/登录用户/管理员/房主等]
        **场景分析**：
        - **情况B**：[场景条件描述]
        - 操作C：[具体操作] → 等价类：[有效/无效操作类型]
        - 操作D：[具体操作] → 等价类：[有效/无效操作类型]
        **边界值考虑**：[相关数据项的边界条件描述]

        # [下一个主功能模块名称]

        [...继续按上述模式分析...]

        **分析要点：**
        1. 识别所有主要功能模块和子模块，按层级组织
        2. 明确每个功能模块涉及的用户角色类型
        3. 针对每个子功能模块，分析不同的使用场景（情况）
        4. 在每个场景下，识别可能的用户操作并标注等价类
        5. 列出需要考虑边界值的数据项

        **术语说明：**
        - 主态：内容创建者、功能发起方
        - 客态：内容消费者、功能参与方
        - 等价类：有效操作、无效操作、异常操作等类型
        - 边界值：数据范围、数量限制、时间阈值等边界条件"""
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求文档完整内容：{text}"}
        ]
        return self.generate_text(messages)

    def enhanced_generate_test_points_step(self, summary: str) -> Tuple[str, str]:
        """第二步：基于需求分析生成测试点文档"""
        # 生成测试点
        testpoint_content = """您作为资深测试工程师，请基于需求分析文档生成详细的测试点文档。

要求：
1. **测试点提取**：从需求分析中提取所有可测试的点
2. **不需要考虑的模块**：有关性能以及安全性测试的内容完全不需要
3. **测试深度**：每个测试点要明确测试目的和验证内容
4. **覆盖完整性**：确保覆盖所有需求模块

输出格式：
# 测试点文档

## 1. 功能测试点
### 1.1 [功能点一]
| 测试点描述 | 验证内容 | 预期 |
|------------|----------|--------|
| [执行操作1] | [数值1] | 数值增加正确 |
| [执行操作1] | [数值2] | 内容显示正确 |

### 1.2 [功能点二]
...

"""

        testpoint_messages = [
            {"role": "system", "content": testpoint_content},
            {"role": "user", "content": f"需求分析文档：{summary}"}
        ]
        test_points = self.generate_text(testpoint_messages)
        
        # 验证测试点
        validation_content = """作为测试架构师，请验证测试点文档：
1. 检查是否覆盖所有需求模块
2. 确认测试点的可测试性和明确性
3. 检查优先级分配是否合理
4. 标记遗漏的测试场景

输出格式：
[验证结果]
覆盖率: [百分比]% (缺漏X处)
问题列表:
1. [模块]缺失[具体测试点]
2. [测试点]描述不清晰
...
[改进建议]"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"需求分析：{summary}\n测试点文档：{test_points}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        return test_points, validation_report

    def enhanced_generate_decision_table_step(self, test_points: str) -> str:
        """第三步：基于测试点生成详细决策表"""
        # 检索知识库获取测试设计经验
        knowledge_context = ""
        if self.knowledge_base:
            try:
                # 搜索测试设计相关的知识
                search_query = "测试用例设计 等价类 边界值 决策表 测试场景"
                knowledge_results = self.knowledge_base.search(search_query, k=3)
                
                if knowledge_results:
                    knowledge_context = "测试设计知识库参考:\n"
                    for i, (content, metadata) in enumerate(knowledge_results):
                        source = metadata.get('source', '未知来源')
                        knowledge_context += f"\n--- 参考 {i+1} ({source}) ---\n{content}\n"
            except Exception as e:
                knowledge_context = f"知识库检索出错: {str(e)}"
        
        system_content = """您作为测试设计专家，请基于测试点生成详细的测试决策表。

要求：
1. **决策表结构**：包含条件桩、动作桩和规则
2. **条件覆盖**：每个测试点都要生成对应的条件组合
3. **动作明确**：每个条件组合对应明确的预期动作
4. **测试场景**：考虑正常、边界、异常各种场景

输出格式：
# 测试决策表

## 决策表：[功能模块名称]

### 条件桩
- C1: [条件1描述]
- C2: [条件2描述] 
- C3: [条件3描述]

### 动作桩
- A1: [动作1描述]
- A2: [动作2描述]
- A3: [动作3描述]

### 规则表
| 规则ID | C1 | C2 | C3 | A1 | A2 | A3 | 测试场景描述 | 优先级 | 知识库参考 |
|--------|----|----|----|----|----|----|-------------|--------|------------|
| R001 | Y | Y | Y | √ | × | × | [场景描述] | P0 | [参考编号] |
| R002 | Y | Y | N | √ | × | √ | [场景描述] | P1 | [参考编号] |
| R003 | Y | N | Y | × | √ | × | [场景描述] | P2 | [参考编号] |

说明：
- Y/N: 条件成立/不成立
- √/×: 执行/不执行该动作
- 优先级: P0(核心场景)、P1(重要场景)、P2(一般场景)"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"测试点文档：{test_points}\n{knowledge_context}"}
        ]
        
        return self.generate_text(messages)

    def enhanced_generate_test_cases_step(self, decision_table: str, test_points: str) -> Tuple[str, str]:
        """第四步：基于决策表和知识库生成详细测试用例"""
        # 增强知识库检索
        knowledge_context = self._enhanced_knowledge_search(decision_table, test_points)
        
        testcase_content = """您作为资深测试工程师，请基于决策表和知识库内容生成详细的测试用例。

要求：
1. **用例完整性**：为决策表中的每个规则生成多个测试用例
2. **数据驱动**：使用不同的测试数据覆盖各种场景
3. **知识库整合**：参考知识库中的测试经验补充测试场景
4. **详细步骤**：测试步骤要具体、可执行

输出格式：
# 详细测试用例

## 功能模块：[模块名称]

### 测试场景：[场景描述]

| 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 数据组合 | 知识库参考 |
|--------|----------|----------|----------|----------|----------|--------|----------|------------|
| TC-R001-01 | [具体用例标题] | [前置条件描述] | 1.[步骤1]<br>2.[步骤2] | [具体测试数据] | 1.[结果1]<br>2.[结果2] | P0 | [数据组合描述] | [参考编号] |
| TC-R001-02 | [具体用例标题] | [前置条件描述] | 1.[步骤1]<br>2.[步骤2] | [具体测试数据] | 1.[结果1]<br>2.[结果2] | P0 | [数据组合描述] | [参考编号] |
| TC-R002-01 | [具体用例标题] | [前置条件描述] | 1.[步骤1]<br>2.[步骤2] | [具体测试数据] | 1.[结果1]<br>2.[结果2] | P1 | [数据组合描述] | [参考编号] |

说明：
- 用例ID: TC-[规则ID]-[序号]
- 数据组合: 描述使用的数据组合策略
- 每个规则至少生成2-3个测试用例，覆盖不同数据场景"""

        testcase_messages = [
            {"role": "system", "content": testcase_content},
            {"role": "user", "content": f"决策表：{decision_table}\n测试点文档：{test_points}\n{knowledge_context}"}
        ]
        test_cases = self.generate_text(testcase_messages)
        
        # 验证测试用例
        validation_content = """作为测试质量专家，请验证测试用例：
1. 检查用例是否覆盖所有决策表规则
2. 确认测试数据的多样性和边界覆盖
3. 验证预期结果的准确性和可验证性
4. 检查知识库参考的合理性

输出格式：
[验证报告]
用例数量: [总数]个
规则覆盖率: [百分比]%
数据覆盖分析:
- 正常场景: [数量]个
- 边界场景: [数量]个  
- 异常场景: [数量]个
缺失覆盖:
1. [规则]缺少[场景类型]测试
2. [功能]缺少[数据组合]测试
[补充建议]"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"决策表：{decision_table}\n生成的测试用例：{test_cases}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        return test_cases, validation_report

    def _enhanced_knowledge_search(self, decision_table: str, test_points: str) -> str:
        """增强的知识库搜索，专门针对测试设计"""
        if not self.knowledge_base:
            return "未配置知识库"
        
        try:
            # 提取关键词进行多轮搜索
            search_queries = [
                "测试用例设计 最佳实践",
                "等价类划分 边界值分析",
                "测试数据设计 组合测试",
                "异常场景测试 错误处理"
            ]
            
            # 从决策表和测试点中提取具体功能关键词
            functional_keywords = self._extract_functional_keywords(decision_table + test_points)
            if functional_keywords:
                search_queries.extend(functional_keywords[:2])  # 添加具体功能相关的搜索
            
            knowledge_context = "知识库测试设计参考:\n"
            all_results = []
            
            for query in search_queries:
                try:
                    results = self.knowledge_base.search(query, k=2)
                    all_results.extend(results)
                except Exception as e:
                    print(f"搜索知识库失败 {query}: {str(e)}")
            
            # 去重并组织结果
            seen_content = set()
            for i, (content, metadata) in enumerate(all_results):
                if content not in seen_content and len(seen_content) < 5:  # 最多5个不同结果
                    seen_content.add(content)
                    source = metadata.get('source', '未知来源')
                    knowledge_context += f"\n--- 参考 {len(seen_content)} ({source}) ---\n{content[:300]}...\n"
            
            return knowledge_context
            
        except Exception as e:
            return f"知识库检索出错: {str(e)}"

    def _extract_functional_keywords(self, text: str) -> List[str]:
        """从文本中提取功能相关的关键词"""
        patterns = [
            r'功能模块[：:]\s*([^\n]+)',
            r'测试点[：:]\s*([^\n]+)', 
            r'[功能|模块][：:]\s*([^\n]+)',
            r'[A-Za-z\u4e00-\u9fa5]+功能',
            r'[A-Za-z\u4e00-\u9fa5]+模块'
        ]
        
        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return list(set(keywords))[:5]  # 返回前5个唯一关键词

    # 辅助方法
    def _extract_keywords_from_analysis(self, analysis_text: str) -> List[str]:
        """从需求分析中提取关键词"""
        patterns = [
            r'FP\d+',                    # 功能点编号
            r'[A-Za-z\u4e00-\u9fa5]+登录', # 登录相关（支持中文）
            r'[A-Za-z\u4e00-\u9fa5]+权限', # 权限相关
            r'边界值?',                   # 边界值相关
            r'等价类?',                   # 等价类相关
            r'[A-Za-z\u4e00-\u9fa5]+功能', # 功能相关
            r'[A-Za-z\u4e00-\u9fa5]+测试', # 测试相关
        ]
        
        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, analysis_text)
            keywords.extend(matches)
        
        # 添加基于分词的关键词提取
        try:
            words = jieba.cut(analysis_text)
            for word in words:
                if len(word) >= 2 and any(char not in '的了吗呢吧啊' for char in word):
                    keywords.append(word)
        except Exception as e:
            print(f"分词失败: {str(e)}")
            # 如果分词失败，使用简单的空格分割
            words = analysis_text.split()
            for word in words:
                if len(word) >= 2:
                    keywords.append(word)
        
        return list(set(keywords))
    def answer_with_knowledge(self, question: str, context_texts: List[str]) -> str:
        """
        基于选定的知识库内容回答问题
        
        Args:
            question: 用户问题
            context_texts: 选定的相关知识文本列表
            
        Returns:
            AI生成的答案
        """
        # 构建系统提示
        system_content = """你是一位专业的测试架构师和知识库分析师。请基于用户选定的知识库内容，回答问题并给出专业建议。

    要求：
    1. 基于用户选定的知识库内容回答问题（用户已经筛选过，所以这些内容都是相关的）
    2. 直接引用选定的知识库内容，并注明来源
    3. 给出具体的、可操作的建议
    4. 使用清晰的结构化格式
    5. 如果选定的知识库内容之间有矛盾或不一致，指出并给出你的专业判断

    输出格式：
    ## 问题分析
    [分析用户问题的核心要点]

    ## 基于选定参考的解决方案
    [基于选定的知识库内容，给出具体的解决方案]

    ## 实施步骤
    1. [步骤1]
    2. [步骤2]
    3. [步骤3]

    ## 注意事项
    - [注意点1]
    - [注意点2]

    ## 后续建议
    [针对该问题的后续工作建议]"""
        
        # 构建上下文
        if context_texts:
            context_str = "\n\n".join([f"【选定参考内容 {i+1}】\n{text}" for i, text in enumerate(context_texts)])
        else:
            context_str = "用户没有选择任何参考内容。"
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"用户问题：{question}\n\n用户选定的知识库参考内容：\n{context_str}"}
        ]
        
        # 生成答案
        return self.generate_text(messages, temperature=0.3, max_tokens=2048)
    def generate_test_cases_from_test_points(self, test_points: str) -> Tuple[str, str]:
        """
        直接从测试点生成测试用例（跳过决策表步骤）
        
        Args:
            test_points: 测试点文档
            
        Returns:
            测试用例和验证报告
        """
        # 增强知识库检索
        knowledge_context = self._enhanced_knowledge_search("", test_points)
        
        testcase_content = """您作为资深测试工程师，请基于测试点文档直接生成详细的测试用例。

    要求：
    1. **用例完整性**：为每个测试点生成多个测试用例
    2. **数据驱动**：使用不同的测试数据覆盖各种场景
    3. **知识库整合**：参考知识库中的测试经验补充测试场景
    4. **详细步骤**：测试步骤要具体、可执行
    5. **不需要决策表**：直接从测试点转换为测试用例

    输出格式：
    # 详细测试用例

    ## 功能模块：[模块名称]

    ### 测试点：[测试点描述]

    | 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 |
    |--------|----------|----------|----------|----------|----------|--------|
    | TC-001-01 | [具体用例标题] | [前置条件描述] | 1.[步骤1]<br>2.[步骤2] | [具体测试数据] | 1.[结果1]<br>2.[结果2] | P0 |
    | TC-001-02 | [具体用例标题] | [前置条件描述] | 1.[步骤1]<br>2.[步骤2] | [具体测试数据] | 1.[结果1]<br>2.[结果2] | P0 |

    说明：
    - 用例ID: TC-[测试点编号]-[序号]
    - 每个测试点至少生成2-3个测试用例，覆盖不同数据场景
    - 优先级: P0(核心场景)、P1(重要场景)、P2(一般场景)"""

        testcase_messages = [
            {"role": "system", "content": testcase_content},
            {"role": "user", "content": f"测试点文档：{test_points}\n{knowledge_context}"}
        ]
        test_cases = self.generate_text(testcase_messages)
        
        # 验证测试用例
        validation_content = """作为测试质量专家，请验证测试用例：
    1. 检查用例是否覆盖所有测试点
    2. 确认测试数据的多样性和边界覆盖
    3. 验证预期结果的准确性和可验证性
    4. 检查知识库参考的合理性

    输出格式：
    [验证报告]
    用例数量: [总数]个
    测试点覆盖率: [百分比]%
    数据覆盖分析:
    - 正常场景: [数量]个
    - 边界场景: [数量]个  
    - 异常场景: [数量]个
    缺失覆盖:
    1. [测试点]缺少[场景类型]测试
    2. [功能]缺少[数据组合]测试
    [补充建议]"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"测试点文档：{test_points}\n生成的测试用例：{test_cases}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        return test_cases, validation_report