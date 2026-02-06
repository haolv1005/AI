# app.py - 保留QA记录功能，但不包括点赞/踩和日报月报
# 禁用文件监视器避免错误
import os
import sys
from pathlib import Path
import traceback
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict

# 设置基础路径
BASE_DIR = "E:/sm-ai"
DATA_DIR = os.path.join(BASE_DIR, "data")

# 创建所需目录
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "outputs"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "knowledge_base", "files"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "knowledge_base", "faiss_index"), exist_ok=True)

# 数据库路径
DB_PATH = os.path.join(DATA_DIR, "testcase.db")

# 环境变量设置
os.environ['STREAMLIT_SERVER_FILE_WATCHER'] = 'none'
os.environ['STREAMLIT_DISABLE_LOGGING'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
st.set_page_config(page_title="AI 测试用例生成系统", layout="wide")

# 导入后端模块
from backend.database import Database
from backend.knowledge_base import KnowledgeBase
from backend.testcase_generator import TestCaseGenerator
from backend.document_processor import DocumentProcessor
from backend.ai_client import AIClient
from backend.qa_logger import QALogger  # 保留日志，但简化了功能

# 工具函数
def save_uploaded_file(uploaded_file, upload_dir=os.path.join(DATA_DIR, "uploads")):
    """保存上传的文件到指定目录"""
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# 初始化会话状态
if 'initialized' not in st.session_state:
    try:
        st.session_state.db = Database(db_path=DB_PATH)
        
        kb_dir = os.path.join(DATA_DIR, "knowledge_base")
        st.session_state.kb = KnowledgeBase(kb_dir=kb_dir, db_path=DB_PATH)
        
        output_dir = os.path.join(DATA_DIR, "outputs")
        st.session_state.testcase_gen = TestCaseGenerator(output_dir=output_dir)
        
        st.session_state.document_processor = DocumentProcessor()
        
        st.session_state.ai_client = AIClient(knowledge_base=st.session_state.kb)
        
        log_dir = os.path.join(BASE_DIR, "log")
        st.session_state.qa_logger = QALogger(log_dir=log_dir)  # 初始化日志
        
        st.session_state.session_id = f"{int(time.time())}_{hash(str(time.time()))}"
        
        st.session_state.initialized = True
        st.toast("系统初始化完成", icon="✅")
    except Exception as init_error:
        st.error(f"初始化失败: {str(init_error)}")
        st.stop()

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["生成测试用例", "历史记录", "知识库管理"])

if page == "生成测试用例":
    # ... (这部分代码保持不变) ...
    st.title("AI 测试用例生成系统")
    
    # 初始化会话状态
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 0
    if 'doc_text' not in st.session_state:
        st.session_state.doc_text = ""
    if 'current_summary' not in st.session_state:
        st.session_state.current_summary = ""
    if 'current_requirement_analysis' not in st.session_state:
        st.session_state.current_requirement_analysis = ""
    if 'current_analysis_report' not in st.session_state:
        st.session_state.current_analysis_report = ""
    if 'current_test_cases' not in st.session_state:
        st.session_state.current_test_cases = ""
    if 'current_test_validation' not in st.session_state:
        st.session_state.current_test_validation = ""
    
    # 文件上传
    uploaded_file = st.file_uploader("上传 Word 或 PDF 需求文档", type=["docx", "pdf"])
    
    if uploaded_file and st.session_state.generation_step == 0:
        if st.button("开始专业分析流程", key="start_generation"):
            try:
                file_path = save_uploaded_file(uploaded_file)
                st.session_state.doc_text = st.session_state.document_processor.read_file(file_path)
                st.session_state.file_path = file_path
                st.session_state.original_filename = uploaded_file.name
                st.session_state.generation_step = 1
                st.rerun()
            except Exception as file_error:
                st.error(f"文件处理失败: {str(file_error)}")
    
    # 第一步：专业需求文档分析
    if st.session_state.generation_step >= 1:
        st.header("第一步：专业需求文档分析")
        
        if st.session_state.current_summary == "":
            with st.spinner("正在进行专业的文档分析..."):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    step_names = ["文档初步解析", "功能点识别", "问题识别", 
                                 "测试关注点分析", "自我检查", "生成综合报告"]
                    
                    for i in range(len(step_names)):
                        progress_bar.progress((i + 1) / len(step_names))
                        status_text.text(f"正在进行：{step_names[i]}")
                        time.sleep(0.2)
                    
                    st.session_state.current_summary = st.session_state.ai_client.enhanced_generate_summary_step(
                        st.session_state.doc_text
                    )
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ 专业需求文档分析完成！")
                    st.success("专业需求文档分析完成！")
                    
                except Exception as summary_error:
                    st.error(f"需求分析失败: {str(summary_error)}")
                    st.stop()
        
        # 可编辑的分析报告区域
        st.subheader("📋 专业需求文档分析报告（可编辑）")
        
        edited_summary = st.text_area(
            "编辑专业分析报告",
            value=st.session_state.current_summary,
            height=500,
            key="summary_editor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 重新生成分析", type="secondary", key="regenerate_summary"):
                st.session_state.current_summary = ""
                st.rerun()
        with col2:
            if st.button("✅ 确认分析并进入下一步", type="primary", key="confirm_summary"):
                st.session_state.current_summary = edited_summary
                st.session_state.generation_step = 2
                st.rerun()
    
    if st.session_state.generation_step >= 2:
        st.header("第二步：基于功能点的测试点详细拆分")
        
        if st.session_state.current_requirement_analysis == "":
            with st.spinner("正在使用4种测试设计方法生成详细测试点..."):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    step_names = ["提取功能点", "等价类划分", "边界值分析", 
                                 "因果图分析", "场景分析", "生成测试点"]
                    
                    for i in range(len(step_names)):
                        progress_bar.progress((i + 1) / len(step_names))
                        status_text.text(f"正在执行：{step_names[i]}")
                        time.sleep(0.2)
                    
                    test_points, analysis_report = st.session_state.ai_client.enhanced_generate_test_points_step(
                        st.session_state.current_summary
                    )
                    st.session_state.current_requirement_analysis = test_points
                    st.session_state.current_analysis_report = analysis_report
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ 测试点生成完成！")
                    st.success("测试点生成完成！")
                    
                except Exception as analysis_error:
                    st.error(f"测试点生成失败: {str(analysis_error)}")
                    st.stop()
        
        # 显示测试点统计
        if st.session_state.current_requirement_analysis:
            test_point_count = st.session_state.current_requirement_analysis.count("测试点ID")
            eq_count = st.session_state.current_requirement_analysis.count("等价类")
            bv_count = st.session_state.current_requirement_analysis.count("边界值")
            ce_count = st.session_state.current_requirement_analysis.count("因果图")
            sa_count = st.session_state.current_requirement_analysis.count("场景分析")
            
            st.markdown("### 📊 测试点统计")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("总测试点数", test_point_count)
            with col2:
                st.metric("等价类测试点", eq_count)
            with col3:
                st.metric("边界值测试点", bv_count)
            with col4:
                st.metric("因果图测试点", ce_count)
            with col5:
                st.metric("场景分析测试点", sa_count)
        
        # 可编辑的测试点区域
        st.subheader("详细测试点（可编辑）")
        edited_requirement_analysis = st.text_area(
            "编辑测试点",
            value=st.session_state.current_requirement_analysis,
            height=400,
            key="requirement_analysis_editor"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("返回上一步", type="secondary", key="back_to_step1"):
                st.session_state.generation_step = 1
                st.rerun()
        with col2:
            if st.button("重新生成测试点", type="secondary", key="regenerate_analysis"):
                st.session_state.current_requirement_analysis = ""
                st.session_state.current_analysis_report = ""
                st.rerun()
        with col3:
            if st.button("确认测试点并进入下一步", type="primary", key="confirm_analysis"):
                st.session_state.current_requirement_analysis = edited_requirement_analysis
                st.session_state.generation_step = 3
                st.rerun()
    
    if st.session_state.generation_step >= 3:
        st.header("第三步：智能问答生成测试用例")
        
        # 添加一个状态跟踪器
        if 'test_cases_generated' not in st.session_state:
            st.session_state.test_cases_generated = False
            st.session_state.test_cases_data = None
            st.session_state.test_cases_validation = None
            st.session_state.test_cases_details = None
        
        if not st.session_state.test_cases_generated:
            with st.spinner("正在通过智能问答生成测试用例..."):
                try:
                    progress_container = st.empty()
                    status_container = st.empty()
                    
                    progress_bar = progress_container.progress(0)
                    
                    steps = [
                        "解析测试点",
                        "准备智能问答",
                        "生成测试用例",
                        "进行完整性检查",
                        "生成验证报告"
                    ]
                    
                    for i, step in enumerate(steps):
                        progress_bar.progress((i + 1) / len(steps))
                        status_container.text(f"正在执行: {step}")
                        time.sleep(0.5)
                    
                    test_cases, validation_report, test_cases_details = st.session_state.ai_client.enhanced_generate_test_cases_step(
                        st.session_state.current_requirement_analysis
                    )
                    
                    st.session_state.current_test_cases = test_cases
                    st.session_state.current_test_validation = validation_report
                    st.session_state.test_cases_details = test_cases_details
                    st.session_state.test_cases_generated = True
                    
                    progress_bar.progress(1.0)
                    status_container.text("✅ 智能问答测试用例生成完成！")
                    st.success("测试用例生成完成！")
                    
                    st.rerun()
                    
                except Exception as testcase_error:
                    st.error(f"测试用例生成失败: {str(testcase_error)}")
                    st.stop()
        
        # 显示生成的测试用例
        if st.session_state.test_cases_details:
            total_test_points = len(st.session_state.test_cases_details)
            total_test_cases = sum(
                tc.get('test_cases_count', 0) 
                for tc in st.session_state.test_cases_details 
                if 'error' not in tc
            )
            failed_points = len([tc for tc in st.session_state.test_cases_details if 'error' in tc])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总测试点数", total_test_points)
            with col2:
                st.metric("成功生成", total_test_points - failed_points)
            with col3:
                st.metric("生成失败", failed_points)
            with col4:
                st.metric("总测试用例数", total_test_cases)
            
            edited_test_cases = st.text_area(
                "编辑测试用例",
                value=st.session_state.current_test_cases,
                height=500,
                key="test_cases_editor"
            )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("返回上一步", type="secondary", key="back_to_step2"):
                st.session_state.generation_step = 2
                st.session_state.test_cases_generated = False
                st.rerun()
        with col2:
            if st.button("重新生成测试用例", type="secondary", key="regenerate_testcases"):
                st.session_state.test_cases_generated = False
                st.session_state.current_test_cases = ""
                st.session_state.current_test_validation = ""
                st.session_state.test_cases_details = None
                st.rerun()
        with col3:
            if st.button("确认用例并进入下一步", type="primary", key="confirm_testcases"):
                if edited_test_cases:
                    st.session_state.current_test_cases = edited_test_cases
                st.session_state.generation_step = 4
                st.rerun()
    
    # 第四步：生成最终输出
    if 'current_test_cases' not in st.session_state:
        st.session_state.current_test_cases = ""
    if 'current_test_validation' not in st.session_state:
        st.session_state.current_test_validation = ""
    if st.session_state.generation_step >= 4:
        st.header("第四步：生成最终输出")
        st.subheader("📋 测试用例（直接使用原始结果）")
        
        final_test_cases = st.text_area(
            "编辑测试用例（可选）",
            value=st.session_state.current_test_cases,
            height=500,
            key="final_test_cases_editor"
        )
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("返回上一步", type="secondary", key="back_to_step3"):
                st.session_state.generation_step = 3
                st.rerun()
        with col2:
            if st.button("生成Excel文件", type="primary", key="generate_excel_final"):
                try:
                    output_path = st.session_state.testcase_gen.generate_excel(
                        final_test_cases,
                        st.session_state.original_filename
                    )
                    st.success(f"Excel 文件已生成: {output_path}")
                    
                    try:
                        record_id = st.session_state.db.add_record(
                            original_filename=st.session_state.original_filename,
                            file_path=st.session_state.file_path,
                            output_filename=os.path.basename(output_path),
                            output_path=output_path,
                            summary=st.session_state.current_summary,
                            requirement_analysis=st.session_state.current_requirement_analysis,
                            decision_table="智能问答生成测试用例流程",
                            test_cases=st.session_state.current_test_cases,
                            test_validation=st.session_state.current_test_validation
                        )
                        st.info(f"记录已保存到数据库，ID: {record_id}")
                    except Exception as db_error:
                        st.warning(f"保存记录失败: {str(db_error)}")
                    
                    if os.path.exists(output_path):
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="下载 Excel 测试用例",
                                data=f,
                                file_name=os.path.basename(output_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_excel_final"
                            )
                    else:
                        st.error(f"Excel文件未找到: {output_path}")
                        
                except Exception as excel_error:
                    st.error(f"生成 Excel 文件失败: {str(excel_error)}")
                    st.text(traceback.format_exc())
    
        st.markdown("---")
        if st.button("重新开始新流程", type="secondary", key="reset_workflow"):
            for key in ['generation_step', 'doc_text', 'current_summary', 'current_requirement_analysis', 
                    'current_analysis_report', 'current_test_cases', 'current_test_validation',
                    'test_cases_generated', 'test_cases_details', 'file_path', 'original_filename']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("流程已重置，可以开始新的生成了！")
            st.rerun()

elif page == "历史记录":
    st.title("📚 历史记录")
    
    # 创建两个选项卡
    tab1, tab2 = st.tabs(["📋 测试用例生成记录", "💬 智能问答记录"])
    
    # 选项卡1：测试用例生成记录
    with tab1:
        st.header("测试用例生成记录")
        
        try:
            records = st.session_state.db.get_records()
        except Exception as records_error:
            st.error(f"加载历史记录失败: {str(records_error)}")
            records = []
        
        if not records:
            st.info("暂无测试用例生成记录")
        else:
            # 简化显示，只显示关键信息和下载按钮
            for record in records:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        # 显示基本信息
                        st.write(f"**📄 需求文档:** {record['original_filename']}")
                        st.write(f"**🕒 生成时间:** {record['created_at']}")
                        
                        # 显示测试用例文件信息
                        output_exists = os.path.exists(record['output_path']) if record.get('output_path') else False
                        if output_exists:
                            st.write(f"**📊 测试用例文件:** {record['output_filename']}")
                        else:
                            st.warning("⚠️ 测试用例文件不存在")
                    
                    with col2:
                        # 下载原始文件按钮（如果存在）
                        original_exists = os.path.exists(record['file_path']) if record.get('file_path') else False
                        if original_exists:
                            with open(record['file_path'], "rb") as f:
                                st.download_button(
                                    label="📥 下载需求文档",
                                    data=f,
                                    file_name=record['original_filename'],
                                    key=f"dl_original_{record['id']}"
                                )
                        else:
                            st.warning("⚠️ 原始文件不存在")
                    
                    with col3:
                        # 下载测试用例文件按钮（如果存在）
                        if output_exists:
                            with open(record['output_path'], "rb") as f:
                                st.download_button(
                                    label="📥 下载测试用例",
                                    data=f,
                                    file_name=record['output_filename'],
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"dl_output_{record['id']}"
                                )
                        else:
                            st.warning("无法下载")
                    
                    st.divider()
    
    # 选项卡2：智能问答记录
    with tab2:
        st.header("智能问答记录")
        
        try:
            # 从数据库获取问答记录
            qa_records = st.session_state.db.get_qa_records(limit=50)
        except Exception as qa_error:
            st.error(f"加载问答记录失败: {str(qa_error)}")
            qa_records = []
        
        if not qa_records:
            st.info("暂无智能问答记录")
        else:
            # 显示问答记录
            for qa_record in qa_records:
                with st.container():
                    # 显示问答信息
                    col_info1, col_info2 = st.columns([2, 1])
                    with col_info1:
                        st.write(f"**🕒 提问时间:** {qa_record['created_at']}")
                    with col_info2:
                        if qa_record.get('reference_count', 0) > 0:
                            st.write(f"**📚 参考文档数:** {qa_record['reference_count']}")
                    
                    # 问题部分
                    with st.expander(
                        f"❓ 问题: {qa_record['question'][:80]}..." 
                        if len(qa_record['question']) > 80 
                        else f"❓ 问题: {qa_record['question']}", 
                        expanded=False
                    ):
                        st.write(f"**完整问题:**")
                        st.info(qa_record['question'])
                        
                        st.write(f"**🤖 AI答案:**")
                        st.markdown("""
                        <style>
                        .answer-box {
                            background-color: #f8f9fa;
                            border-left: 4px solid #4CAF50;
                            padding: 15px;
                            border-radius: 5px;
                            margin: 10px 0;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.markdown('<div class="answer-box">', unsafe_allow_html=True)
                        st.markdown(qa_record['answer'])
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 操作按钮
                    col_btn1, col_btn2 = st.columns([1, 5])
                    with col_btn1:
                        delete_key = f"delete_qa_{qa_record['id']}"
                        if st.button("🗑️ 删除", key=delete_key, type="secondary"):
                            success = st.session_state.db.delete_qa_record(qa_record['id'])
                            if success:
                                st.success("记录已删除")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("删除失败")
                    
                    st.divider()

elif page == "知识库管理":
    st.title("知识库管理")
    
    # 合并搜索和问答功能
    st.subheader("知识库搜索与问答")
    
    # 搜索配置
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search_query = st.text_input(
            "输入搜索查询", 
            "用户登录功能，包含管理员和普通用户角色", 
            key="search_query_input"
        )
    with col2:
        result_count = st.number_input(
            "结果数量",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            key="result_count_input"
        )
    with col3:
        similarity_threshold = st.number_input(
            "相似度阈值(%)",
            min_value=0,
            max_value=100,
            value=65,
            step=5,
            key="similarity_threshold"
        )
    
    # 搜索按钮
    if st.button("执行搜索", key="execute_search", type="primary"):
        try:
            if not search_query.strip():
                st.warning("请输入查询内容")
            else:
                with st.spinner("正在搜索知识库..."):
                    # 执行搜索
                    search_k = min(50, result_count * 2)
                    knowledge_results = st.session_state.kb.search_with_score(
                        search_query.strip(), 
                        k=search_k
                    )
                    
                    # 过滤结果：按相似度阈值过滤，并按相似度排序
                    relevant_results = []
                    
                    for content, metadata, distance in knowledge_results:
                        similarity = st.session_state.kb.get_similarity_percentage(distance)
                        if similarity >= similarity_threshold:
                            source = metadata.get('source', '未知来源')
                            file_id = hash(source)
                            
                            ref_id = f"{file_id}_{metadata.get('row', '0')}_{metadata.get('chunk_index', '0')}"
                            
                            relevant_results.append({
                                "id": ref_id,
                                "content": content,
                                "metadata": metadata,
                                "distance": distance,
                                "similarity": similarity,
                                "source": source,
                                "selected": False
                            })
                    
                    # 按相似度排序（从高到低）
                    relevant_results.sort(key=lambda x: x["similarity"], reverse=True)
                    
                    # 限制显示数量
                    if len(relevant_results) > result_count:
                        relevant_results = relevant_results[:result_count]
                    
                    # 保存搜索结果到会话状态
                    st.session_state.kb_search_results = relevant_results
                    st.session_state.kb_selected_refs = []
                    st.session_state.kb_generated_answer = None
                    
                    if relevant_results:
                        st.success(f"找到 {len(relevant_results)} 个相关参考（相似度≥{similarity_threshold}%）")
                    else:
                        st.warning(f"未找到相似度≥{similarity_threshold}%的相关结果")
                        
        except Exception as search_error:
            st.error(f"检索失败: {str(search_error)}")
            st.text(traceback.format_exc())
    
    # 显示搜索结果和选择界面
    if 'kb_search_results' in st.session_state and st.session_state.kb_search_results:
        st.markdown("---")
        st.subheader("📊 搜索结果 - 选择参考内容")
        
        total_refs = len(st.session_state.kb_search_results)
        selected_count = len(st.session_state.kb_selected_refs) if 'kb_selected_refs' in st.session_state else 0
        
        st.info(f"共找到 {total_refs} 个参考，已选中 {selected_count} 个")
        
        # 批量选择控制
        col_sel1, col_sel2, col_sel3 = st.columns([1, 1, 2])
        with col_sel1:
            if st.button("全选", key="select_all"):
                st.session_state.kb_selected_refs = [r["id"] for r in st.session_state.kb_search_results]
                st.rerun()
        with col_sel2:
            if st.button("全不选", key="deselect_all"):
                st.session_state.kb_selected_refs = []
                st.rerun()
        with col_sel3:
            if st.button("选相似度≥90%", key="select_high"):
                high_refs = [r["id"] for r in st.session_state.kb_search_results if r["similarity"] >= 90]
                st.session_state.kb_selected_refs = high_refs
                st.rerun()
        
        # 显示搜索结果表格
        table_data = []
        for i, result in enumerate(st.session_state.kb_search_results):
            metadata = result["metadata"]
            content = result["content"]
            similarity = result["similarity"]
            
            # 检查是否已选中
            is_selected = result["id"] in st.session_state.kb_selected_refs
            
            table_data.append({
                "选择": is_selected,
                "排名": i + 1,
                "相似度": similarity,
                "文件名": result["source"],
                "类型": metadata.get('type', '未知'),
                "工作表": metadata.get('sheet', 'N/A'),
                "行号": str(metadata.get('row', 'N/A')),
                "内容摘要": (content[:80] + "...") if len(content) > 80 else content,
                "ID": result["id"]
            })
        
        # 创建可编辑的DataFrame用于选择
        df_results = pd.DataFrame(table_data)
        
        # 使用st.data_editor显示表格
        edited_df = st.data_editor(
            df_results[["选择", "排名", "相似度", "文件名", "类型", "工作表", "行号", "内容摘要"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "选择": st.column_config.CheckboxColumn(
                    "选择",
                    help="选择此项作为参考",
                    default=False,
                ),
                "排名": st.column_config.NumberColumn(width="small"),
                "相似度": st.column_config.ProgressColumn(
                    "相似度(%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                ),
                "内容摘要": st.column_config.TextColumn(width="large"),
            },
            key="search_results_table"
        )
        
        # 更新选择状态
        if not edited_df.empty and '选择' in edited_df.columns:
            selected_ids = []
            for idx, row in edited_df.iterrows():
                if row['选择'] and idx < len(st.session_state.kb_search_results):
                    selected_ids.append(st.session_state.kb_search_results[idx]["id"])
            
            if set(selected_ids) != set(st.session_state.get('kb_selected_refs', [])):
                st.session_state.kb_selected_refs = selected_ids
                st.rerun()
        
        # 智能问答部分
        st.markdown("---")
        st.subheader("🤖 智能问答")
        
        col_qa1, col_qa2 = st.columns([3, 1])
        with col_qa1:
            user_question = st.text_area(
                "输入您的问题",
                "如何设计用户登录功能的测试用例？",
                height=100,
                key="user_question_input"
            )
        
        # 显示选定的参考
        if st.session_state.kb_selected_refs:
            with st.expander(f"📋 查看选定的 {len(st.session_state.kb_selected_refs)} 个参考", expanded=False):
                for i, ref_id in enumerate(st.session_state.kb_selected_refs):
                    result = next((r for r in st.session_state.kb_search_results if r["id"] == ref_id), None)
                    if result:
                        st.write(f"**参考 {i+1}** - {result['source']} - 相似度: {result['similarity']:.1f}%")
                        content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
                        st.text(content_preview)
                        st.markdown("---")
        
        # 生成答案按钮
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            generate_clicked = st.button("基于选定参考生成答案", 
                                        key="generate_answer", 
                                        type="primary",
                                        disabled=len(st.session_state.kb_selected_refs) == 0)
        
        with col_btn2:
            if 'kb_generated_answer' in st.session_state and st.session_state.kb_generated_answer:
                if st.button("清空历史答案", key="clear_answer"):
                    st.session_state.kb_generated_answer = None
                    st.rerun()
        
        if generate_clicked:
            if not user_question.strip():
                st.warning("请输入问题")
            elif len(st.session_state.kb_selected_refs) == 0:
                st.warning("请至少选择一个参考内容")
            else:
                with st.spinner("正在基于选定参考生成专业答案..."):
                    try:
                        selected_contexts = []
                        for ref_id in st.session_state.kb_selected_refs:
                            result = next((r for r in st.session_state.kb_search_results if r["id"] == ref_id), None)
                            if result:
                                source = result["source"]
                                similarity = result["similarity"]
                                content = result["content"]
                                
                                context_text = f"来源: {source}\n相似度: {similarity:.1f}%\n\n{content}"
                                selected_contexts.append(context_text)
                        
                        ai_answer = st.session_state.ai_client.answer_with_knowledge(
                            user_question.strip(),
                            selected_contexts
                        )
                        
                        st.session_state.kb_generated_answer = {
                            "question": user_question.strip(),
                            "answer": ai_answer,
                            "reference_count": len(st.session_state.kb_selected_refs),
                            "selected_ref_ids": st.session_state.kb_selected_refs.copy(),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 保存到数据库
                        record_id = st.session_state.db.add_qa_record(
                            question=user_question.strip(),
                            answer=ai_answer,
                            reference_count=len(st.session_state.kb_selected_refs)
                        )
                        
                        if record_id > 0:
                            st.session_state.kb_generated_answer["record_id"] = record_id
                            print(f"问答记录已保存到数据库，ID: {record_id}")
                        
                        # 保存到日志文件（可选）
                        if st.session_state.qa_logger:
                            log_id = st.session_state.qa_logger.log_qa(
                                question=user_question.strip(),
                                answer=ai_answer,
                                reference_count=len(st.session_state.kb_selected_refs)
                            )
                            print(f"问答记录已记录到日志，ID: {log_id}")
                        
                        st.success("答案生成完成！")
                        st.rerun()
                        
                    except Exception as ai_error:
                        st.error(f"AI生成答案失败: {str(ai_error)}")
        
        # 显示生成的答案（不包含点赞/踩功能）
        if 'kb_generated_answer' in st.session_state and st.session_state.kb_generated_answer:
            st.markdown("---")
            st.subheader("🤖 AI 专业建议")
            
            answer_info = st.session_state.kb_generated_answer
            record_id = answer_info.get("record_id")
            
            st.markdown(f"**问题**: {answer_info['question']}")
            st.caption(f"生成时间: {answer_info['timestamp']} | 参考数量: {answer_info['reference_count']}个")
            
            # 显示答案
            st.markdown("""
            <style>
            .answer-card {
                background-color: #f8f9fa;
                border-left: 4px solid #4CAF50;
                padding: 20px;
                border-radius: 5px;
                margin: 10px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="answer-card">', unsafe_allow_html=True)
            st.markdown(answer_info['answer'])
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 清空按钮
    if 'kb_search_results' in st.session_state and st.session_state.kb_search_results:
        if st.button("清空搜索结果", key="clear_search_results", type="secondary"):
            if 'kb_search_results' in st.session_state:
                del st.session_state.kb_search_results
            if 'kb_selected_refs' in st.session_state:
                del st.session_state.kb_selected_refs
            if 'kb_generated_answer' in st.session_state:
                del st.session_state.kb_generated_answer
            st.rerun()
    
    st.subheader("上传知识文件")
    knowledge_file = st.file_uploader(
        "上传 Excel、CSV 或文本文件到知识库", 
        type=["csv", "xlsx", "xls", "txt", "docx", "pdf"],
        key="kb_file_uploader"
    )

    if knowledge_file and st.button("上传到知识库", key="upload_to_kb"):
        with st.spinner("上传并处理文件中..."):
            try:
                # 保存文件到知识库目录
                file_path = os.path.join(st.session_state.kb.KB_FILES_DIR, knowledge_file.name)
                with open(file_path, "wb") as f:
                    f.write(knowledge_file.getbuffer())
                st.success(f"文件已保存到: {file_path}")
                
                # 添加到知识库索引
                kb_success = st.session_state.kb.add_document(file_path)
                
                if kb_success:
                    # 添加到数据库
                    db_success = st.session_state.db.add_knowledge_file(knowledge_file.name, file_path)
                    
                    if db_success:
                        st.success(f"文件 '{knowledge_file.name}' 已成功添加到知识库！")
                        # 刷新页面以显示新文件
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("添加文件到数据库失败")
                else:
                    st.error("添加文件到知识库索引失败")
                    
            except Exception as upload_error:
                error_msg = f"添加文件到知识库失败: {str(upload_error)}"
                st.error(error_msg)
                st.text(traceback.format_exc())
        
        st.subheader("知识库文件列表")
        try:
            kb_files = st.session_state.kb.get_all_documents()
        except Exception as kb_files_error:
            st.error(f"加载知识库文件列表失败: {str(kb_files_error)}")
            st.text(traceback.format_exc())
            kb_files = []

        if not kb_files:
            st.info("知识库中暂无文件")
        else:
            for i, file_info in enumerate(kb_files):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    filename = file_info.get('filename', '未知文件')
                    size_str = file_info.get('size_str', '未知大小')
                    file_path = file_info.get('file_path', '路径未知')
                    exists = file_info.get('exists', False)
                    file_id = file_info.get('id', i)
                    
                    st.write(f"{i+1}. {filename} ({size_str})")
                    st.caption(f"路径: {file_path}")
                    if not exists:
                        st.error("⚠️ 文件不存在")
                    
                with col2:
                    delete_key = f"del_{file_id}_{i}"
                    if st.button(f"删除", key=delete_key):
                        try:
                            if exists and os.path.exists(file_path):
                                os.remove(file_path)
                            
                            if file_id and file_id != i:
                                st.session_state.db.delete_knowledge_file(file_id)
                            
                            with st.spinner("正在更新知识库索引..."):
                                st.session_state.kb.rebuild_index()
                                
                            st.success(f"已删除文件: {filename}")
                            st.rerun()
                        except Exception as delete_error:
                            st.error(f"删除文件失败: {str(delete_error)}")
                
                with col3:
                    reindex_key = f"reindex_{file_id}_{i}"
                    if exists and st.button(f"重新索引", key=reindex_key):
                        with st.spinner("重新索引文件中..."):
                            try:
                                success = st.session_state.kb.add_document(file_path)
                                if success:
                                    st.success("文件已重新索引！")
                                else:
                                    st.error("重新索引失败")
                            except Exception as reindex_error:
                                st.error(f"重新索引失败: {str(reindex_error)}")

# 添加一些样式
st.markdown("""
<style>
    .stExpander {
        margin-bottom: 1rem;
        border: 1px solid #eee;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    .stDownloadButton button {
        background-color: #4CAF50;
        color: white;
    }
    .stProgress > div > div {
        background-color: #2196F3 !important;
    }
    .analysis-step {
        border-left: 4px solid #4CAF50;
        padding-left: 1rem;
        margin: 1rem 0;
    }
    .risk-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-low {
        background-color: #e8f5e8;
        border-left: 4px solid #4CAF50;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)