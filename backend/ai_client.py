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
    
    # 第一步：需求文档分析
    def enhanced_generate_summary_step(self, text: str) -> str:
        """第一步：分析需求文档，提取需求点，识别问题"""
        system_content = """你是一位资深的软件需求分析师，请分析以下需求文档并完成以下任务：

## 任务要求

### 1. 提取所有明确的需求点
- 列出文档中明确提到的每一个功能需求
- 使用清晰、简洁的语言描述每个需求点
- 按功能模块组织需求点

### 2. 识别并分类问题
#### 2.1 逻辑缺失
- 缺少必要的业务流程描述
- 缺少状态转换说明
- 缺少异常处理逻辑
- 缺少数据验证规则

#### 2.2 概念模糊
- 术语定义不清晰
- 功能范围不明确
- 用户角色权限模糊
- 输入输出数据格式不明确

### 3. 归纳总结
- 总结文档的核心功能
- 评估文档的完整性和清晰度
- 提出文档改进建议

## 输出格式

# 需求文档分析报告

## 一、核心功能模块
### 1.1 [模块名称]
#### 明确需求点：
1. [需求点1：详细描述]
2. [需求点2：详细描述]
3. ...

#### 潜在问题：
- 逻辑缺失：[具体描述]
- 概念模糊：[具体描述]

### 1.2 [模块名称]
...

## 二、问题汇总
### 2.1 逻辑缺失问题
1. [问题1：位置和描述]
2. [问题2：位置和描述]
3. ...

### 2.2 概念模糊问题
1. [问题1：位置和描述]
2. [问题2：位置和描述]
3. ...

## 三、改进建议
### 3.1 必须澄清的内容
1. [建议1]
2. [建议2]
3. ...

### 3.2 建议补充的内容
1. [建议1]
2. [建议2]
3. ...

## 四、总结
- 文档质量评估：[优秀/良好/一般/较差]
- 测试可行性：[高/中/低]
- 建议优先级：[高/中/低]

---
请确保：
1. 每个需求点都清晰、可测试
2. 每个问题都有具体位置和描述
3. 建议要具体、可操作"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求文档内容：\n{text}"}
        ]
        return self.generate_text(messages)
    
    # 第二步：测试点扩充
    def enhanced_generate_test_points_step(self, summary: str) -> Tuple[str, str]:
        """第二步：基于需求点生成测试点"""
        # 生成测试点
        testpoint_content = """你是一位资深测试工程师，请基于第一步的需求分析结果，为每个需求点生成详细的测试点。

## 任务要求

### 1. 提取需求点
从需求分析报告中提取所有明确的需求点（包括功能模块和具体需求点）。

### 2. 测试点扩充规则
为每个需求点生成至少5个测试点，覆盖以下维度：
- 正常功能验证（至少2个）
- 边界条件测试（至少1个）
- 异常场景测试（至少1个）
- 用户体验测试（至少1个）

### 3. 测试点质量标准
- 每个测试点必须清晰、可执行
- 明确测试目的和验证内容
- 标明测试类型（功能、边界、异常等）
- 考虑不同用户角色场景

### 4. 完整性检查
完成所有测试点生成后，检查：
- 是否覆盖了所有需求点
- 是否有重复或冗余的测试点
- 是否有遗漏的测试场景

## 输出格式

# 测试点文档

## 模块1：[模块名称]

### 需求点1：[需求点描述]
**测试点：**
1. 【正常功能】[测试点描述]
   - 测试目的：[验证什么]
   - 验证内容：[具体验证什么]
   - 预期结果：[预期结果]

2. 【正常功能】[测试点描述]
   - 测试目的：[验证什么]
   - 验证内容：[具体验证什么]
   - 预期结果：[预期结果]

3. 【边界条件】[测试点描述]
   - 测试目的：[验证什么]
   - 验证内容：[具体验证什么]
   - 预期结果：[预期结果]

4. 【异常场景】[测试点描述]
   - 测试目的：[验证什么]
   - 验证内容：[具体验证什么]
   - 预期结果：[预期结果]

5. 【用户体验】[测试点描述]
   - 测试目的：[验证什么]
   - 验证内容：[具体验证什么]
   - 预期结果：[预期结果]

### 需求点2：[需求点描述]
**测试点：**
1. ...

## 模块2：[模块名称]
...

## 完整性检查报告
### 已覆盖需求点：
1. [模块1-需求点1]：已覆盖[数字]个测试点
2. [模块1-需求点2]：已覆盖[数字]个测试点
3. ...

### 建议与补充：
1. [建议补充的测试场景]
2. [建议优化的测试点]
3. [需要注意的风险点]

## 统计信息
- 总需求点数量：[数字]
- 总测试点数量：[数字]
- 平均每个需求点测试点数量：[数字]
- 测试类型分布：[正常功能:X, 边界条件:Y, 异常场景:Z, 用户体验:W]"""

        testpoint_messages = [
            {"role": "system", "content": testpoint_content},
            {"role": "user", "content": f"需求分析报告：\n{summary}"}
        ]
        test_points = self.generate_text(testpoint_messages)
        
        # 验证测试点
        validation_content = """作为测试负责人，请验证测试点文档的完整性和质量：

## 验证要点

### 1. 覆盖完整性验证
- 是否覆盖了所有需求点？
- 每个需求点是否都有至少5个测试点？
- 测试点是否覆盖了多种场景（正常、边界、异常、体验）？

### 2. 测试点质量验证
- 测试点描述是否清晰、可执行？
- 测试目的是否明确？
- 验证内容是否具体？
- 预期结果是否可验证？

### 3. 遗漏检查
- 是否有遗漏的重要测试场景？
- 测试点之间是否有不必要的重复？
- 是否有过于简单的测试点？

## 输出格式

# 测试点验证报告

## 验证结果
**总体质量**：[优秀/良好/一般/需要改进]
**覆盖完整性**：[百分比]%
**建议采纳度**：[高/中/低]

## 详细分析
### 覆盖情况
- 已覆盖需求点：[列出]
- 部分覆盖需求点：[列出及缺失]
- 完全覆盖需求点：[列出]

### 质量问题
1. [问题1：描述不清晰的测试点]
2. [问题2：验证内容不具体的测试点]
3. ...

### 遗漏建议
1. [建议补充的测试点1]
2. [建议补充的测试点2]
3. ...

## 改进建议
1. [立即改进的建议]
2. [后续优化的建议]
3. [重点关注的风险]"""

        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"需求分析概要：\n{summary[:1000]}...\n\n生成的测试点：\n{test_points}"}
        ]
        validation_report = self.generate_text(validation_messages)
        
        return test_points, validation_report
    
    # 第三步：测试用例生成
    def generate_test_cases_from_test_points(self, test_points: str) -> Tuple[str, str]:
        """第三步：基于测试点生成测试用例"""
        try:
            # 1. 提取所有测试点
            test_point_items = self._extract_test_points(test_points)
            
            # 2. 为每个测试点生成问题并搜索知识库
            enhanced_test_points = []
            for test_point in test_point_items:
                # 为每个测试点构建一个问题
                question = self._build_question_for_test_point(test_point)
                
                # 搜索知识库获取相关信息
                knowledge_results = []
                if self.knowledge_base:
                    try:
                        # 搜索相关知识
                        search_results = self.knowledge_base.search_with_score(question, k=3)
                        for content, metadata, score in search_results:
                            similarity = self.knowledge_base.get_similarity_percentage(score)
                            if similarity > 30:  # 相似度阈值
                                metadata['similarity'] = similarity
                                knowledge_results.append((content, metadata))
                    except Exception as e:
                        print(f"知识库搜索失败: {str(e)}")
                
                # 记录增强信息
                test_point['question'] = question
                test_point['knowledge_results'] = knowledge_results[:2]  # 最多取2个结果
                enhanced_test_points.append(test_point)
            
            # 3. 生成测试用例
            test_cases = self._generate_detailed_test_cases(enhanced_test_points)
            
            # 4. 验证测试用例
            validation_report = self._validate_test_cases(test_cases, enhanced_test_points)
            
            return test_cases, validation_report
            
        except Exception as e:
            print(f"测试用例生成失败: {str(e)}")
            # 回退到简单生成
            return self._simple_generate_test_cases(test_points)
    
    def _extract_test_points(self, test_points: str) -> List[Dict]:
        """从测试点文档中提取结构化测试点"""
        points = []
        
        # 简单模式：查找带编号的测试点
        import re
        
        # 匹配【类型】开头的测试点
        pattern = r'(\d+)\.\s*【([^】]+)】\s*([^\n]+)(?:\s*-\s*测试目的：([^\n]+))?(?:\s*-\s*验证内容：([^\n]+))?'
        matches = re.findall(pattern, test_points)
        
        for match in matches:
            if len(match) >= 3:
                point = {
                    'index': match[0],
                    'type': match[1],
                    'description': match[2],
                    'purpose': match[3] if len(match) > 3 else '',
                    'verification': match[4] if len(match) > 4 else '',
                    'module': '未分类'
                }
                points.append(point)
        
        # 如果没有找到，使用简单分割
        if not points:
            lines = test_points.split('\n')
            index = 1
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and '测试' in line:
                    point = {
                        'index': str(index),
                        'type': '功能测试',
                        'description': line,
                        'purpose': '',
                        'verification': '',
                        'module': '综合测试'
                    }
                    points.append(point)
                    index += 1
        
        return points[:50]  # 限制最多50个测试点
    
    def _build_question_for_test_point(self, test_point: Dict) -> str:
        """为测试点构建智能问题"""
        question = f"如何设计测试用例来测试：{test_point['description']}"
        
        if test_point['purpose']:
            question += f"\n测试目的：{test_point['purpose']}"
        
        if test_point['type']:
            question += f"\n测试类型：{test_point['type']}"
        
        return question
    
    def _generate_detailed_test_cases(self, enhanced_test_points: List[Dict]) -> str:
        """生成详细的测试用例"""
        # 构建输入文本
        input_text = "# 测试点与知识库参考\n\n"
        for i, point in enumerate(enhanced_test_points, 1):
            input_text += f"## 测试点{i}: {point['description']}\n"
            input_text += f"- 类型：{point['type']}\n"
            if point['purpose']:
                input_text += f"- 测试目的：{point['purpose']}\n"
            
            if point['knowledge_results']:
                input_text += "- 知识库参考：\n"
                for j, (content, metadata) in enumerate(point['knowledge_results'], 1):
                    source = metadata.get('source', '未知')
                    similarity = metadata.get('similarity', 'N/A')
                    input_text += f"  参考{j}（来源：{source}，相似度：{similarity}%）：{content[:200]}...\n"
            input_text += "\n"
        
        # 生成测试用例的提示词
        system_content = """你是一位专业的测试用例设计师，请基于以下测试点和知识库参考，生成详细的测试用例。

## 生成要求

### 1. 为每个测试点生成1个测试用例
每个测试用例必须包含：
- 用例ID（格式：TC_序号）
- 用例标题（清晰描述测试内容）
- 前置条件（执行测试前需要满足的条件）
- 测试步骤（详细、可执行的操作步骤）
- 测试数据（具体的数据值）
- 预期结果（可验证的预期行为）
- 优先级（P0/P1/P2/P3）

### 2. 利用知识库参考
- 参考知识库中的测试经验
- 应用最佳实践到测试用例设计中
- 如果知识库参考有价值，在测试步骤中注明参考

### 3. 输出格式要求
请严格按照以下格式输出：

# 详细测试用例

## 测试点1：[测试点描述]
### 测试用例TC_001
**用例标题**：[具体标题]
**前置条件**：[条件描述]
**测试步骤**：
1. [步骤1]
2. [步骤2]
3. [步骤3]
**测试数据**：[具体数据]
**预期结果**：[预期行为]
**优先级**：[P0/P1/P2/P3]
**知识库参考**：[简要说明参考了哪些知识]

## 测试点2：[测试点描述]
...

### 4. 注意事项
- 确保每个测试用例都可以独立执行
- 测试步骤要足够详细，让测试人员能够照着执行
- 预期结果要具体、可验证
- 优先级分配要合理（P0：核心功能，P1：重要功能，P2：一般功能，P3：边缘功能）"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": input_text}
        ]
        
        return self.generate_text(messages, temperature=0.3, max_tokens=8192)
    
    def _validate_test_cases(self, test_cases: str, enhanced_test_points: List[Dict]) -> str:
        """验证生成的测试用例"""
        system_content = """作为测试质量负责人，请验证生成的测试用例：

## 验证要点
1. **完整性**：是否每个测试点都有对应的测试用例？
2. **质量**：测试用例是否详细、可执行？
3. **格式**：是否按照要求的格式输出？
4. **实用性**：测试用例是否可以直接用于测试执行？

## 输出格式

# 测试用例验证报告

## 总体评估
- **测试点覆盖**：[百分比]%
- **用例质量评分**：[1-10分]
- **格式合规性**：[合规/基本合规/不合规]

## 详细分析
### 覆盖情况
- 已生成用例的测试点：[列出]
- 未生成用例的测试点：[列出]

### 质量问题
1. [问题1：测试用例不详细]
2. [问题2：预期结果不可验证]
3. [问题3：测试步骤不清晰]
4. ...

### 改进建议
1. [建议1：需要补充的测试用例]
2. [建议2：需要优化的测试用例]
3. [建议3：需要调整的优先级]

## 统计信息
- 总测试点数量：[数字]
- 总测试用例数量：[数字]
- 优先级分布：[P0:X, P1:Y, P2:Z, P3:W]
- 知识库参考使用率：[百分比]%

## 总结
[总体评价和建议下一步工作]"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"测试点数量：{len(enhanced_test_points)}\n\n生成的测试用例：\n{test_cases}"}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=4096)
    
    def _simple_generate_test_cases(self, test_points: str) -> Tuple[str, str]:
        """简单的测试用例生成（回退方案）"""
        system_content = """请基于以下测试点生成测试用例。为每个测试点生成一个测试用例，包含：
- 用例ID
- 用例标题
- 前置条件
- 测试步骤
- 测试数据
- 预期结果
- 优先级

输出格式：
# 测试用例

## [测试点1描述]
**TC_001**：[用例标题]
- 前置条件：[条件]
- 测试步骤：[步骤]
- 测试数据：[数据]
- 预期结果：[结果]
- 优先级：[P0/P1/P2/P3]

## [测试点2描述]
..."""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": test_points}
        ]
        
        test_cases = self.generate_text(messages)
        
        # 简单验证
        validation_content = "请简要验证生成的测试用例是否覆盖了所有测试点，并给出改进建议。"
        validation_messages = [
            {"role": "system", "content": validation_content},
            {"role": "user", "content": f"测试点：\n{test_points}\n\n生成的测试用例：\n{test_cases}"}
        ]
        
        validation_report = self.generate_text(validation_messages)
        
        return test_cases, validation_report
    
    # 旧版本兼容方法（保持原有调用不变）
    def enhanced_generate_test_cases_step(self, decision_table: str, test_points: str) -> Tuple[str, str]:
        """旧版本：生成测试用例（保持兼容性）"""
        # 调用新版本的方法，忽略decision_table参数
        return self.generate_test_cases_from_test_points(test_points)
    
    # 知识库相关方法
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
    
    def _extract_functional_keywords(self, analysis_text: str) -> List[str]:
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