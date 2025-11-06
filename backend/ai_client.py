import openai
from typing import List, Dict, Tuple, Optional
import re
import traceback
import datetime
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


        

    def generate_decision_table(self, requirement_analysis: str, prompt: str) -> str:
        """生成决策表，整合知识库内容"""
        # 检索知识库
        knowledge_context = ""
        if self.knowledge_base:
            try:
                # 从需求分析中提取关键词 - 改进版本
                keywords = self._extract_keywords_from_analysis(requirement_analysis)
                
                # 使用关键词搜索知识库
                search_query = " ".join(keywords[:3]) if keywords else requirement_analysis[:100]
                print(f"搜索知识库的关键词: {search_query}")  # 调试信息
                
                knowledge_results = self.knowledge_base.search(search_query, k=3)
                
                if knowledge_results:
                    knowledge_context = "相关知识库内容:\n"
                    for i, (content, metadata) in enumerate(knowledge_results):
                        source = metadata.get('source', '未知来源')
                        knowledge_context += f"\n--- 参考 {i+1} ({source}) ---\n{content}\n"
                else:
                    knowledge_context = "知识库中没有找到相关内容。"
                    
            except Exception as e:
                knowledge_context = f"知识库检索出错: {str(e)}"
                print(f"知识库检索错误: {e}")  # 调试信息
        else:
            knowledge_context = "未配置知识库。"
        
        # 改进的决策表生成提示词
        system_content = """您作为高级测试架构师，请基于需求分析点生成测试决策表：

        请严格按照以下格式生成表格：

        | 组合ID | 功能点 | 等价类 | 边界状态 | 用户角色 | 预期动作 | 优先级 | 知识库参考 |
        |---|---|---|---|---|---|---|---|
        | 1 | FP001 | 有效 | 正常 | 管理员 | 成功处理 | P0 | KB-001 |
        | 2 | FP001 | 有效 | 边界 | 管理员 | 成功处理 | P1 | KB-001 |
        | 3 | FP001 | 无效 | 越界 | 管理员 | 显示错误 | P2 | KB-002 |

        生成要求：
        1. 必须覆盖需求分析中的所有功能点
        2. 每个功能点需要包含：有效/无效等价类，正常/边界/越界状态
        3. 优先级定义：P0(核心功能)、P1(重要功能)、P2(一般功能)
        4. 如果有知识库参考，请标注对应的知识库条目"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求分析点：{requirement_analysis}\n{knowledge_context}\n附加要求：{prompt}"}
        ]
        
        print("正在生成决策表...")  # 调试信息
        result = self.generate_text(messages)
        print(f"决策表生成完成，长度: {len(result)}")  # 调试信息
        
        return result
    
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
    

        
    def _extract_keywords_from_analysis(self, analysis_text: str) -> List[str]:
        """从需求分析中提取关键词 - 改进版本"""
        # 改进的模式匹配
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
        
        # 添加基于分词的关键词提取（如果analysis_text包含中文）
        import jieba  # 需要安装: pip install jieba
        words = jieba.cut(analysis_text)
        for word in words:
            if len(word) >= 2 and any(char not in '的了吗呢吧啊' for char in word):
                keywords.append(word)
        
        return list(set(keywords))  # 去重
    def enhanced_search(self, query: str) -> List[Tuple[str, Dict]]:
        """增强型搜索，结合向量搜索和AI重新排序"""
        if not self.knowledge_base:
            return []
        
        try:
            # 记录搜索日志 - 这是第四步的核心功能
            log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 搜索查询: {query}\n"
            
            # 1. 扩展短查询（少于3个字符）
            if len(query) < 3:
                expanded_query = self.expand_short_query(query)
                log_msg += f"扩展后查询: {expanded_query}\n"
            else:
                expanded_query = query
            
            # 2. 向量相似度搜索
            results = self.knowledge_base.search(expanded_query, k=10)
            log_msg += f"基础搜索结果数: {len(results)}\n"
            
            # 记录前3个搜索结果的内容摘要
            for i, (content, metadata) in enumerate(results[:3]):
                source = metadata.get('source', '未知来源')
                log_msg += f"结果 {i+1} (来源: {source}): {content[:100]}...\n"
            
            if not results:
                log_msg += "未找到基础搜索结果\n"
                self._write_log(log_msg)
                return []
            reranked_results = self.rerank_results(query, results)
            log_msg += f"重排序后结果数: {len(reranked_results)}\n"
            
            # 记录最终结果
            for i, (content, metadata) in enumerate(reranked_results):
                source = metadata.get('source', '未知来源')
                log_msg += f"最终结果 {i+1} (来源: {source}): {content[:100]}...\n"
            
            # 写入日志文件
            self._write_log(log_msg)
            
            return reranked_results
        
        except Exception as e:
            error_msg = f"AI增强搜索失败: {str(e)}\n{traceback.format_exc()}"
            self._write_log(error_msg)
            print(error_msg)
            return []    
            # 3. AI重新排序结果
    def _write_log(self, log_msg: str):
            """写入日志文件"""
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n" + "-" * 80 + "\n\n")
            except Exception as e:
                print(f"写入日志失败: {str(e)}")
            
            except Exception as e:
                error_msg = f"AI增强搜索失败: {str(e)}\n{traceback.format_exc()}"
                self._write_log(error_msg)
                print(error_msg)
                return []
        
            except Exception as e:
                print(f"AI增强搜索失败: {str(e)}")
                return []
    def _parse_rerank_response(self, response: str, k: int, max_index: int) -> List[int]:
        """解析AI的重新排序响应"""
        import re
        numbers = [int(num) for num in re.findall(r'\d+', response)]
        
        # 过滤有效索引
        valid_indices = []
        for num in numbers:
            if 1 <= num <= max_index and num-1 not in valid_indices:
                valid_indices.append(num-1)
                if len(valid_indices) >= k:
                    break
                    
        return valid_indices