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
    st.title("AI 测试用例生成系统 - 分步生成")
    
    # 初始化会话状态
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 0  # 0: 未开始, 1: 总结, 2: 需求分析, 3: 决策表, 4: 测试用例
    if 'doc_text' not in st.session_state:
        st.session_state.doc_text = ""
    if 'current_summary' not in st.session_state:
        st.session_state.current_summary = ""
    if 'current_requirement_analysis' not in st.session_state:
        st.session_state.current_requirement_analysis = ""
    if 'current_analysis_report' not in st.session_state:
        st.session_state.current_analysis_report = ""
    if 'current_decision_table' not in st.session_state:
        st.session_state.current_decision_table = ""
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
            if st.button("确认测试点并进入下一步", type="primary", key="confirm_analysis"):
                st.session_state.current_requirement_analysis = edited_requirement_analysis
                st.session_state.generation_step = 3
                st.rerun()
    
    # 第三步：生成决策表
    if st.session_state.generation_step >= 3:
        st.header("第三步：决策表生成")
        
        if st.session_state.current_decision_table == "":
            with st.spinner("正在生成测试决策表..."):
                try:
                    st.session_state.current_decision_table = st.session_state.ai_client.enhanced_generate_decision_table_step(
                        st.session_state.current_requirement_analysis
                    )
                    st.success("决策表生成完成！")
                except Exception as decision_error:
                    st.error(f"决策表生成失败: {str(decision_error)}")
                    st.stop()
        
        # 可编辑的决策表区域
        st.subheader("决策表（可编辑）")
        edited_decision_table = st.text_area(
            "编辑决策表",
            value=st.session_state.current_decision_table,
            height=300,
            key="decision_table_editor"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("返回上一步", type="secondary", key="back_to_step2"):
                st.session_state.generation_step = 2
                st.rerun()
        with col2:
            if st.button("重新生成决策表", type="secondary", key="regenerate_decision"):
                st.session_state.current_decision_table = ""
                st.rerun()
        with col3:
            if st.button("确认决策表并进入下一步", type="primary", key="confirm_decision"):
                st.session_state.current_decision_table = edited_decision_table
                st.session_state.generation_step = 4
                st.rerun()
    
    # 第四步：生成测试用例
    if st.session_state.generation_step >= 4:
        st.header("第四步：测试用例生成")
        
        if st.session_state.current_test_cases == "":
            with st.spinner("正在生成详细测试用例..."):
                try:
                    test_cases, test_validation = st.session_state.ai_client.enhanced_generate_test_cases_step(
                        st.session_state.current_decision_table,
                        st.session_state.current_requirement_analysis
                    )
                    st.session_state.current_test_cases = test_cases
                    st.session_state.current_test_validation = test_validation
                    st.success("测试用例生成完成！")
                except Exception as testcase_error:
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
            if st.button("返回上一步", type="secondary", key="back_to_step3"):
                st.session_state.generation_step = 3
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
                            decision_table=st.session_state.current_decision_table,
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
                       'current_analysis_report', 'current_decision_table', 'current_test_cases', 
                       'current_test_validation', 'file_path', 'original_filename']:
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
                    with st.expander("决策表详情", expanded=True):
                        st.text_area("", record.get('decision_table', '无决策表信息'), 
                                    height=200, key=f"decision_{record['id']}", disabled=True)
                    
                    with st.expander("测试用例详情", expanded=True):
                        st.text_area("", record.get('test_cases', '无测试用例信息'), 
                                    height=300, key=f"testcases_{record['id']}", disabled=True)
                
                st.divider()

elif page == "知识库管理":
    st.title("知识库管理")
    
    # 重建索引按钮
    if st.button("完全重建知识库索引", type="secondary", key="rebuild_index"):
        with st.spinner("重建整个知识库索引中..."):
            try:
                success = st.session_state.kb.rebuild_index()
                if success:
                    st.success("知识库索引已完全重建！")
                else:
                    st.error("重建索引失败，请查看日志")
            except Exception as rebuild_error:
                st.error(f"重建索引失败: {str(rebuild_error)}")
                st.text(traceback.format_exc())
    
    # 索引状态
    st.subheader("索引状态")
    try:
        index_status = st.session_state.kb.get_index_status()
        st.write(f"索引存在: {'是' if index_status['index_exists'] else '否'}")
        st.write(f"文档块数量: {index_status['document_count']}")
        st.write(f"知识文件数量: {index_status['file_count']}")
        
        if index_status['document_count'] == 0 and index_status['file_count'] > 0:
            st.warning("索引中无文档块但存在知识文件，请重建索引")
    except Exception as status_error:
        st.error(f"获取索引状态失败: {str(status_error)}")
        st.text(traceback.format_exc())
    
    # 知识库搜索测试 - 显示所有结果和相似度
    st.subheader("知识库检索测试")
    
    # 配置选项
    col1, col2 = st.columns([3, 1])
    with col1:
        test_query = st.text_input(
            "输入测试查询", 
            "用户登录功能，包含管理员和普通用户角色", 
            key="test_query_input"
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
    
    if st.button("执行知识库检索", key="test_kb_search", type="primary"):
        try:
            if not test_query.strip():
                st.warning("请输入查询内容")
            else:
                # 执行知识库搜索，返回带分数的结果
                knowledge_results = st.session_state.kb.search_with_score(
                    test_query.strip(), 
                    k=result_count
                )
                
                if not knowledge_results:
                    st.warning("未找到相关结果")
                else:
                    st.success(f"找到 {len(knowledge_results)} 个相关结果")
                    
                    # 计算相似度百分比
                    processed_results = []
                    for content, metadata, distance in knowledge_results:
                        similarity = st.session_state.kb.get_similarity_percentage(distance)
                        processed_results.append({
                            "content": content,
                            "metadata": metadata,
                            "distance": distance,
                            "similarity": similarity
                        })
                    
                    # 按相似度排序
                    processed_results.sort(key=lambda x: x["similarity"], reverse=True)
                    
                    # 创建摘要表格
                    table_data = []
                    for i, result in enumerate(processed_results):
                        metadata = result["metadata"]
                        content = result["content"]
                        
                        table_data.append({
                            "排名": i + 1,
                            "相似度": result["similarity"],
                            "距离分数": f"{result['distance']:.4f}",
                            "文件名": metadata.get('source', '未知'),
                            "类型": metadata.get('type', '未知'),
                            "工作表": metadata.get('sheet', 'N/A'),
                            "行号": metadata.get('row', 'N/A'),
                            "内容摘要": (content[:80] + "...") if len(content) > 80 else content
                        })
                    
                    # 显示摘要表格
                    df_summary = pd.DataFrame(table_data)
                    
                    # 使用Streamlit的dataframe组件显示，并设置样式
                    st.dataframe(
                        df_summary,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "排名": st.column_config.NumberColumn(width="small"),
                            "相似度": st.column_config.ProgressColumn(
                                "相似度(%)",
                                format="%.1f",
                                min_value=0,
                                max_value=100,
                            ),
                            "距离分数": st.column_config.TextColumn(width="medium"),
                            "内容摘要": st.column_config.TextColumn(width="large"),
                        }
                    )
                    
                    # 详细结果展示
                    st.subheader("详细结果")
                    
                    for i, result in enumerate(processed_results):
                        metadata = result["metadata"]
                        content = result["content"]
                        similarity = result["similarity"]
                        distance = result["distance"]
                        
                        # 创建可展开的区域
                        with st.expander(
                            f"结果 {i+1}: {metadata.get('source', '未知文件')} - 相似度: {similarity:.1f}%",
                            expanded=(i == 0)
                        ):
                            # 两列布局
                            col_left, col_right = st.columns([3, 1])
                            
                            with col_left:
                                st.text_area(
                                    "文档内容",
                                    value=content,
                                    height=250,
                                    key=f"detail_content_{i}",
                                    disabled=False
                                )
                            
                            with col_right:
                                # 相似度指标
                                st.metric(
                                    "相似度", 
                                    f"{similarity:.1f}%",
                                    delta=f"距离: {distance:.4f}" if distance < 1.0 else None,
                                    delta_color="normal" if similarity >= 70 else "off"
                                )
                                
                                # 质量评估
                                if similarity >= 90:
                                    st.success("✓ 高度相关")
                                elif similarity >= 70:
                                    st.info("✓ 中等相关")
                                elif similarity >= 50:
                                    st.warning("△ 一般相关")
                                else:
                                    st.error("○ 弱相关")
                                
                                # 元数据详情
                                st.write("**文件信息**")
                                st.caption(f"来源: {metadata.get('source', '未知')}")
                                st.caption(f"类型: {metadata.get('type', '未知')}")
                                
                                if metadata.get('sheet'):
                                    st.caption(f"工作表: {metadata['sheet']}")
                                if metadata.get('row'):
                                    st.caption(f"行号: {metadata['row']}")
                                if metadata.get('chunk_index'):
                                    st.caption(f"分块: {metadata['chunk_index']}/{metadata.get('total_chunks', '?')}")
                            
                            # 底部操作按钮
                            st.markdown("---")
                            col_btn1, col_btn2, col_btn3 = st.columns(3)
                            with col_btn1:
                                if st.button("复制内容", key=f"copy_{i}"):
                                    st.write("内容已复制到剪贴板")
                            with col_btn2:
                                if st.button("标记为相关", key=f"mark_relevant_{i}"):
                                    st.write("已标记为相关")
                            with col_btn3:
                                if st.button("查看源文件", key=f"view_source_{i}"):
                                    st.write("正在打开源文件...")
                    
                    # 添加统计信息
                    st.markdown("---")
                    st.subheader("检索统计")
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    
                    with col_stat1:
                        avg_similarity = sum(r["similarity"] for r in processed_results) / len(processed_results)
                        st.metric("平均相似度", f"{avg_similarity:.1f}%")
                    
                    with col_stat2:
                        max_similarity = max(r["similarity"] for r in processed_results)
                        st.metric("最高相似度", f"{max_similarity:.1f}%")
                    
                    with col_stat3:
                        min_similarity = min(r["similarity"] for r in processed_results)
                        st.metric("最低相似度", f"{min_similarity:.1f}%")
                    
                    with col_stat4:
                        st.metric("结果总数", f"{len(processed_results)}条")
                    
                    # 相似度分布
                    st.caption(f"相似度分布: ≥90%: {sum(1 for r in processed_results if r['similarity'] >= 90)}个, "
                             f"70-89%: {sum(1 for r in processed_results if 70 <= r['similarity'] < 90)}个, "
                             f"50-69%: {sum(1 for r in processed_results if 50 <= r['similarity'] < 70)}个, "
                             f"<50%: {sum(1 for r in processed_results if r['similarity'] < 50)}个")
        
        except Exception as search_error:
            st.error(f"检索失败: {str(search_error)}")
            st.text(traceback.format_exc())
    
    # 智能问答功能 - 修改为用户先选择参考内容
    st.markdown("---")
    st.subheader("智能问答")
    
    # 问答配置
    col1, col2 = st.columns([3, 1])
    with col1:
        user_question = st.text_area(
            "输入您的问题",
            "如何设计用户登录功能的测试用例？",
            height=100,
            key="user_question_input"
        )
    with col2:
        similarity_threshold = st.number_input(
            "参考阈值(%)",
            min_value=0,
            max_value=100,
            value=75,
            step=5,
            key="qa_similarity_threshold"
        )
        max_references = st.number_input(
            "最大参考数",
            min_value=1,
            max_value=20,
            value=10,
            step=1,
            key="max_references"
        )
    
    # 第一步：检索参考内容
    if st.button("检索参考内容", key="search_references", type="primary"):
        try:
            if not user_question.strip():
                st.warning("请输入问题")
            else:
                with st.spinner("正在检索知识库..."):
                    # 从知识库检索相关内容
                    knowledge_results = st.session_state.kb.search_with_score(
                        user_question.strip(), 
                        k=20  # 检索较多结果
                    )
                    
                    # 过滤相似度阈值以上的结果
                    relevant_results = []
                    
                    for content, metadata, distance in knowledge_results:
                        similarity = st.session_state.kb.get_similarity_percentage(distance)
                        if similarity >= similarity_threshold:
                            # 提取有用的信息
                            source = metadata.get('source', '未知来源')
                            file_id = hash(source)  # 使用哈希作为文件ID
                            
                            # 生成唯一标识符
                            ref_id = f"{file_id}_{metadata.get('row', '0')}_{metadata.get('chunk_index', '0')}"
                            
                            relevant_results.append({
                                "id": ref_id,
                                "content": content,
                                "metadata": metadata,
                                "distance": distance,
                                "similarity": similarity,
                                "source": source,
                                "selected": True  # 默认选中
                            })
                    
                    # 保存到会话状态
                    st.session_state.qa_relevant_results = relevant_results
                    st.session_state.qa_selected_refs = [r["id"] for r in relevant_results]
                    st.session_state.qa_generated_answer = None
                    st.session_state.show_stats = False
                    
                    # 显示检索结果摘要
                    if relevant_results:
                        st.success(f"找到 {len(relevant_results)} 个相关参考（相似度≥{similarity_threshold}%）")
                        st.info("请检查以下参考内容，取消选中不需要的参考，然后点击『基于选定参考生成答案』")
                    else:
                        st.warning(f"没有找到相似度≥{similarity_threshold}%的相关内容")
                        
                        if st.button("使用较低阈值重新检索", key="retry_lower_threshold"):
                            st.session_state.qa_similarity_threshold = 50
                            st.rerun()
        
        except Exception as search_error:
            st.error(f"检索失败: {str(search_error)}")
    
    # 显示参考内容并允许用户选择
    if st.session_state.qa_relevant_results:
        st.markdown("---")
        st.subheader("参考内容选择")
        
        # 统计信息
        total_refs = len(st.session_state.qa_relevant_results)
        selected_count = len(st.session_state.qa_selected_refs)
        
        st.info(f"共找到 {total_refs} 个参考，已选中 {selected_count} 个")
        
        # 全选/全不选按钮
        col_sel1, col_sel2, col_sel3 = st.columns([1, 1, 2])
        with col_sel1:
            if st.button("全选", key="select_all"):
                st.session_state.qa_selected_refs = [r["id"] for r in st.session_state.qa_relevant_results]
                st.rerun()
        with col_sel2:
            if st.button("全不选", key="deselect_all"):
                st.session_state.qa_selected_refs = []
                st.rerun()
        with col_sel3:
            if st.button("只选相似度≥90%", key="select_high"):
                high_refs = [r["id"] for r in st.session_state.qa_relevant_results if r["similarity"] >= 90]
                st.session_state.qa_selected_refs = high_refs
                st.rerun()
        
        # 显示每个参考内容的复选框
        st.markdown("### 请选择要用于生成答案的参考内容:")
        
        for i, result in enumerate(st.session_state.qa_relevant_results):
            metadata = result["metadata"]
            content = result["content"]
            similarity = result["similarity"]
            
            # 创建复选框
            is_selected = result["id"] in st.session_state.qa_selected_refs
            
            # 使用列布局
            with st.container():
                col_check, col_content = st.columns([1, 10])
                
                with col_check:
                    # 复选框
                    checkbox_key = f"ref_checkbox_{result['id']}"
                    selected = st.checkbox(
                        "选择",
                        value=is_selected,
                        key=checkbox_key,
                        label_visibility="collapsed"
                    )
                    
                    # 更新选中状态
                    if selected and result["id"] not in st.session_state.qa_selected_refs:
                        st.session_state.qa_selected_refs.append(result["id"])
                    elif not selected and result["id"] in st.session_state.qa_selected_refs:
                        st.session_state.qa_selected_refs.remove(result["id"])
                    
                    # 显示相似度
                    st.metric("相似度", f"{similarity:.1f}%")
                
                with col_content:
                    with st.expander(f"参考 {i+1}: {result['source']}", expanded=False):
                        st.caption(f"来源: {result['source']}")
                        if metadata.get('sheet'):
                            st.caption(f"工作表: {metadata['sheet']}")
                        if metadata.get('row'):
                            st.caption(f"行号: {metadata['row']}")
                        
                        st.text_area(
                            "内容",
                            value=content,
                            height=200,
                            key=f"ref_content_{result['id']}",
                            disabled=True
                        )
            
            st.markdown("---")
        
        # 第二步：基于选定的参考生成答案
        st.markdown("### 生成答案")
        
        if selected_count == 0:
            st.warning("请至少选择一个参考内容")
        else:
            with st.expander(f"查看选定的 {selected_count} 个参考", expanded=False):
                for i, ref_id in enumerate(st.session_state.qa_selected_refs):
                    result = next((r for r in st.session_state.qa_relevant_results if r["id"] == ref_id), None)
                    if result:
                        st.write(f"**参考 {i+1}** - {result['source']} - 相似度: {result['similarity']:.1f}%")
                        content_preview = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                        st.text(content_preview)
                        st.markdown("---")
            
            # 生成答案按钮
            col_gen1, col_gen2 = st.columns([1, 3])
            with col_gen1:
                generate_clicked = st.button("基于选定参考生成答案", key="generate_answer", type="primary")
            
            with col_gen2:
                if st.session_state.qa_generated_answer:
                    if st.button("清空历史答案", key="clear_answer"):
                        st.session_state.qa_generated_answer = None
                        st.rerun()
            
            if generate_clicked:
                with st.spinner("正在基于选定参考生成专业答案..."):
                    try:
                        # 获取选定的参考内容
                        selected_contexts = []
                        for ref_id in st.session_state.qa_selected_refs:
                            result = next((r for r in st.session_state.qa_relevant_results if r["id"] == ref_id), None)
                            if result:
                                source = result["source"]
                                similarity = result["similarity"]
                                content = result["content"]
                                
                                context_text = f"来源: {source}\n相似度: {similarity:.1f}%\n\n{content}"
                                selected_contexts.append(context_text)
                        
                        # 调用AI生成答案
                        ai_answer = st.session_state.ai_client.answer_with_knowledge(
                            user_question.strip(),
                            selected_contexts
                        )
                        
                        # 保存答案到会话状态
                        st.session_state.qa_generated_answer = {
                            "question": user_question.strip(),
                            "answer": ai_answer,
                            "reference_count": selected_count,
                            "selected_ref_ids": st.session_state.qa_selected_refs.copy(),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 记录到日志
                        if st.session_state.qa_logger:
                            record_id = st.session_state.qa_logger.log_qa(
                                question=user_question.strip(),
                                answer=ai_answer,
                                reference_count=selected_count
                            )
                            st.session_state.qa_generated_answer["record_id"] = record_id
                        
                        st.success("答案生成完成！")
                        st.rerun()
                        
                    except Exception as ai_error:
                        st.error(f"AI生成答案失败: {str(ai_error)}")
        
        # 显示生成的答案和反馈功能
        if st.session_state.qa_generated_answer:
            st.markdown("---")
            st.subheader("🤖 AI 专业建议")
            
            answer_info = st.session_state.qa_generated_answer
            record_id = answer_info.get("record_id")
            
            st.markdown(f"**问题**: {answer_info['question']}")
            st.caption(f"生成时间: {answer_info['timestamp']} | 参考数量: {answer_info['reference_count']}个")
            
            # 获取当前反馈统计
            current_upvotes = 0
            current_downvotes = 0
            
            if record_id and st.session_state.qa_logger:
                record = st.session_state.qa_logger.get_record(record_id)
                if record:
                    current_upvotes = record.get("upvotes", 0)
                    current_downvotes = record.get("downvotes", 0)
            
            # 显示反馈统计
            col_fb1, col_fb2, col_fb3 = st.columns([1, 1, 2])
            with col_fb1:
                st.metric("👍 点赞", current_upvotes)
            with col_fb2:
                st.metric("👎 点踩", current_downvotes)
            with col_fb3:
                if current_upvotes + current_downvotes > 0:
                    positive_rate = current_upvotes / (current_upvotes + current_downvotes) * 100
                    st.metric("👍 率", f"{positive_rate:.1f}%")
            
            st.markdown("---")
            
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
            
            # 反馈按钮区域
            st.markdown("### 这个回答有帮助吗？")
            
            col_fb_btn1, col_fb_btn2, col_fb_btn3 = st.columns([1, 1, 4])
            
            with col_fb_btn1:
                if st.button(f"👍 点赞 ({current_upvotes})", key=f"upvote_{record_id}"):
                    if record_id and st.session_state.qa_logger:
                        user_ip = "user_" + str(hash(st.session_state.session_id))
                        success = st.session_state.qa_logger.add_feedback(record_id, "upvote", user_ip)
                        if success:
                            st.success("感谢您的反馈！")
                            st.rerun()
                        else:
                            st.warning("您已经给过反馈了")
            
            with col_fb_btn2:
                if st.button(f"👎 点踩 ({current_downvotes})", key=f"downvote_{record_id}"):
                    if record_id and st.session_state.qa_logger:
                        user_ip = "user_" + str(hash(st.session_state.session_id))
                        success = st.session_state.qa_logger.add_feedback(record_id, "downvote", user_ip)
                        if success:
                            st.success("感谢您的反馈！")
                            st.rerun()
                        else:
                            st.warning("您已经给过反馈了")
            
            with col_fb_btn3:
                if st.button("查看反馈详情", key=f"view_feedback_{record_id}"):
                    if record_id and st.session_state.qa_logger:
                        record = st.session_state.qa_logger.get_record(record_id)
                        if record and record.get("feedback"):
                            with st.expander("反馈详情", expanded=True):
                                st.write(f"总反馈数: {len(record['feedback'])}")
                                for fb in record["feedback"]:
                                    fb_type = "👍 点赞" if fb["type"] == "upvote" else "👎 点踩"
                                    st.write(f"- {fb_type} ({fb['timestamp']})")
            
            # 其他操作按钮
            st.markdown("---")
            st.markdown("### 其他操作")
            
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            
            with col_btn1:
                if st.button("复制答案", key=f"copy_answer_{record_id}"):
                    st.write("答案已复制到剪贴板")
            
            with col_btn2:
                if st.button("保存答案", key=f"save_answer_{record_id}"):
                    st.success("答案已保存")
            
            with col_btn3:
                if st.button("重新生成", key=f"regenerate_{record_id}"):
                    st.session_state.qa_generated_answer = None
                    st.rerun()
            
            with col_btn4:
                if st.button("查看统计", key=f"view_stats_{record_id}"):
                    st.session_state.show_stats = True
            
            # 显示统计信息
            if st.session_state.show_stats:
                st.markdown("---")
                st.subheader("📊 问答统计")
                
                if st.session_state.qa_logger:
                    daily_stats = st.session_state.qa_logger.get_daily_stats()
                    
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    
                    with col_stat1:
                        st.metric("今日问答数", daily_stats.get("total_qa", 0))
                    
                    with col_stat2:
                        st.metric("今日总点赞", daily_stats.get("total_upvotes", 0))
                    
                    with col_stat3:
                        st.metric("今日总点踩", daily_stats.get("total_downvotes", 0))
                    
                    with col_stat4:
                        feedback_rate = daily_stats.get("feedback_rate", 0)
                        st.metric("反馈率", f"{feedback_rate:.1f}%")
                    
                    # 问题频率统计
                    st.markdown("### 📈 问题频率统计")
                    
                    question_freq = st.session_state.qa_logger.get_question_frequency(days=7)
                    
                    if question_freq and question_freq.get("most_frequent_questions"):
                        st.write(f"最近7天共有 {question_freq.get('total_unique_questions', 0)} 个不同问题")
                        st.write("**最常见的问题:**")
                        
                        for question, count in question_freq["most_frequent_questions"]:
                            st.write(f"- {question} (出现 {count} 次)")
                    
                    # 导出报告按钮
                    st.markdown("---")
                    col_export1, col_export2 = st.columns(2)
                    
                    with col_export1:
                        if st.button("导出今日报告", key="export_daily"):
                            today = datetime.now().strftime("%Y%m%d")
                            excel_file = os.path.join("E:/sm-ai/log", f"qa_log_{today}.xlsx")
                            
                            if os.path.exists(excel_file):
                                with open(excel_file, "rb") as f:
                                    st.download_button(
                                        label="下载今日问答报告",
                                        data=f,
                                        file_name=f"qa_report_{today}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_daily_report"
                                    )
                            else:
                                st.warning("今日报告尚未生成")
                    
                    with col_export2:
                        if st.button("生成月度报告", key="export_monthly"):
                            current_year = datetime.now().year
                            current_month = datetime.now().month
                            
                            with st.spinner("正在生成月度报告..."):
                                success = st.session_state.qa_logger.export_monthly_report(
                                    year=current_year, month=current_month
                                )
                                
                                if success:
                                    report_file = os.path.join(
                                        "E:/sm-ai/log", 
                                        f"monthly_report_{current_year:04d}_{current_month:02d}.xlsx"
                                    )
                                    
                                    if os.path.exists(report_file):
                                        with open(report_file, "rb") as f:
                                            st.download_button(
                                                label="下载月度报告",
                                                data=f,
                                                file_name=f"qa_monthly_report_{current_year:04d}_{current_month:02d}.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key="download_monthly_report"
                                            )
                                    else:
                                        st.error("月度报告文件未找到")
                                else:
                                    st.error("生成月度报告失败")
                    
                    if st.button("关闭统计", key="close_stats"):
                        st.session_state.show_stats = False
                        st.rerun()
    
    # 清空按钮
    if st.session_state.qa_relevant_results:
        if st.button("清空所有参考", key="clear_all_refs", type="secondary"):
            st.session_state.qa_relevant_results = []
            st.session_state.qa_selected_refs = []
            st.session_state.qa_generated_answer = None
            st.session_state.show_stats = False
            st.rerun()
    
    # 上传知识文件
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
                
                # 添加到知识库
                success = st.session_state.kb.add_document(file_path)
                
                if success:
                    # 添加到数据库
                    st.session_state.db.add_knowledge_file(knowledge_file.name, file_path)
                    st.success("文件已成功添加到知识库")
                else:
                    st.error("添加文件到知识库失败")
                    
            except Exception as upload_error:
                error_msg = f"添加文件到知识库失败: {str(upload_error)}"
                st.error(error_msg)
                with st.expander("查看错误详情"):
                    st.text(traceback.format_exc())
    
    # 显示知识库文件列表
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
                        # 删除物理文件
                        if exists and os.path.exists(file_path):
                            os.remove(file_path)
                        
                        # 从数据库删除记录
                        if file_id and file_id != i:
                            st.session_state.db.delete_knowledge_file(file_id)
                        
                        # 重建索引
                        with st.spinner("正在更新知识库索引..."):
                            st.session_state.kb.rebuild_index()
                            
                        st.success(f"已删除文件: {filename}")
                        st.rerun()
                    except Exception as delete_error:
                        st.error(f"删除文件失败: {str(delete_error)}")
                        st.text(traceback.format_exc())
            
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
                            st.text(traceback.format_exc())

elif page == "知识库内容":
    st.title("知识库内容")
    
    # 添加知识库状态检查
    st.subheader("知识库状态检查")
    if st.button("手动同步知识库与数据库", key="sync_kb_db"):
        try:
            kb_files_dir = os.path.join(DATA_DIR, "knowledge_base", "files")
            if os.path.exists(kb_files_dir):
                files = os.listdir(kb_files_dir)
                for file in files:
                    file_path = os.path.join(kb_files_dir, file)
                    # 添加到数据库
                    st.session_state.db.add_knowledge_file(file, file_path)
                st.success(f"已同步 {len(files)} 个文件到数据库")
            else:
                st.warning("知识库文件目录不存在")
        except Exception as sync_error:
            st.error(f"同步失败: {str(sync_error)}")
            st.text(traceback.format_exc())
    
    try:
        # 尝试获取知识库文档
        kb_docs = st.session_state.kb.get_all_documents()
        
        if not kb_docs:
            st.info("知识库中暂无文件")
            
            # 尝试直接读取文件系统
            kb_files_dir = os.path.join(DATA_DIR, "knowledge_base", "files")
            if os.path.exists(kb_files_dir):
                files = os.listdir(kb_files_dir)
                if files:
                    st.warning("警告：文件系统中有知识库文件，但知识库索引中没有记录")
                    for i, filename in enumerate(files):
                        with st.expander(f"{filename} - (未在知识库索引中)"):
                            st.write(f"文件路径: {os.path.join(kb_files_dir, filename)}")
                            if st.button("添加到知识库索引", key=f"add_to_index_{filename}"):
                                try:
                                    file_path = os.path.join(kb_files_dir, filename)
                                    success = st.session_state.kb.add_document(file_path)
                                    if success:
                                        st.success("已添加到知识库索引！")
                                        st.rerun()
                                    else:
                                        st.error("添加到知识库索引失败")
                                except Exception as add_error:
                                    st.error(f"添加失败: {str(add_error)}")
                                    st.text(traceback.format_exc())
        else:
            st.write(f"知识库中有 {len(kb_docs)} 个文件")
            
            for i, doc in enumerate(kb_docs):
                file_exists = 'file_path' in doc and os.path.exists(doc['file_path'])
                with st.expander(f"{doc['filename']} - 上传于 {doc.get('uploaded_at', '未知时间')}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**文件路径:** `{doc.get('file_path', '未记录')}`")
                        st.write(f"**文件状态:** {'存在' if file_exists else '不存在'}")
                    
                    with col2:
                        # 删除按钮
                        delete_key = f"del_kb_{doc.get('id', i)}_{i}"
                        if st.button("删除此文档", key=delete_key):
                            try:
                                # 删除物理文件
                                if file_exists:
                                    os.remove(doc['file_path'])
                                
                                # 删除数据库记录
                                st.session_state.db.delete_knowledge_file(doc['id'])
                                
                                # 重建索引
                                with st.spinner("正在更新知识库索引..."):
                                    st.session_state.kb.rebuild_index()
                                
                                st.success("文档已删除，知识库索引已更新！")
                                st.rerun()
                            except Exception as delete_error:
                                st.error(f"删除失败: {str(delete_error)}")
                                st.text(traceback.format_exc())
                    
                    # 显示文件预览
                    if file_exists:
                        try:
                            preview = st.session_state.document_processor.get_file_preview(doc['file_path'])
                            st.subheader("文件预览")
                            st.text_area("", value=preview, height=300, 
                                        key=f"preview_{doc.get('id', i)}", disabled=True)
                        except Exception as preview_error:
                            st.error(f"预览失败: {str(preview_error)}")
                            st.text(traceback.format_exc())
                    else:
                        st.warning("文件不存在，无法预览")
                    
                    # 重建索引按钮
                    reindex_key = f"reindex_{doc.get('id', i)}_{i}"
                    if st.button("重建此文档索引", key=reindex_key):
                        with st.spinner("重建索引中..."):
                            try:
                                # 重新添加文件到知识库
                                if file_exists:
                                    st.session_state.kb.add_document(doc['file_path'])
                                    st.success("文档索引已重建！")
                                else:
                                    st.error("文件不存在，无法重建索引")
                            except Exception as reindex_error:
                                st.error(f"重建索引失败: {str(reindex_error)}")
                                st.text(traceback.format_exc())
    
    except Exception as main_error:
        st.error(f"加载知识库内容失败: {str(main_error)}")
        st.text(traceback.format_exc())

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