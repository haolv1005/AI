import openai
from typing import List, Dict, Tuple, Optional, Any
import re
import traceback
import datetime
import json
import os
import time
class AIClient:
    def __init__(self, model_name="deepseek-coder-v2", base_url="http://localhost:11434/v1", knowledge_base=None):
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key="ollama"
        )
        self.model_name = model_name
        self.default_max_tokens = 32768
        self.knowledge_base = knowledge_base
    
    def generate_text(self, messages: List[Dict[str, str]], temperature=0.7, max_tokens=None) -> str:
        """生成文本，本地模型不限制token"""
        try:
            max_tokens = max_tokens or self.default_max_tokens
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI生成失败: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
            return f"生成失败: {str(e)}"
    
    # ==================== 第一步：专业需求文档分析 ====================
    
    def enhanced_generate_summary_step(self, text: str) -> str:
        """
        第一步：以测试工程师视角进行全面需求文档分析
        专注于功能点识别和问题发现
        """
        print("开始专业需求文档分析流程...")
        
        try:
            # 第一步：文档初步解析
            preliminary_analysis = self._preliminary_document_analysis(text)
            
            # 第二步：功能点识别与分类
            functional_analysis = self._functional_point_analysis(preliminary_analysis)
            
            # 第三步：问题与模糊点识别
            issues_analysis = self._identify_ambiguities_issues(preliminary_analysis, functional_analysis)
            
            # 第四步：生成最终分析报告
            final_report = self._generate_analysis_report(
                preliminary_analysis,
                functional_analysis,
                issues_analysis
            )
            
            return final_report
            
        except Exception as e:
            print(f"需求分析流程异常: {str(e)}")
            traceback.print_exc()
            raise Exception(f"需求分析失败: {str(e)}")
    
    def _preliminary_document_analysis(self, text: str) -> str:
        """初步文档解析：提取基本信息"""
        system_content = """您是一名资深测试分析师，正在对需求文档进行初步解析。

请重点关注以下内容：
1. 识别文档中的功能模块和子功能
2. 提取业务流程和用户角色
3. 识别输入输出数据
4. 标记潜在的测试关注点

输出格式：
# 1. 文档初步解析

## 1.1 文档概况
- **主要功能模块**: [列出主要模块]
- **用户角色**: [列出所有用户角色]
- **核心业务流程**: [简要描述核心流程]

## 1.2 功能范围
- **包含的功能**: [明确包含的功能]
- **排除的功能**: [明确排除的功能]
- **功能边界**: [功能的边界条件]

## 1.3 关键数据项
- **输入数据**: [所有输入字段和参数]
- **输出数据**: [所有输出结果和响应]
- **配置数据**: [所有配置项和参数]

## 1.4 测试准备要点
- [需要澄清的问题1]
- [需要澄清的问题2]
- [需要澄清的问题3]"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求文档内容：\n\n{text}\n\n请进行初步解析："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=2000)
    
    def _functional_point_analysis(self, preliminary_analysis: str) -> str:
        """功能点识别与详细分析"""
        system_content = """您是一名测试架构师，需要从测试角度详细识别和分类所有功能点。

请按照以下要求进行分析：

## 功能点识别要求
1. **粒度要求**: 功能点必须足够细，能够独立测试
2. **独立性要求**: 功能点之间尽量独立，减少依赖
3. **完整性要求**: 覆盖所有业务场景
4. **可测试性要求**: 每个功能点必须可验证

## 输出格式要求
# 2. 功能点详细分析

## 2.1 功能点清单（结构化的）
### [主功能模块1名称]
**模块描述**: [简要描述]
**用户角色**: [涉及的角色]

#### 子功能点1.1: [功能点名称]
- **功能描述**: [详细描述]
- **输入参数**: [输入列表]
- **输出结果**: [输出列表]
- **业务规则**: [业务逻辑规则]
- **前置条件**: [执行前必须满足的条件]
- **后置条件**: [执行后产生的状态变化]

#### 子功能点1.2: [功能点名称]
[同上结构]

### [主功能模块2名称]
[同上结构]

## 2.2 功能点属性分析
| 功能点ID | 功能点名称 | 复杂度 | 优先级 | 风险等级 | 测试类型 | 预计用例数 |
|----------|------------|--------|--------|----------|----------|------------|
| FP-001 | [功能点1] | [高/中/低] | [P0/P1/P2] | [高/中/低] | [功能/集成] | [数字] |
| FP-002 | [功能点2] | [高/中/低] | [P0/P1/P2] | [高/中/低] | [功能/集成] | [数字] |

## 2.3 功能点依赖关系
- **强依赖**: [必须满足的依赖]
- **弱依赖**: [可选的依赖]
- **顺序依赖**: [执行顺序要求]
- **数据依赖**: [数据传递依赖]

## 2.4 功能点可测试性评估
| 功能点 | 输入清晰度 | 输出明确度 | 规则完整性 | 可测试性评分 |
|--------|------------|------------|------------|--------------|
| [功能点1] | [好/中/差] | [好/中/差] | [好/中/差] | [1-10分] |"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"初步文档分析结果：\n{preliminary_analysis}\n\n请进行详细的功能点识别与分析："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=4000)
    
    def _identify_ambiguities_issues(self, preliminary_analysis: str, functional_analysis: str) -> str:
        """识别需求文档中的模糊点、矛盾点和遗漏点"""
        system_content = """您是一名需求质量分析师，专注于发现需求文档中的问题。

## 分析要点
### 1. 模糊点识别
- 术语定义不清晰
- 功能边界模糊
- 业务规则不明确
- 成功标准不量化

### 2. 矛盾点识别
- 不同章节的描述矛盾
- 业务流程逻辑矛盾
- 技术实现矛盾

### 3. 遗漏点识别
- 缺失的业务场景
- 缺失的异常处理
- 缺失的边界条件
- 缺失的数据验证

### 4. 可测试性问题
- 不可验证的需求
- 不可量化的指标
- 不可复现的场景

## 输出格式
# 3. 需求问题识别报告

## 3.1 关键模糊点（影响测试设计）
### 3.1.1 术语模糊 (共X个)
**问题描述**: [具体描述]
- **位置**: [文档位置]
- **测试影响**: [对测试设计的影响]
- **澄清需求**: [需要澄清的内容]
- **风险等级**: 🔴 高/🟡 中/🟢 低

### 3.1.2 规则模糊 (共Y个)
[同上结构]

## 3.2 关键矛盾点 (共Z个)
**问题描述**: [具体描述]
- **矛盾位置**: [矛盾的具体位置]
- **影响范围**: [影响哪些测试]
- **解决方案**: [建议的解决方案]
- **风险等级**: 🔴 高/🟡 中/🟢 低

## 3.3 关键遗漏点 (共W个)
**问题描述**: [具体描述]
- **遗漏内容**: [缺少什么]
- **测试影响**: [如果不补充会怎样]
- **补充建议**: [建议补充的内容]
- **紧急程度**: ⚡ 立即/⚠️ 尽快/📅 后续

## 3.4 总体评估
- **文档质量评分**: [1-10分]
- **可测试性评分**: [1-10分]
- **澄清优先级**: [立即澄清/尽快澄清/可接受]
- **测试风险等级**: [高/中/低]"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"""
1. 初步文档分析：
{preliminary_analysis[:1500]}...

2. 功能点分析：
{functional_analysis[:1500]}...

请识别需求文档中的关键问题：
"""}
        ]
        
        return self.generate_text(messages, temperature=0.3, max_tokens=3000)
    
    def _generate_analysis_report(self, preliminary: str, functional: str, issues: str) -> str:
        """生成最终分析报告"""
        system_content = """您是一名测试分析报告专家，需要整合所有分析结果，生成一份专业的需求文档分析报告。

请按照以下结构组织报告：

# 📋 需求文档专业分析报告
## 📅 生成时间：YYYY-MM-DD HH:MM:SS
## 👨‍💼 分析师：AI测试分析系统

---

## 🎯 报告摘要
- **文档概况**: [简要描述]
- **功能点总数**: [数字]个
- **关键问题**: [X]个模糊点，[Y]个矛盾点，[Z]个遗漏点
- **测试准备度**: [评分/等级]

---

## 📊 详细分析

### 第一部分：文档概况
[整合初步分析]

### 第二部分：功能点架构
[整合功能点分析]

### 第三部分：问题清单
[整合问题识别]

---

## ⚠️ 关键风险与影响
### 🔴 高风险问题（必须澄清）
1. [问题1] - [影响范围]
2. [问题2] - [影响范围]

### 🟡 中风险问题（建议澄清）
1. [问题1] - [影响范围]
2. [问题2] - [影响范围]

### 🟢 低风险问题（可接受）
1. [问题1] - [影响范围]
2. [问题2] - [影响范围]

---

## 🔍 测试设计建议
### 1. 测试重点区域
- [区域1] - [理由]
- [区域2] - [理由]

### 2. 测试难点
- [难点1] - [解决方案]
- [难点2] - [解决方案]

### 3. 数据准备建议
- [数据1] - [来源]
- [数据2] - [来源]

---

## 📈 工作量预估
| 测试类型 | 预计用例数 | 复杂度 | 预计工时 |
|----------|------------|--------|----------|
| 功能测试 | [数字] | [高/中/低] | [数字]小时 |
| 边界测试 | [数字] | [高/中/低] | [数字]小时 |
| 异常测试 | [数字] | [高/中/低] | [数字]小时 |

---

## 🎯 下一步行动
### 立即执行（今天）
1. [行动1]
2. [行动2]

### 近期执行（本周）
1. [行动1]
2. [行动2]

### 后续跟踪（文档澄清后）
1. [行动1]
2. [行动2]

---

## 📝 备注
[其他补充说明]

请确保报告：
1. 重点突出关键功能点和风险点
2. 为测试点生成提供明确输入
3. 语言专业，表述准确"""
        
        all_content = f"""
=== 初步分析 ===
{preliminary[:1000]}...

=== 功能点分析 ===
{functional[:1500]}...

=== 问题识别 ===
{issues[:1000]}...
"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"所有分析内容：{all_content}\n\n请生成最终的专业分析报告："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=4000)
    
    # ==================== 第二步：基于功能点的测试点拆分 ====================
    
    def enhanced_generate_test_points_step(self, analysis_report: str) -> Tuple[str, str]:
        """
        第二步：基于第一步分析出的功能点，使用测试设计方法进行详细拆分
        使用等价类、边界值、因果法、场景分析法
        """
        print("开始基于功能点的测试点拆分...")
        
        try:
            # 第一步：从分析报告中提取功能点
            functional_points = self._extract_functional_points(analysis_report)
            
            # 第二步：为每个功能点生成详细测试点
            test_points = self._generate_detailed_test_points(functional_points)
            
            # 第三步：生成验证报告
            validation_report = self._validate_test_points(test_points, functional_points)
            
            return test_points, validation_report
            
        except Exception as e:
            print(f"测试点生成失败: {str(e)}")
            traceback.print_exc()
            raise Exception(f"测试点生成失败: {str(e)}")
    
    def _extract_functional_points(self, analysis_report: str) -> str:
        """从分析报告中提取功能点信息"""
        system_content = """您是一名测试需求分析师，需要从需求分析报告中提取所有功能点信息。

请按以下格式提取：

# 功能点提取结果

## 提取的功能点列表
### [主功能模块1]
#### 功能点1.1: [功能点名称]
- **功能描述**: [详细描述]
- **输入参数**: 
  - 参数1: [类型, 范围, 约束]
  - 参数2: [类型, 范围, 约束]
- **输出结果**: 
  - 结果1: [预期值/状态]
  - 结果2: [预期值/状态]
- **业务规则**: 
  - 规则1: [详细规则]
  - 规则2: [详细规则]
- **约束条件**:
  - 条件1: [具体约束]
  - 条件2: [具体约束]

#### 功能点1.2: [功能点名称]
[同上结构]

### [主功能模块2]
[同上结构]

## 功能点统计
- 总功能点数: [数字]
- 功能模块数: [数字]
- 复杂度分布: 高[数字]个, 中[数字]个, 低[数字]个

请确保提取完整，为后续测试点拆分提供充分信息。"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"需求分析报告：\n{analysis_report}\n\n请提取所有功能点信息："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=3000)
    
    def _generate_detailed_test_points(self, functional_points: str) -> str:
        """为每个功能点生成详细测试点（使用4种测试设计方法）"""
        system_content = """您是一名资深测试设计师，需要使用4种测试设计方法为每个功能点生成详细测试点。

## 测试设计方法说明
### 1. 等价类划分法 (Equivalence Partitioning)
- 将输入域划分为有效等价类和无效等价类
- 每个等价类选一个代表性值测试

### 2. 边界值分析法 (Boundary Value Analysis)
- 测试输入域的边界值、边界内值和边界外值
- 包括上点、离点、内点

### 3. 因果图法 (Cause-Effect Graphing)
- 分析输入条件（因）和输出结果（果）的关系
- 设计覆盖所有因果组合的测试用例

### 4. 场景分析法 (Scenario Analysis)
- 基于用户实际使用场景设计测试
- 包括正常场景、异常场景、边界场景

## 输出格式要求
# 测试点详细设计

## 总体说明
- **设计方法**: 等价类划分 + 边界值分析 + 因果图法 + 场景分析
- **覆盖目标**: 100%功能点覆盖
- **测试深度**: 每个功能点至少4种测试设计

---

### [功能点名称] - 测试点设计
**功能描述**: [简要描述]

#### 1. 等价类划分测试点
| 测试点ID | 输入参数 | 等价类类型 | 测试值 | 预期结果 | 优先级 |
|----------|----------|------------|--------|----------|--------|
| EC-FP001-01 | [参数名] | 有效等价类 | [具体值] | [预期结果] | P0 |
| EC-FP001-02 | [参数名] | 无效等价类 | [具体值] | [错误提示] | P1 |
| EC-FP001-03 | [参数名] | 特殊等价类 | [具体值] | [特殊处理] | P2 |

#### 2. 边界值分析测试点
| 测试点ID | 参数 | 边界类型 | 测试值 | 预期结果 | 说明 |
|----------|------|----------|--------|----------|------|
| BV-FP001-01 | [参数名] | 最小值 | [min] | [预期结果] | 下边界 |
| BV-FP001-02 | [参数名] | 最大值 | [max] | [预期结果] | 上边界 |
| BV-FP001-03 | [参数名] | 最小值-1 | [min-1] | [错误处理] | 下边界外 |
| BV-FP001-04 | [参数名] | 最大值+1 | [max+1] | [错误处理] | 上边界外 |
| BV-FP001-05 | [参数名] | 典型值 | [typical] | [预期结果] | 边界内 |

#### 3. 因果图法测试点
**因果分析**:
- 因1: [输入条件1]
- 因2: [输入条件2]
- 果1: [输出结果1]
- 果2: [输出结果2]

| 测试点ID | 因1 | 因2 | 果1 | 果2 | 场景描述 | 优先级 |
|----------|-----|-----|-----|-----|----------|--------|
| CE-FP001-01 | Y | Y | Y | N | [场景描述] | P0 |
| CE-FP001-02 | Y | N | N | Y | [场景描述] | P1 |
| CE-FP001-03 | N | Y | N | N | [场景描述] | P2 |

#### 4. 场景分析法测试点
| 测试点ID | 场景类型 | 场景描述 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|----------|----------|----------|----------|----------|--------|
| SA-FP001-01 | 正常场景 | [用户正常操作] | [条件] | 1.[步骤] | [结果] | P0 |
| SA-FP001-02 | 异常场景 | [用户异常操作] | [条件] | 1.[步骤] | [错误处理] | P1 |
| SA-FP001-03 | 边界场景 | [边界条件操作] | [条件] | 1.[步骤] | [边界处理] | P2 |
| SA-FP001-04 | 并发场景 | [多用户并发] | [条件] | 1.[步骤] | [并发处理] | P3 |

---

### [下一个功能点名称] - 测试点设计
[同上结构]

请确保每个功能点都有完整的4种测试设计方法覆盖。"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"功能点信息：\n{functional_points}\n\n请使用4种测试设计方法生成详细测试点："}
        ]
        
        return self.generate_text(messages, temperature=0.3, max_tokens=6000)
    
    def _validate_test_points(self, test_points: str, functional_points: str) -> str:
        """验证测试点的完整性和质量"""
        system_content = """您是一名测试质量专家，需要验证生成的测试点。

## 验证要点
1. **完整性验证**: 是否覆盖所有功能点
2. **方法验证**: 是否正确应用了4种测试设计方法
3. **深度验证**: 测试点是否足够详细和具体
4. **可执行性验证**: 测试点是否可执行和可验证

## 输出格式
# 测试点验证报告

## 1. 覆盖率分析
### 1.1 功能点覆盖率
- **总功能点数**: [数字]
- **已覆盖功能点数**: [数字]
- **覆盖率**: [百分比]%
- **未覆盖功能点**: 
  1. [功能点1] - [原因]
  2. [功能点2] - [原因]

### 1.2 测试方法覆盖率
| 测试设计方法 | 应用次数 | 平均深度 | 质量评分 |
|--------------|----------|----------|----------|
| 等价类划分 | [数字] | [评分] | [1-10分] |
| 边界值分析 | [数字] | [评分] | [1-10分] |
| 因果图法 | [数字] | [评分] | [1-10分] |
| 场景分析法 | [数字] | [评分] | [1-10分] |

## 2. 质量问题清单
### 2.1 方法应用问题
1. **问题描述**: [具体问题]
   - **位置**: [在哪个功能点]
   - **影响**: [对测试的影响]
   - **建议**: [改进建议]
   - **严重程度**: 🔴 高/🟡 中/🟢 低

### 2.2 测试点质量问题
1. **问题描述**: [具体问题]
   - **位置**: [测试点ID]
   - **问题类型**: [不清晰/不可执行/不完整]
   - **改进建议**: [具体建议]
   - **严重程度**: 🔴 高/🟡 中/🟢 低

## 3. 质量评估指标
- **总体质量评分**: [1-10分]
- **可执行性评分**: [1-10分]
- **详细程度评分**: [1-10分]
- **方法正确性评分**: [1-10分]

## 4. 改进建议
### 4.1 立即改进
1. [建议1]
2. [建议2]

### 4.2 建议优化
1. [建议1]
2. [建议2]

## 5. 总结
- **是否通过验证**: [是/否，需改进]
- **建议行动**: [具体行动建议]
- **风险提示**: [测试执行风险]"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"""
原始功能点信息：
{functional_points[:1000]}...

生成的测试点：
{test_points[:2000]}...

请进行详细验证：
"""}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=3000)
    
    # ==================== 第三步：基于测试点的智能问答生成测试用例 ====================
    
    def enhanced_generate_test_cases_step(self, test_points: str) -> Tuple[str, str, List[Dict]]:
        """
        第三步：基于测试点，使用智能问答为每个测试点生成测试用例
        """
        print("开始基于智能问答的测试用例生成...")
    
        try:
            # 第一步：解析测试点，提取所有测试点信息
            parsed_test_points = self._parse_test_points(test_points)
            
            print(f"成功解析 {len(parsed_test_points)} 个测试点")
            
            # 第二步：为每个测试点生成测试用例
            test_cases_by_point = []
            
            for i, test_point in enumerate(parsed_test_points):
                print(f"为测试点 {i+1}/{len(parsed_test_points)} 生成用例: {test_point.get('id', '未知ID')}")
                
                try:
                    # 使用智能问答生成测试用例
                    test_case = self._generate_test_case_for_point(test_point)
                    
                    # 添加测试点信息
                    test_case['test_point'] = test_point
                    test_cases_by_point.append(test_case)
                    
                    # 显示进度
                    if (i + 1) % 5 == 0 or i == len(parsed_test_points) - 1:
                        print(f"进度: {i+1}/{len(parsed_test_points)}，成功: {len([tc for tc in test_cases_by_point if 'error' not in tc])}")
                    
                    # 添加延迟，避免频繁调用
                    time.sleep(0.5)
                    
                except Exception as point_error:
                    print(f"为测试点 {test_point.get('id', '未知ID')} 生成用例失败: {str(point_error)}")
                    # 记录失败信息
                    test_cases_by_point.append({
                        'test_point': test_point,
                        'error': str(point_error),
                        'generated_content': f"生成测试用例失败: {str(point_error)}",
                        'test_cases_count': 0,
                        'generated_at': datetime.datetime.now().isoformat()
                    })
            
            # 第三步：整合所有测试用例
            all_test_cases = self._integrate_test_cases(test_cases_by_point)
            
            # 第四步：生成自我检查报告
            verification_report = self._verify_test_case_completeness(test_points, test_cases_by_point)
            
            # 第五步：生成详细的验证报告
            detailed_validation = self._generate_detailed_validation_report(all_test_cases, verification_report)
            
            print(f"测试用例生成完成！成功: {len([tc for tc in test_cases_by_point if 'error' not in tc])}, 失败: {len([tc for tc in test_cases_by_point if 'error' in tc])}")
            
            return all_test_cases, detailed_validation, test_cases_by_point
        
        except Exception as e:
            print(f"测试用例生成失败: {str(e)}")
            traceback.print_exc()
            raise Exception(f"测试用例生成失败: {str(e)}")
    def _parse_test_points(self, test_points: str) -> List[Dict]:
        """解析测试点字符串，提取结构化信息"""
        print("解析测试点信息...")
        
        parsed_points = []
        
        try:
            # 按行分割
            lines = test_points.split('\n')
            
            current_module = ""
            current_function = ""
            current_point_type = ""
            
            for line in lines:
                line = line.strip()
                
                # 检测模块标题
                if line.startswith('### '):
                    # 示例: "### [功能点名称] - 测试点设计"
                    current_module = line.replace('### ', '').replace(' - 测试点设计', '').strip()
                
                # 检测测试点类型标题
                elif line.startswith('#### '):
                    # 示例: "#### 1. 等价类划分测试点"
                    if '等价类' in line:
                        current_point_type = '等价类划分'
                    elif '边界值' in line:
                        current_point_type = '边界值分析'
                    elif '因果图' in line:
                        current_point_type = '因果图法'
                    elif '场景分析' in line:
                        current_point_type = '场景分析'
                
                # 检测表格行
                elif '|' in line and line.count('|') >= 5 and not line.startswith('|--'):
                    # 跳过表头
                    if any(keyword in line.lower() for keyword in ['测试点id', '输入参数', '测试值', '预期结果']):
                        continue
                    
                    # 解析表格行
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 6:
                        point_id = parts[1] if len(parts) > 1 else ''
                        input_param = parts[2] if len(parts) > 2 else ''
                        eq_type = parts[3] if len(parts) > 3 else ''
                        test_value = parts[4] if len(parts) > 4 else ''
                        expected_result = parts[5] if len(parts) > 5 else ''
                        priority = parts[6] if len(parts) > 6 else ''
                        
                        # 构建测试点描述
                        description = f"{current_module} - {current_point_type}"
                        if input_param:
                            description += f" | 参数: {input_param}"
                        if eq_type:
                            description += f" | 类型: {eq_type}"
                        
                        parsed_points.append({
                            'id': point_id,
                            'module': current_module,
                            'type': current_point_type,
                            'description': description,
                            'input_param': input_param,
                            'test_value': test_value,
                            'expected_result': expected_result,
                            'priority': priority,
                            'full_line': line
                        })
            
            print(f"成功解析 {len(parsed_points)} 个测试点")
            
        except Exception as e:
            print(f"解析测试点时出错: {str(e)}")
        
        # 如果解析失败，返回至少一个测试点
        if not parsed_points:
            parsed_points.append({
                'id': 'TP-001',
                'module': '通用功能',
                'type': '功能测试',
                'description': '通用功能测试点',
                'input_param': '通用参数',
                'test_value': '通用测试值',
                'expected_result': '预期成功',
                'priority': 'P0'
            })
        
        return parsed_points
    def _generate_answer_for_question(self, question: str, test_point: Dict) -> str:
        """为问题生成答案"""
        
        # 系统提示词
        system_content = """你是一名专业的测试工程师，擅长设计详细、可执行的测试用例。

    你的任务是为给定的测试点设计测试用例。要求：

    ## 基本要求：
    1. 每个测试点必须生成至少3个测试用例
    2. 测试用例必须详细具体，不能模糊
    3. 测试用例必须可执行、可验证

    ## 测试用例要素：
    1. **用例ID**：必须唯一，格式如TC-xxx-01
    2. **用例标题**：简洁明了，反映测试场景
    3. **前置条件**：执行前需要满足的条件
    4. **测试步骤**：详细的操作步骤，按1.2.3.编号
    5. **测试数据**：具体的输入数据，不能是"测试数据"这样的模糊描述
    6. **预期结果**：明确的验证点，要具体可验证
    7. **优先级**：P0（最高）、P1（高）、P2（中）、P3（低）
    8. **备注**：可选，特殊注意事项

    ## 测试场景覆盖：
    - 正常场景：用户正常操作流程
    - 边界场景：输入边界值、极限值
    - 异常场景：错误输入、异常操作
    - 并发场景：多用户同时操作（如适用）
    - 安全场景：权限验证、数据安全（如适用）

    ## 输出格式：
    请使用Markdown表格格式输出，确保表格对齐。

    示例：
    | 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 备注 |
    |--------|----------|----------|----------|----------|----------|--------|------|
    | TC-LOGIN-01 | 管理员正常登录 | 1.管理员账号已注册<br>2.系统正常运行 | 1.打开登录页面<br>2.输入用户名admin<br>3.输入密码Admin@123<br>4.点击登录按钮 | 用户名：admin<br>密码：Admin@123 | 1.登录成功<br>2.跳转到管理后台<br>3.显示管理员欢迎信息 | P0 | 测试管理员权限 |

    现在请开始设计测试用例："""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question}
        ]
        
        return self.generate_text(messages, temperature=0.3, max_tokens=3000)
    def _generate_test_case_for_point(self, test_point: Dict) -> Dict:
        """为单个测试点生成详细测试用例"""
        
        try:
            # 构建详细的问题
            question = self._build_test_case_question(test_point)
            
            # 生成答案
            answer = self._generate_answer_for_question(question, test_point)
            
            # 统计用例数量
            test_cases_count = self._count_test_cases_in_answer(answer)
            
            return {
                'test_point': test_point,
                'generated_content': answer,
                'test_cases_count': test_cases_count,
                'generated_at': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"为测试点生成用例失败: {str(e)}")
            return {
                'test_point': test_point,
                'error': str(e),
                'generated_content': f"生成测试用例失败: {str(e)}",
                'test_cases_count': 0,
                'generated_at': datetime.datetime.now().isoformat()
            }

    def _build_test_case_question(self, test_point: Dict) -> str:
        """构建测试用例生成问题"""
        
        base_info = f"""测试点ID: {test_point.get('id', '未知')}
    测试点类型: {test_point.get('type', '未知')}
    测试点描述: {test_point.get('description', '')}"""

        # 根据测试点类型添加特定信息
        additional_info = ""
        if test_point.get('input_param'):
            additional_info += f"\n输入参数: {test_point.get('input_param', '')}"
        if test_point.get('test_value'):
            additional_info += f"\n测试值: {test_point.get('test_value', '')}"
        if test_point.get('expected_result'):
            additional_info += f"\n预期结果: {test_point.get('expected_result', '')}"
        if test_point.get('priority'):
            additional_info += f"\n优先级: {test_point.get('priority', 'P1')}"

        question = f"""请为以下测试点设计详细的测试用例：

    {base_info}{additional_info}

    请为这个测试点生成3-5个详细的测试用例，每个测试用例应该包含：

    **用例ID**: 格式如 TC-[测试点ID]-01, TC-[测试点ID]-02 等
    **用例标题**: 简洁明了的标题，反映测试场景
    **前置条件**: 执行前需要满足的条件
    **测试步骤**: 详细的操作步骤，按1. 2. 3. 编号
    **测试数据**: 具体的输入数据，要真实可执行
    **预期结果**: 明确的验证点，要具体可验证
    **优先级**: 根据重要性设定优先级（P0最高，P3最低）
    **备注**: 可选说明，如特殊注意事项

    请确保：
    1. 每个测试用例都是独立的，可以单独执行
    2. 测试步骤要详细具体，任何人看了都能执行
    3. 测试数据要真实有效，不能是"测试数据"这样的模糊描述
    4. 预期结果要具体明确，不能是"功能正常"这样的模糊描述
    5. 至少生成3个测试用例，建议覆盖：
    - 正常场景测试用例
    - 边界条件测试用例
    - 异常场景测试用例

    输出格式请使用Markdown表格：
    | 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 备注 |
    |--------|----------|----------|----------|----------|----------|--------|------|
    | [ID] | [标题] | [条件] | 1.[步骤]<br>2.[步骤] | [数据] | 1.[结果]<br>2.[结果] | [P1] | [备注] |
    """
        
        return question

    
    def _integrate_test_cases(self, test_cases_by_point: List[Dict]) -> str:
        """整合所有测试用例，生成统一的测试用例文档"""
        
        print(f"开始整合测试用例，共 {len(test_cases_by_point)} 个测试点的结果")
        
        # 统计信息
        total_points = len(test_cases_by_point)
        success_points = len([tc for tc in test_cases_by_point if 'error' not in tc])
        failed_points = len([tc for tc in test_cases_by_point if 'error' in tc])
        total_test_cases = sum(
            tc.get('test_cases_count', 0) 
            for tc in test_cases_by_point 
            if 'error' not in tc
        )
        
        # 生成文档标题
        integrated_content = "# 📋 智能问答生成的详细测试用例\n\n"
        integrated_content += f"## 📅 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        integrated_content += f"## 📊 统计信息\n"
        integrated_content += f"- **总测试点数**: {total_points}\n"
        integrated_content += f"- **成功生成**: {success_points}\n"
        integrated_content += f"- **生成失败**: {failed_points}\n"
        integrated_content += f"- **总测试用例数**: {total_test_cases}\n\n"
        
        # 按模块分组
        modules = {}
        for test_case in test_cases_by_point:
            if 'error' in test_case:
                continue
                
            test_point = test_case.get('test_point', {})
            module = test_point.get('module', '其他模块')
            if module not in modules:
                modules[module] = []
            
            modules[module].append(test_case)
        
        # 添加每个模块的测试用例
        for module, test_cases in modules.items():
            integrated_content += f"---\n\n"
            integrated_content += f"## 🎯 模块: {module}\n\n"
            
            # 统计该模块的测试点
            module_test_points = len(test_cases)
            module_test_cases = sum(tc.get('test_cases_count', 0) for tc in test_cases)
            
            integrated_content += f"**模块统计**: {module_test_points} 个测试点，{module_test_cases} 个测试用例\n\n"
            
            # 按测试点类型分组
            type_groups = {}
            for test_case in test_cases:
                test_point = test_case.get('test_point', {})
                test_type = test_point.get('type', '其他类型')
                if test_type not in type_groups:
                    type_groups[test_type] = []
                type_groups[test_type].append(test_case)
            
            for test_type, type_cases in type_groups.items():
                integrated_content += f"### 🔍 {test_type}测试用例\n\n"
                
                for i, test_case in enumerate(type_cases):
                    test_point = test_case.get('test_point', {})
                    generated_content = test_case.get('generated_content', '')
                    
                    # 添加测试点信息
                    integrated_content += f"#### 测试点: {test_point.get('id', f'TP-{i+1:03d}')}\n\n"
                    integrated_content += f"**原始测试点信息**:\n"
                    integrated_content += f"- ID: {test_point.get('id', '未知')}\n"
                    integrated_content += f"- 描述: {test_point.get('description', '')}\n"
                    integrated_content += f"- 类型: {test_point.get('type', '未知')}\n"
                    
                    if test_point.get('input_param'):
                        integrated_content += f"- 输入参数: {test_point.get('input_param', '')}\n"
                    if test_point.get('test_value'):
                        integrated_content += f"- 测试值: {test_point.get('test_value', '')}\n"
                    if test_point.get('expected_result'):
                        integrated_content += f"- 预期结果: {test_point.get('expected_result', '')}\n"
                    if test_point.get('priority'):
                        integrated_content += f"- 优先级: {test_point.get('priority', 'P1')}\n"
                    
                    integrated_content += f"\n**生成的测试用例** ({test_case.get('test_cases_count', 0)}个):\n\n"
                    integrated_content += f"{generated_content}\n\n"
                    integrated_content += f"---\n\n"
        
        # 添加生成失败的测试点
        failed_cases = [tc for tc in test_cases_by_point if 'error' in tc]
        if failed_cases:
            integrated_content += f"## ❌ 生成失败的测试点\n\n"
            integrated_content += f"以下测试点未能成功生成测试用例，需要人工干预:\n\n"
            
            for i, test_case in enumerate(failed_cases):
                test_point = test_case.get('test_point', {})
                error = test_case.get('error', '未知错误')
                
                integrated_content += f"{i+1}. **{test_point.get('id', f'TP-FAIL-{i+1:03d}')}**\n"
                integrated_content += f"   - 模块: {test_point.get('module', '未知')}\n"
                integrated_content += f"   - 类型: {test_point.get('type', '未知')}\n"
                integrated_content += f"   - 描述: {test_point.get('description', '')[:100]}...\n"
                integrated_content += f"   - 错误: {error}\n\n"
        
        # 添加生成总结
        integrated_content += f"## 📝 生成总结\n\n"
        integrated_content += f"- **整体成功率**: {success_points/total_points*100:.1f}% ({success_points}/{total_points})\n"
        integrated_content += f"- **平均每个测试点的用例数**: {total_test_cases/max(1, success_points):.1f}\n"
        integrated_content += f"- **生成质量评估**: {'良好' if (success_points/total_points) > 0.8 else '一般' if (success_points/total_points) > 0.6 else '需要改进'}\n"
        integrated_content += f"- **建议**: {'可以直接使用' if (success_points/total_points) > 0.8 else '需要人工检查部分测试用例' if (success_points/total_points) > 0.6 else '需要大量人工干预'}\n\n"
        
        integrated_content += f"*生成完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return integrated_content
    def _count_test_cases_in_answer(self, answer: str) -> int:
        """统计答案中的测试用例数量"""
        try:
            # 方法1：统计表格行中的用例数量
            lines = answer.split('\n')
            table_case_count = 0
            
            for line in lines:
                line = line.strip()
                # 检测表格数据行（有|但不是表头或分隔线）
                if (line.startswith('|') and line.endswith('|') and 
                    '---' not in line and 
                    '用例ID' not in line.upper() and 
                    '用例标题' not in line):
                    table_case_count += 1
            
            if table_case_count > 0:
                return table_case_count
            
            # 方法2：统计明显的测试用例标识
            import re
            patterns = [
                r'用例\s*\d+[\.:：]',
                r'TC-\w+',
                r'测试用例\s*\d+',
                r'Case\s*\d+'
            ]
            
            total_count = 0
            for pattern in patterns:
                matches = re.findall(pattern, answer, re.IGNORECASE)
                total_count += len(matches)
            
            # 方法3：如果没有找到，按段落粗略统计
            if total_count == 0:
                paragraphs = [p.strip() for p in answer.split('\n\n') if p.strip()]
                # 假设每个非短段落可能是一个测试用例
                long_paragraphs = [p for p in paragraphs if len(p) > 50]
                total_count = len(long_paragraphs)
            
            return max(1, total_count)  # 至少返回1
            
        except Exception as e:
            print(f"统计测试用例数量时出错: {str(e)}")
            return 1  # 默认返回1
    def _verify_test_case_completeness(self, original_test_points: str, generated_cases: List[Dict]) -> str:
        """验证测试用例的完整性，确保每个测试点都有对应用例"""
        
        # 解析原始测试点，获取所有测试点ID
        original_ids = set()
        lines = original_test_points.split('\n')
        for line in lines:
            if '|' in line and not line.startswith('|--') and '测试点ID' not in line.lower():
                parts = [part.strip() for part in line.split('|')]
                if len(parts) > 1 and parts[1] and parts[1].strip():
                    original_ids.add(parts[1].strip())
        
        # 获取成功生成的测试点ID
        generated_ids = set()
        for test_case in generated_cases:
            if 'error' not in test_case:
                point_id = test_case.get('test_point', {}).get('id', '')
                if point_id and point_id.strip():
                    generated_ids.add(point_id.strip())
        
        # 计算覆盖率
        total_points = len(original_ids)
        covered_points = len([id for id in original_ids if id in generated_ids])
        coverage_rate = (covered_points / total_points * 100) if total_points > 0 else 0
        
        # 查找未覆盖的测试点
        uncovered_ids = original_ids - generated_ids
        
        # 生成报告
        report = "# ✅ 测试用例完整性验证报告\n\n"
        report += f"## 📊 覆盖率统计\n\n"
        report += f"- **总测试点数**: {total_points}\n"
        report += f"- **已覆盖测试点数**: {covered_points}\n"
        report += f"- **未覆盖测试点数**: {len(uncovered_ids)}\n"
        report += f"- **覆盖率**: {coverage_rate:.1f}%\n\n"
        
        if coverage_rate >= 90:
            report += f"## 🎉 验证结果: ✅ 通过\n\n"
            report += f"测试用例覆盖良好，建议继续下一步。\n\n"
        elif coverage_rate >= 70:
            report += f"## ⚠️ 验证结果: 🔶 部分通过\n\n"
            report += f"测试用例覆盖率一般，建议补充缺失的测试用例。\n\n"
        else:
            report += f"## ❌ 验证结果: ❌ 不通过\n\n"
            report += f"测试用例覆盖率不足，需要重新生成或人工补充。\n\n"
        
        if uncovered_ids:
            report += f"## 📋 未覆盖的测试点清单\n\n"
            report += f"以下测试点没有对应的测试用例:\n\n"
            
            for i, point_id in enumerate(sorted(uncovered_ids)[:20]):  # 最多显示20个
                report += f"{i+1}. **{point_id}**\n"
            
            if len(uncovered_ids) > 20:
                report += f"\n... 还有 {len(uncovered_ids) - 20} 个未覆盖的测试点\n"
        
        report += f"\n## 🔧 建议\n\n"
        if coverage_rate >= 90:
            report += f"1. ✅ 覆盖率良好，可以直接进行测试执行\n"
            report += f"2. 🔍 建议抽查部分测试用例，验证可执行性\n"
            report += f"3. 📝 如有特殊场景，可手动补充测试用例\n"
        elif coverage_rate >= 70:
            report += f"1. ⚠️ 需要补充缺失的测试用例\n"
            report += f"2. 🔄 考虑重新生成覆盖率较低的部分\n"
            report += f"3. 👨‍💻 建议人工审查生成的测试用例\n"
        else:
            report += f"1. ❌ 需要大量人工干预来补充测试用例\n"
            report += f"2. 🔄 建议重新检查测试点设计\n"
            report += f"3. 💡 考虑调整测试策略或补充需求\n"
        
        report += f"\n## 📅 验证时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return report
    
    def _generate_detailed_validation_report(self, all_test_cases: str, verification_report: str) -> str:
        """生成详细的验证报告"""
        
        system_content = """您是一名测试质量专家，需要对生成的测试用例进行全面评估。

请从以下维度进行评估：
1. **完整性评估**: 测试用例是否完整覆盖所有测试点
2. **可执行性评估**: 测试步骤是否清晰，能否实际执行
3. **详细程度评估**: 测试数据是否具体，预期结果是否明确
4. **规范性评估**: 测试用例格式是否规范
5. **风险识别**: 识别测试用例中的潜在风险

输出格式：
# 测试用例详细验证报告

## 1. 整体评估
- **总体质量评分**: [1-10分]
- **可执行性评分**: [1-10分]
- **详细程度评分**: [1-10分]
- **规范性评分**: [1-10分]

## 2. 详细评估结果
### 2.1 完整性分析
- [分析结果]
- [存在的问题]
- [改进建议]

### 2.2 可执行性分析
- [分析结果]
- [存在的问题]
- [改进建议]

### 2.3 详细程度分析
- [分析结果]
- [存在的问题]
- [改进建议]

### 2.4 规范性分析
- [分析结果]
- [存在的问题]
- [改进建议]

## 3. 风险识别
### 3.1 高风险问题
1. [问题描述] - [影响] - [建议]
2. [问题描述] - [影响] - [建议]

### 3.2 中风险问题
1. [问题描述] - [影响] - [建议]
2. [问题描述] - [影响] - [建议]

### 3.3 低风险问题
1. [问题描述] - [影响] - [建议]
2. [问题描述] - [影响] - [建议]

## 4. 综合建议
### 4.1 立即执行
1. [建议1]
2. [建议2]

### 4.2 建议优化
1. [建议1]
2. [建议2]

### 4.3 长期改进
1. [建议1]
2. [建议2]

## 5. 总结
- **是否通过验证**: [是/否]
- **验证结论**: [总结性结论]
- **下一步建议**: [具体建议]"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"""生成的测试用例摘要：
{all_test_cases[:3000]}...

完整性验证报告：
{verification_report}

请进行详细的质量评估："""}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=3000)
    # ==================== 第四步：测试用例优化和导出 ====================
    
    def enhanced_generate_final_output_step(self, test_cases: str, validation_report: str) -> Tuple[str, str]:
        """
        第四步：对测试用例进行优化，并生成最终的Excel文件
        """
        print("开始生成最终输出...")
        
        try:
            # 第一步：优化测试用例结构
            optimized_cases = self._optimize_test_cases(test_cases)
            
            # 第二步：生成测试用例执行计划
            execution_plan = self._generate_execution_plan(optimized_cases)
            
            # 第三步：生成最终报告
            final_report = self._generate_final_report(optimized_cases, validation_report, execution_plan)
            
            return optimized_cases, final_report
            
        except Exception as e:
            print(f"最终输出生成失败: {str(e)}")
            traceback.print_exc()
            raise Exception(f"最终输出生成失败: {str(e)}")
    
    def _optimize_test_cases(self, test_cases: str) -> str:
        """优化测试用例结构，使其更适合Excel导出"""
        
        system_content = """您是一名测试用例管理专家，需要优化测试用例结构，使其更适合导入到Excel中。

请执行以下优化：
1. **标准化格式**: 统一用例标题、步骤、预期结果的格式
2. **结构化数据**: 确保测试数据以结构化形式呈现
4. **优先级排序**: 按优先级对测试用例进行排序
5. **添加执行信息**: 为每个用例添加执行状态、执行人、执行时间等字段

输出格式：
# 优化后的测试用例

## 总体说明
- **优化时间**: [时间]
- **优化项目**: [数量]个用例被优化
- **优化重点**: [重点说明]

---

## 测试用例列表

### 模块: [模块名称]

| 用例ID | 用例标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 状态 | 执行人 | 执行时间 | 备注 |
|--------|----------|----------|----------|----------|----------|--------|------|--------|----------|------|
| TC-001 | [优化后的标题] | [优化的前置条件] | 1.[步骤1]<br>2.[步骤2] | [优化后的数据] | 1.[结果1]<br>2.[结果2] | P0 | 未执行 | - | - | - |
| TC-002 | [优化后的标题] | [优化的前置条件] | 1.[步骤1]<br>2.[步骤2] | [优化后的数据] | 1.[结果1]<br>2.[结果2] | P1 | 未执行 | - | - | - |

请确保优化后的测试用例清晰、完整、可执行。"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"原始测试用例：\n{test_cases[:4000]}...\n\n请进行优化："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=4000)
    
    def _generate_execution_plan(self, test_cases: str) -> str:
        """生成测试用例执行计划"""
        
        system_content = """您是一名测试经理，需要为测试用例生成执行计划。

请考虑以下因素：
1. **优先级分配**: P0用例优先执行
2. **模块依赖**: 考虑模块之间的依赖关系
3. **资源分配**: 假设有2名测试人员
4. **时间估算**: 每个用例平均执行时间5-10分钟
5. **风险控制**: 高风险功能优先测试

输出格式：
# 测试用例执行计划

## 1. 执行策略
- **测试人员**: 2名
- **预计总工时**: [数字]小时
- **执行周期**: [数字]天
- **每日目标**: [数字]个用例

## 2. 执行阶段
### 阶段1: 核心功能测试 (第1-2天)
- **目标**: 完成所有P0优先级用例
- **重点模块**: [模块列表]
- **预计用例数**: [数字]
- **负责人**: [人员分配]

### 阶段2: 完整功能测试 (第3-5天)
- **目标**: 完成所有P0和P1优先级用例
- **重点模块**: [模块列表]
- **预计用例数**: [数字]
- **负责人**: [人员分配]

### 阶段3: 边缘和回归测试 (第6-7天)
- **目标**: 完成剩余用例和回归测试
- **重点模块**: [模块列表]
- **预计用例数**: [数字]
- **负责人**: [人员分配]

## 3. 每日执行计划
### 第1天
| 时间段 | 测试人员 | 模块 | 用例数 | 备注 |
|--------|----------|------|--------|------|
| 上午 | [人员1] | [模块1] | [数字] | [重点] |
| 下午 | [人员2] | [模块2] | [数字] | [重点] |

## 4. 风险控制
- **高风险区域**: [区域列表]
- **应对措施**: [措施描述]
- **备用计划**: [计划描述]

## 5. 成功标准
- [标准1]
- [标准2]
- [标准3]"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"测试用例：\n{test_cases[:2000]}...\n\n请生成执行计划："}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=3000)
    
    def _generate_final_report(self, test_cases: str, validation_report: str, execution_plan: str) -> str:
        """生成最终的综合报告"""
        
        system_content = """您是一名项目经理，需要整合所有信息生成最终的综合测试报告。

报告结构：
# 📋 综合测试报告
## 📅 生成时间: YYYY-MM-DD HH:MM:SS

## 🎯 项目概况
- [项目基本信息]
- [测试目标]
- [测试范围]

## 📊 测试产出
### 1. 测试用例统计
- **总用例数**: [数字]
- **按优先级分布**: P0:[数字], P1:[数字], P2:[数字]
- **按模块分布**: [模块1]:[数字], [模块2]:[数字]

### 2. 测试质量评估
- **覆盖率**: [百分比]%
- **用例质量评分**: [1-10分]
- **可执行性评分**: [1-10分]

### 3. 测试风险
- **高风险**: [数量]个
- **中风险**: [数量]个
- **低风险**: [数量]个

## 🚀 执行计划摘要
- [计划摘要]

## 📈 资源需求
- **人力**: [数字]人
- **时间**: [数字]天
- **环境**: [环境要求]

## ⚠️ 关键依赖和风险
1. [依赖/风险1]
2. [依赖/风险2]
3. [依赖/风险3]

## ✅ 成功标准
1. [标准1]
2. [标准2]
3. [标准3]

## 📝 建议和备注
- [建议1]
- [建议2]
- [备注]

请确保报告专业、全面、有指导性。"""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"""
测试用例摘要：
{test_cases[:1000]}...

验证报告摘要：
{validation_report[:1000]}...

执行计划摘要：
{execution_plan[:1000]}...

请生成最终的综合报告：
"""}
        ]
        
        return self.generate_text(messages, temperature=0.2, max_tokens=4000)
    
    # ==================== 辅助方法 ====================
    
    def answer_with_knowledge(self, question: str, context_texts: List[str]) -> str:
        """
        基于选定的知识库内容回答问题
        这是一个简化的版本，实际使用时可能需要更复杂的处理
        """
        # 构建消息
        if context_texts:
            context_str = "\n\n".join([f"【参考内容】\n{text}" for text in context_texts])
            full_content = f"问题：{question}\n\n参考内容：\n{context_str}"
        else:
            full_content = f"问题：{question}"
        
        # 使用通用的生成方法
        messages = [
            {"role": "system", "content": "您是一名测试专家，请基于提供的参考内容回答问题，给出专业、详细的建议。"},
            {"role": "user", "content": full_content}
        ]
        
        return self.generate_text(messages, temperature=0.3, max_tokens=1500)