# 禁用文件监视器避免错误
import os
import sys
from pathlib import Path

# 设置基础路径
BASE_DIR = "E:/sm-ai-testcase"
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

# 继续其他导入
import time
from datetime import datetime
from typing import List, Dict
import traceback

# 导入后端模块
from backend.database import Database
from backend.knowledge_base import KnowledgeBase
from backend.testcase_generator import TestCaseGenerator
from backend.document_processor import DocumentProcessor
from backend.ai_client import AIClient

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
        st.session_state.kb = KnowledgeBase(kb_dir=kb_dir)
        
        # 测试用例生成器使用自定义输出目录
        output_dir = os.path.join(DATA_DIR, "outputs")
        st.session_state.testcase_gen = TestCaseGenerator(output_dir=output_dir)
        
        # 文档处理器
        st.session_state.document_processor = DocumentProcessor()
        
        # AI客户端
        st.session_state.ai_client = AIClient(knowledge_base=st.session_state.kb)
        
        st.session_state.initialized = True
        st.toast("系统初始化完成", icon="✅")
    except Exception as e:
        st.error(f"初始化失败: {str(e)}")
        st.error("请检查配置文件或依赖项安装情况")
        st.stop()

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["生成测试用例", "历史记录", "知识库管理"])

# 显示路径信息
st.sidebar.subheader("系统信息")
st.sidebar.write(f"数据目录: {DATA_DIR}")
st.sidebar.write(f"数据库路径: {DB_PATH}")
st.sidebar.write(f"上传目录: {os.path.join(DATA_DIR, 'uploads')}")
st.sidebar.write(f"输出目录: {os.path.join(DATA_DIR, 'outputs')}")
st.sidebar.write(f"知识库目录: {os.path.join(DATA_DIR, 'knowledge_base')}")

# 检查目录是否存在
st.sidebar.write("目录状态:")
st.sidebar.write(f"- 上传目录: {'存在' if os.path.exists(os.path.join(DATA_DIR, 'uploads')) else '不存在'}")
st.sidebar.write(f"- 输出目录: {'存在' if os.path.exists(os.path.join(DATA_DIR, 'outputs')) else '不存在'}")
st.sidebar.write(f"- 知识库目录: {'存在' if os.path.exists(os.path.join(DATA_DIR, 'knowledge_base')) else '不存在'}")
st.sidebar.write(f"- 数据库文件: {'存在' if os.path.exists(DB_PATH) else '不存在'}")

if page == "生成测试用例":
    st.title("AI 测试用例生成系统")
    
    # 文件上传
    uploaded_file = st.file_uploader("上传 Word 或 PDF 需求文档", type=["docx", "pdf"])
    
    # 提示词输入
    st.subheader("提示词配置")
    col1, col2 = st.columns(2)
    with col1:
        summary_prompt = st.text_area("总结提示词", value="请总结文档的主要内容，提取关键功能点和业务规则。")
        analysis_prompt = st.text_area("需求分析提示词", value="请基于文档总结，应用等价类划分和边界值分析方法生成需求分析点。")
    with col2:
        decision_prompt = st.text_area("决策表提示词", value="根据需求分析点生成测试决策表，包含所有可能的输入组合和预期输出。")
        testcase_prompt = st.text_area("测试用例提示词", value="根据决策表生成详细的测试用例，包含测试步骤、预期结果和优先级。")
    
    if st.button("生成测试用例") and uploaded_file:
        # 保存文件并读取内容
        try:
            file_path = save_uploaded_file(uploaded_file)
            st.info(f"文件已保存到: {file_path}")
            doc_text = st.session_state.document_processor.read_file(file_path)
        except Exception as e:
            st.error(f"文件处理失败: {str(e)}")
            st.stop()
        
        # 进度显示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 阶段1: 文档总结与需求分析
        progress_bar.progress(5)
        status_text.text("阶段1/3: 生成文档总结...")
        try:
            summary = st.session_state.ai_client.generate_summary(doc_text, summary_prompt)
        except Exception as e:
            st.error(f"生成总结失败: {str(e)}")
            st.stop()
        
        progress_bar.progress(25)
        status_text.text("阶段1/3: 生成需求分析点...")
        try:
            requirement_analysis, analysis_report = st.session_state.ai_client.generate_requirement_analysis(summary)
        except Exception as e:
            st.error(f"需求分析失败: {str(e)}")
            st.stop()
        
        # 显示阶段1结果
        with st.expander("文档总结", expanded=True):
            st.write(summary)
        
        with st.expander("需求分析点", expanded=True):
            st.write(requirement_analysis)
        
        with st.expander("需求分析验证报告", expanded=True):
            st.write(analysis_report)
        
        # 阶段2: 决策表生成
        progress_bar.progress(50)
        status_text.text("阶段2/3: 生成决策表...")
        try:
            decision_table = st.session_state.ai_client.generate_decision_table(
                requirement_analysis, 
                f"{decision_prompt}\n需求分析验证报告：{analysis_report}"
            )
        except Exception as e:
            st.error(f"决策表生成失败: {str(e)}")
            st.stop()
        
        # 显示阶段2结果
        with st.expander("决策表", expanded=True):
            st.write(decision_table)
        
        # 阶段3: 测试用例生成
        progress_bar.progress(75)
        status_text.text("阶段3/3: 生成测试用例...")
        try:
            test_cases, test_validation = st.session_state.ai_client.generate_test_cases(
                decision_table, 
                doc_text, 
                testcase_prompt
            )
        except Exception as e:
            st.error(f"测试用例生成失败: {str(e)}")
            st.stop()
        
        progress_bar.progress(95)
        status_text.text("阶段3/3: 验证测试用例...")
        
        # 显示阶段3结果
        with st.expander("测试用例", expanded=True):
            st.write(test_cases)
        
        with st.expander("测试用例验证报告", expanded=True):
            st.write(test_validation)
        
        # 生成 Excel 文件
        try:
            output_path = st.session_state.testcase_gen.generate_excel(test_cases, uploaded_file.name)
            st.success(f"Excel 文件已生成: {output_path}")
        except Exception as e:
            st.error(f"生成 Excel 文件失败: {str(e)}")
            st.stop()
        
        # 保存记录到数据库
        try:
            record_id = st.session_state.db.add_record(
                original_filename=uploaded_file.name,
                file_path=file_path,
                output_filename=os.path.basename(output_path),
                output_path=output_path,
                summary=summary,
                requirement_analysis=requirement_analysis,
                decision_table=decision_table,
                test_cases=test_cases,
                test_validation=test_validation
            )
            st.info(f"记录已保存到数据库，ID: {record_id}")
        except Exception as e:
            st.warning(f"保存记录失败: {str(e)}")
        
        # 完成状态
        progress_bar.progress(100)
        status_text.text("流程完成！")
        st.success("✅ 测试用例生成完成！")
        
        # 提供下载链接
        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                st.download_button(
                    label="下载 Excel 测试用例",
                    data=f,
                    file_name=os.path.basename(output_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )
        else:
            st.error(f"Excel文件未找到: {output_path}")

elif page == "历史记录":
    st.title("历史生成记录")
    
    records = st.session_state.db.get_records()
    if not records:
        st.info("暂无历史记录")
    else:
        # 添加清空选择按钮
        if 'selected_record' in st.session_state:
            if st.button("清除选择"):
                del st.session_state.selected_record
        
        for record in records:
            with st.container():
                st.subheader(f"{record['original_filename']} - {record['created_at']}")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**原始文件:** {record['original_filename']}")
                    st.write(f"**生成时间:** {record['created_at']}")
                    
                    # 使用文本区域显示内容
                    st.write("**文档总结**")
                    st.text_area("", record.get('summary', '无总结信息'), 
                                height=100, key=f"summary_{record['id']}", disabled=True)
                    
                    st.write("**需求分析点**")
                    st.text_area("", record.get('requirement_analysis', '无需求分析信息'), 
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
                
                # 如果选择了查看详情，显示完整内容
                if 'selected_record' in st.session_state and st.session_state.selected_record == record['id']:
                    with st.expander("决策表详情", expanded=True):
                        st.text_area("", record.get('decision_table', '无决策表信息'), 
                                    height=200, key=f"decision_{record['id']}", disabled=True)
                    
                    with st.expander("测试用例详情", expanded=True):
                        st.text_area("", record.get('test_cases', '无测试用例信息'), 
                                    height=300, key=f"testcases_{record['id']}", disabled=True)
                
                st.divider()  # 添加分隔线

elif page == "知识库管理":
    st.title("知识库管理")
    
    st.subheader("知识库状态")
    if hasattr(st.session_state.kb, 'vectorstore') and st.session_state.kb.vectorstore:
        st.success("知识库已成功加载")
        try:
            doc_count = len(st.session_state.kb.vectorstore.docstore._dict)
            st.write(f"包含文档数: {doc_count}")
        except:
            st.info("无法获取文档数量")
    else:
        st.warning("知识库未完全初始化")
    
    # 决策表生成测试
    st.subheader("知识库检索测试")
    test_query = st.text_input("输入测试查询", "用户登录功能，包含管理员和普通用户角色")
    if st.button("测试知识库引用"):
        try:
            # 执行知识库搜索
            knowledge_context = st.session_state.kb.search(test_query, k=3, full_content=True)
            st.write("### 知识库引用内容")
            for i, content in enumerate(knowledge_context):
                st.text_area(f"知识库结果 {i+1}", content, height=150)
        except Exception as e:
            st.error(f"测试失败: {str(e)}")
    
    # 上传知识文件
    st.subheader("上传知识文件")
    knowledge_file = st.file_uploader(
        "上传 Excel、CSV 或文本文件到知识库", 
        type=["csv", "xlsx", "xls", "txt", "docx", "pdf"]
    )
    
    if knowledge_file and st.button("上传到知识库"):
        with st.spinner("上传并处理文件中..."):
            try:
                # 创建上传目录
                kb_dir = os.path.join(DATA_DIR, "knowledge_base", "files")
                os.makedirs(kb_dir, exist_ok=True)
                
                # 保存文件
                file_path = os.path.join(kb_dir, knowledge_file.name)
                with open(file_path, "wb") as f:
                    f.write(knowledge_file.getbuffer())
                st.info(f"文件已保存到: {file_path}")
                
                # 添加到知识库
                st.session_state.kb.add_document(file_path)
                st.session_state.db.add_knowledge_file(knowledge_file.name, file_path)
                st.success("文件已成功添加到知识库")
            except Exception as e:
                error_msg = f"添加文件到知识库失败: {str(e)}"
                st.error(error_msg)
                with st.expander("查看错误详情"):
                    st.text(traceback.format_exc())
    
    # 显示知识库文件列表
    st.subheader("知识库文件列表")
    try:
        kb_files_dir = os.path.join(DATA_DIR, "knowledge_base", "files")
        if os.path.exists(kb_files_dir):
            kb_files = os.listdir(kb_files_dir)
        else:
            kb_files = []
    except Exception as e:
        st.error(f"加载知识库文件列表失败: {str(e)}")
        kb_files = []
    
    if not kb_files:
        st.info("知识库中暂无文件")
    else:
        for i, filename in enumerate(kb_files):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i+1}. {filename}")
            with col2:
                if st.button(f"删除", key=f"del_{filename}"):
                    try:
                        file_path = os.path.join(kb_files_dir, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        st.success(f"已删除文件: {filename}")
                        
                        # 重新初始化知识库
                        st.session_state.kb = KnowledgeBase(kb_dir=os.path.join(DATA_DIR, "knowledge_base"))
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"删除文件失败: {str(e)}")
    
    # 知识库搜索
    st.subheader("知识库搜索")
    query = st.text_input("输入查询内容")
    if query and st.button("搜索"):
        results = st.session_state.kb.search(query)
        if results:
            st.write("搜索结果:")
            for i, result in enumerate(results, 1):
                with st.expander(f"结果 {i}"):
                    st.write(result)
        else:
            st.info("没有找到相关结果")
            
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