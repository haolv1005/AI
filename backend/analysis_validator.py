"""
分析质量评估器
用于评估分析报告的完整性和质量
"""

import re
from typing import Dict, List, Tuple

class AnalysisValidator:
    """分析报告质量验证器"""
    
    @staticmethod
    def validate_completeness(analysis_report: str) -> Dict:
        """验证分析报告的完整性"""
        sections = {
            "文档基本信息": 0,
            "功能点识别": 0,
            "问题识别": 0,
            "测试关注点": 0,
            "自我检查": 0,
            "综合报告": 0
        }
        
        completeness_score = 0
        missing_sections = []
        
        # 检查关键章节
        key_patterns = {
            "文档基本信息": [r"文档基本信息", r"文档类型", r"文档结构"],
            "功能点识别": [r"功能点识别", r"功能模块", r"用户角色"],
            "问题识别": [r"问题识别", r"模糊点", r"遗漏点", r"矛盾点"],
            "测试关注点": [r"测试关注点", r"测试策略", r"测试类型"],
            "自我检查": [r"自我检查", r"检查结果", r"补充内容"],
            "综合报告": [r"综合报告", r"报告摘要", r"关键问题"]
        }
        
        for section, patterns in key_patterns.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, analysis_report, re.IGNORECASE):
                    found = True
                    sections[section] = 1
                    completeness_score += 1
                    break
            
            if not found:
                missing_sections.append(section)
        
        # 计算完整度百分比
        total_sections = len(sections)
        completeness_percentage = (completeness_score / total_sections) * 100
        
        return {
            "completeness_score": completeness_score,
            "completeness_percentage": round(completeness_percentage, 2),
            "missing_sections": missing_sections,
            "section_coverage": sections
        }
    
    @staticmethod
    def validate_structure(analysis_report: str) -> Dict:
        """验证报告结构"""
        lines = analysis_report.split('\n')
        
        structure_metrics = {
            "total_lines": len(lines),
            "headings": 0,
            "tables": 0,
            "lists": 0,
            "risk_mentions": 0,
            "action_items": 0
        }
        
        # 统计标题数量
        heading_pattern = r"^#{1,3}\s+.+"
        for line in lines:
            if re.match(heading_pattern, line):
                structure_metrics["headings"] += 1
        
        # 统计表格数量
        if "|" in analysis_report:
            table_sections = re.findall(r"\|.+\|", analysis_report)
            structure_metrics["tables"] = len(set(table_sections)) // 3  # 粗略估计
        
        # 统计列表项
        list_pattern = r"^[\-\*]\s+.+"
        for line in lines:
            if re.match(list_pattern, line):
                structure_metrics["lists"] += 1
        
        # 统计风险提及
        risk_keywords = ["风险", "问题", "错误", "缺陷", "bug", "issue"]
        for keyword in risk_keywords:
            structure_metrics["risk_mentions"] += analysis_report.count(keyword)
        
        # 统计行动项
        action_keywords = ["建议", "行动", "下一步", "TODO", "待办"]
        for keyword in action_keywords:
            structure_metrics["action_items"] += analysis_report.count(keyword)
        
        return structure_metrics
    
    @staticmethod
    def validate_testability(analysis_report: str) -> Dict:
        """验证可测试性"""
        testability_indicators = {
            "clear_requirements": 0,  # 清晰需求
            "defined_conditions": 0,  # 定义的条件
            "expected_results": 0,    # 预期结果
            "test_scenarios": 0,      # 测试场景
            "data_requirements": 0    # 数据需求
        }
        
        # 检查可测试性关键词
        patterns = {
            "clear_requirements": [r"明确[的需求|要求]", r"清晰[的描述|定义]", r"具体[说明|描述]"],
            "defined_conditions": [r"[前置|触发]条件", r"当.*时", r"如果.*则"],
            "expected_results": [r"预期[结果|输出]", r"应该.*显示", r"返回.*结果"],
            "test_scenarios": [r"测试场景", r"测试用例", r"测试数据", r"边界条件"],
            "data_requirements": [r"测试数据", r"输入数据", r"数据格式", r"数据范围"]
        }
        
        for indicator, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, analysis_report)
                testability_indicators[indicator] += len(matches)
        
        # 计算可测试性得分
        total_indicators = len(testability_indicators)
        total_score = sum(testability_indicators.values())
        testability_score = min(100, total_score * 10)  # 粗略评分
        
        return {
            "testability_score": testability_score,
            "indicators": testability_indicators,
            "recommendations": AnalysisValidator._generate_testability_recommendations(testability_indicators)
        }
    
    @staticmethod
    def _generate_testability_recommendations(indicators: Dict) -> List[str]:
        """生成可测试性改进建议"""
        recommendations = []
        
        if indicators["clear_requirements"] < 3:
            recommendations.append("增加需求的明确性描述")
        
        if indicators["defined_conditions"] < 2:
            recommendations.append("明确定义前置条件和触发条件")
        
        if indicators["expected_results"] < 3:
            recommendations.append("为每个功能点定义明确的预期结果")
        
        if indicators["test_scenarios"] < 5:
            recommendations.append("补充更多测试场景和边界条件")
        
        if indicators["data_requirements"] < 2:
            recommendations.append("明确定义测试数据要求")
        
        return recommendations
    
    @staticmethod
    def comprehensive_validation(analysis_report: str) -> Dict:
        """综合验证"""
        completeness = AnalysisValidator.validate_completeness(analysis_report)
        structure = AnalysisValidator.validate_structure(analysis_report)
        testability = AnalysisValidator.validate_testability(analysis_report)
        
        # 计算总体评分
        overall_score = (
            completeness["completeness_percentage"] * 0.4 +
            min(100, structure["headings"] * 5) * 0.3 +
            testability["testability_score"] * 0.3
        )
        
        return {
            "overall_score": round(overall_score, 2),
            "completeness": completeness,
            "structure": structure,
            "testability": testability,
            "quality_level": AnalysisValidator._get_quality_level(overall_score)
        }
    
    @staticmethod
    def _get_quality_level(score: float) -> str:
        """获取质量等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 60:
            return "及格"
        else:
            return "需要改进"