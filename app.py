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
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # 避免huggingface的并行错误

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 必须是第一个Streamlit命令
import streamlit as st
st.set_page_config(page_title="AI 测试用例生成系统", layout="wide")

# 导入后端模块
from backend.database import Database
from backend.knowledge_base import KnowledgeBase
from backend.testcase_generator import TestCaseGenerator
from backend.document_processor import DocumentProcessor
from backend.ai_client import AIClient
from backend.qa_logger import QALogger

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
        # 初始化数据库实例 - 使用绝对路径
        st.session_state.db = Database(db_path=DB_PATH)
        
        # 知识库使用自定义路径
        kb_dir = os.path.join(DATA_DIR, "knowledge_base")
        st.session_state.kb = KnowledgeBase(kb_dir=kb_dir, db_path=DB_PATH)
        
        # 测试用例生成器使用自定义输出目录
        output_dir = os.path.join(DATA_DIR, "outputs")
        st.session_state.testcase_gen = TestCaseGenerator(output_dir=output_dir)
        
        # 文档处理器
        st.session_state.document_processor = DocumentProcessor()
        
        # AI客户端
        st.session_state.ai_client = AIClient(knowledge_base=st.session_state.kb)
        
        # 问答日志记录器
        log_dir = os.path.join(BASE_DIR, "log")
        st.session_state.qa_logger = QALogger(log_dir=log_dir)
        
        # 初始化问答相关状态
        st.session_state.qa_relevant_results = []
        st.session_state.qa_selected_refs = []
        st.session_state.qa_generated_answer = None
        st.session_state.show_stats = False
        
        # 创建一个简单的会话ID（用于用户标识）
        st.session_state.session_id = f"{int(time.time())}_{hash(str(time.time()))}"
        
        st.session_state.initialized = True
        st.toast("系统初始化完成", icon="✅")
    except Exception as init_error:
        st.error(f"初始化失败: {str(init_error)}")
        st.error("请检查配置文件或依赖项安装情况")
        st.stop()

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["生成测试用例", "历史记录", "知识库管理", "知识库内容"])

if page == "生成测试用例":
    st.title("AI 测试用例生成系统 - 简化流程")
    
    # 初始化会话状态（简化流程：0:未开始, 1:需求分析, 2:测试点, 3:测试用例）
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
        if st.button("开始生成流程", key="start_generation"):
            try:
                # 保存文件并读取内容
                file_path = save_uploaded_file(uploaded_file)
                st.info(f"文件已保存到: {file_path}")
                st.session_state.doc_text = st.session_state.document_processor.read_file(file_path)
                st.session_state.file_path = file_path
                st.session_state.original_filename = uploaded_file.name
                st.session_state.generation_step = 1
                st.rerun()
            except Exception as file_error:
                st.error(f"文件处理失败: {str(file_error)}")
    
    # 第一步：生成文档总结
    if st.session_state.generation_step >= 1:
        st.header("第一步：需求文档分析")
        
        if st.session_state.current_summary == "":
            with st.spinner("正在进行全面的需求文档分析..."):
                try:
                    st.session_state.current_summary = st.session_state.ai_client.enhanced_generate_summary_step(
                        st.session_state.doc_text
                    )
                    st.success("需求文档分析完成！")
                except Exception as summary_error:
                    st.error(f"需求分析失败: {str(summary_error)}")
                    st.stop()
        
        # 可编辑的总结区域
        st.subheader("需求文档分析（可编辑）")
        edited_summary = st.text_area(
            "编辑需求文档分析",
            value=st.session_state.current_summary,
            height=300,
            key="summary_editor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重新生成分析", type="secondary", key="regenerate_summary"):
                st.session_state.current_summary = ""
                st.rerun()
        with col2:
            if st.button("确认分析并进入下一步", type="primary", key="confirm_summary"):
                st.session_state.current_summary = edited_summary
                st.session_state.generation_step = 2
                st.rerun()
    
    # 第二步：生成测试点文档
    if st.session_state.generation_step >= 2:
        st.header("第二步：测试点文档生成")
        
        if st.session_state.current_requirement_analysis == "":
            with st.spinner("正在生成测试点文档..."):
                try:
                    test_points, analysis_report = st.session_state.ai_client.enhanced_generate_test_points_step(
                        st.session_state.current_summary
                    )
                    st.session_state.current_requirement_analysis = test_points
                    st.session_state.current_analysis_report = analysis_report
                    st.success("测试点文档生成完成！")
                except Exception as analysis_error:
                    st.error(f"测试点生成失败: {str(analysis_error)}")
                    st.stop()
        
        # 可编辑的测试点文档区域
        st.subheader("测试点文档（可编辑）")
        edited_requirement_analysis = st.text_area(
            "编辑测试点文档",
            value=st.session_state.current_requirement_analysis,
            height=300,
            key="requirement_analysis_editor"
        )
        
        # 显示验证报告（只读）
        with st.expander("测试点验证报告", expanded=False):
            st.text_area(
                "验证报告",
                value=st.session_state.current_analysis_report,
                height=200,
                key="analysis_report_viewer",
                disabled=True
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
            if st.button("确认测试点并生成测试用例", type="primary", key="confirm_analysis"):
                st.session_state.current_requirement_analysis = edited_requirement_analysis
                st.session_state.generation_step = 3
                st.rerun()
    
    # 第三步：生成测试用例（直接从测试点生成）
    if st.session_state.generation_step >= 3:
        st.header("第三步：测试用例生成")
        
        if st.session_state.current_test_cases == "":
            with st.spinner("正在从测试点生成详细测试用例..."):
                try:
                    # 直接从测试点生成测试用例，跳过决策表
                    test_cases, test_validation = st.session_state.ai_client.generate_test_cases_from_test_points(
                        st.session_state.current_requirement_analysis
                    )
                    st.session_state.current_test_cases = test_cases
                    st.session_state.current_test_validation = test_validation
                    st.success("测试用例生成完成！")
                except Exception as testcase_error:
                    # 如果新方法不存在，尝试使用旧方法
                    try:
                        test_cases, test_validation = st.session_state.ai_client.enhanced_generate_test_cases_step(
                            "",  # 空的决策表
                            st.session_state.current_requirement_analysis
                        )
                        st.session_state.current_test_cases = test_cases
                        st.session_state.current_test_validation = test_validation
                        st.success("测试用例生成完成！")
                    except Exception as fallback_error:
                        st.error(f"测试用例生成失败: {str(testcase_error)}")
                        st.stop()
        
        # 可编辑的测试用例区域
        st.subheader("测试用例（可编辑）")
        edited_test_cases = st.text_area(
            "编辑测试用例",
            value=st.session_state.current_test_cases,
            height=400,
            key="test_cases_editor"
        )
        
        # 显示验证报告（只读）
        with st.expander("测试用例验证报告", expanded=False):
            st.text_area(
                "验证报告",
                value=st.session_state.current_test_validation,
                height=200,
                key="test_validation_viewer",
                disabled=True
            )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("返回上一步", type="secondary", key="back_to_step2"):
                st.session_state.generation_step = 2
                st.rerun()
        with col2:
            if st.button("重新生成测试用例", type="secondary", key="regenerate_testcases"):
                st.session_state.current_test_cases = ""
                st.session_state.current_test_validation = ""
                st.rerun()
        with col3:
            if st.button("完成并生成Excel", type="primary", key="finish_and_generate"):
                st.session_state.current_test_cases = edited_test_cases
                
                # 生成 Excel 文件
                try:
                    output_path = st.session_state.testcase_gen.generate_excel(
                        st.session_state.current_test_cases, 
                        st.session_state.original_filename
                    )
                    st.success(f"Excel 文件已生成: {output_path}")
                    
                    # 保存记录到数据库
                    try:
                        record_id = st.session_state.db.add_record(
                            original_filename=st.session_state.original_filename,
                            file_path=st.session_state.file_path,
                            output_filename=os.path.basename(output_path),
                            output_path=output_path,
                            summary=st.session_state.current_summary,
                            requirement_analysis=st.session_state.current_requirement_analysis,
                            decision_table="",  # 决策表字段留空
                            test_cases=st.session_state.current_test_cases,
                            test_validation=st.session_state.current_test_validation
                        )
                        st.info(f"记录已保存到数据库，ID: {record_id}")
                    except Exception as db_error:
                        st.warning(f"保存记录失败: {str(db_error)}")
                    
                    # 提供下载链接
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
        
        # 重置流程按钮
        st.markdown("---")
        if st.button("重新开始新流程", type="secondary", key="reset_workflow"):
            for key in ['generation_step', 'doc_text', 'current_summary', 'current_requirement_analysis', 
                       'current_analysis_report', 'current_test_cases', 'current_test_validation', 
                       'file_path', 'original_filename']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("流程已重置，可以开始新的生成了！")
            st.rerun()

elif page == "历史记录":
    st.title("历史生成记录")
    
    try:
        records = st.session_state.db.get_records()
    except Exception as records_error:
        st.error(f"加载历史记录失败: {str(records_error)}")
        records = []
    
    if not records:
        st.info("暂无历史记录")
    else:
        # 处理删除操作
        if 'delete_record_id' in st.session_state:
            record_id = st.session_state.delete_record_id
            try:
                success = st.session_state.db.delete_record(record_id)
                if success:
                    st.success(f"已删除记录 ID: {record_id}")
                    # 清除删除状态
                    del st.session_state.delete_record_id
                    # 重新加载页面
                    st.rerun()
                else:
                    st.error("删除记录失败")
            except Exception as delete_error:
                st.error(f"删除记录时出错: {str(delete_error)}")
                st.text(traceback.format_exc())
        
        # 添加清空选择按钮
        if 'selected_record' in st.session_state:
            if st.button("清除选择", key="clear_selection"):
                del st.session_state.selected_record
        
        for record in records:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"{record['original_filename']} - {record['created_at']}")
                    st.write(f"**原始文件:** {record['original_filename']}")
                    st.write(f"**生成时间:** {record['created_at']}")
                    
                    # 使用文本区域显示内容
                    st.write("**需求文档分析**")
                    st.text_area("", record.get('summary', '无分析信息'), 
                                height=100, key=f"summary_{record['id']}", disabled=True)
                    
                    st.write("**测试点文档**")
                    st.text_area("", record.get('requirement_analysis', '无测试点信息'), 
                                height=100, key=f"analysis_{record['id']}", disabled=True)
                    
                    st.write("**测试用例验证报告**")
                    st.text_area("", record.get('test_validation', '无验证报告'), 
                                height=100, key=f"validation_{record['id']}", disabled=True)
                
                with col2:
                    # 下载按钮
                    file_exists = os.path.exists(record['output_path'])
                    if file_exists:
                        with open(record['output_path'], "rb") as f:
                            st.download_button(
                                label="下载测试用例",
                                data=f,
                                file_name=record['output_filename'],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{record['id']}"
                            )
                    else:
                        st.error(f"文件不存在: {record['output_path']}")
                    
                    # 查看详情按钮
                    btn_key = f"detail_{record['id']}"
                    if st.button(f"查看完整记录", key=btn_key):
                        st.session_state.selected_record = record['id']
                    
                    # 删除按钮
                    delete_key = f"delete_{record['id']}"
                    if st.button(f"删除记录", key=delete_key, type="secondary"):
                        st.session_state.delete_record_id = record['id']
                        # 立即触发重新运行以执行删除
                        st.rerun()
                
                # 如果选择了查看详情，显示完整内容
                if 'selected_record' in st.session_state and st.session_state.selected_record == record['id']:
                    with st.expander("测试用例详情", expanded=True):
                        st.text_area("", record.get('test_cases', '无测试用例信息'), 
                                    height=300, key=f"testcases_{record['id']}", disabled=True)
                
                st.divider()

# 知识库管理和知识库内容页面保持不变
elif page == "知识库管理":
    # ... (知识库管理页面代码保持不变，使用之前完整的代码)
    pass

elif page == "知识库内容":
    # ... (知识库内容页面代码保持不变，使用之前完整的代码)
    pass

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
</style>
""", unsafe_allow_html=True)