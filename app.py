import streamlit as st
import os
import base64
from paper_pipeline import run_pipeline
from paper_assistant import PaperAssistant
import affiliation_analyzer
import re
import pandas as pd

def get_download_link(content, filename, text):
    """生成下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:text/markdown;base64,{b64}" download="{filename}">{text}</a>'
    return href

def display_image(image_path, base_dir):
    """显示图片，支持多种路径尝试"""
    # 如果是URL，直接显示
    if image_path.startswith(('http://', 'https://')):
        try:
            st.image(image_path)
            return True
        except Exception as e:
            st.warning(f"无法加载图片URL: {image_path}，错误: {str(e)}")
            return False
    
    # 如果是本地路径，尝试多种路径组合
    possible_paths = [
        image_path,  # 原始路径
        os.path.join(base_dir, image_path),  # 相对于基础目录
        os.path.abspath(image_path),  # 绝对路径
        os.path.join(os.getcwd(), image_path)  # 相对于当前工作目录
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                st.image(path)
                return True
            except Exception as e:
                st.warning(f"图片存在但无法显示: {path}，错误: {str(e)}")
                break
    
    # st.warning(f"无法找到图片: {image_path}")
    return False

def process_markdown_line(line, base_dir):
    """处理普通的Markdown行，显示文本和图片"""
    # 查找行中的图片标记
    img_pattern = r'!\[(.*?)\]\((.*?)\)'
    img_matches = re.findall(img_pattern, line)
    
    if img_matches:
        # 有图片，分割文本和图片
        parts = re.split(img_pattern, line)
        for i in range(len(parts)):
            if i % 3 == 0:  # 文本部分
                if parts[i].strip():
                    st.markdown(parts[i])
            elif i % 3 == 2:  # 图片路径
                display_image(parts[i], base_dir)
    else:
        # 没有图片，直接显示文本
        st.markdown(line)

def process_markdown_table(table_lines, base_dir):
    """处理Markdown表格，正确显示表格结构和图片"""
    # 解析表格结构
    rows = []
    for line in table_lines:
        # 跳过分隔行 (| --- | --- |)
        if re.match(r'\|\s*[-:]+\s*\|', line):
            continue
        
        # 分割单元格
        cells = line.split('|')[1:-1]  # 去掉首尾的 |
        processed_cells = []
        
        for cell in cells:
            # 检查单元格是否包含图片
            img_match = re.search(r'!\[(.*?)\]\((.*?)\)', cell)
            if img_match:
                # 这是一个包含图片的单元格，使用图片路径作为占位符
                img_path = img_match.group(2)
                processed_cells.append(img_path)
            else:
                # 普通文本单元格
                processed_cells.append(cell.strip())
        
        rows.append(processed_cells)
    
    # 创建表格
    if rows:
        # 创建一个空的DataFrame
        df = pd.DataFrame(rows)
        
        # 使用st.columns创建表格布局
        cols = st.columns(len(rows[0]))
        
        # 填充表格内容
        for col_idx, col in enumerate(cols):
            for row_idx in range(len(rows)):
                cell_content = rows[row_idx][col_idx]
                
                # 检查是否是图片路径
                if re.match(r'.*\.(png|jpg|jpeg|gif|bmp|webp)', cell_content, re.IGNORECASE):
                    with col:
                        display_image(cell_content, base_dir)
                else:
                    with col:
                        st.markdown(cell_content)

def display_markdown_with_images(markdown_content, base_dir="."):
    """解析Markdown内容并使用Streamlit组件显示，包括图片和表格"""
    # 分割内容为行
    lines = markdown_content.split('\n')
    i = 0
    while i < len(lines):
        # 检查是否是表格开始
        if lines[i].strip().startswith('|') and '|' in lines[i][1:]:
            # 收集表格行
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            # 处理表格
            process_markdown_table(table_lines, base_dir)
        else:
            # 处理普通文本行
            if lines[i].strip():
                process_markdown_line(lines[i], base_dir)
            i += 1

def main():
    st.set_page_config(page_title="每日arXiv论文快报", page_icon="📚")
    
    st.title("AI4Paper")
    st.write("点击下方按钮生成今日精选论文快报")
    
    # 添加一些配置选项
    with st.expander("高级配置"):
        days_back = st.slider("查询过去几天的论文", 1, 7, 3)
        
        # 目标机构多选
        default_orgs = [
            "Google", "Meta", "Microsoft", "OpenAI", 
            "Anthropic", "DeepMind", "Stanford", 
            "Alibaba", "Huawei", "Baidu",
        ]
        target_orgs = st.multiselect(
            "目标机构", 
            options=default_orgs + ["其他"],
            default=default_orgs
        )
        
        # 如果选择了"其他"，允许用户输入自定义机构
        if "其他" in target_orgs:
            target_orgs.remove("其他")
            custom_org = st.text_input("输入自定义机构名称")
            if custom_org:
                target_orgs.append(custom_org)
    
    # 生成按钮
    if st.button("生成每日论文快报", type="primary"):
        with st.spinner("正在获取和处理论文，请稍候..."):
            # 创建进度条
            progress_bar = st.progress(0)
            
            # 第一步：运行pipeline获取论文
            st.info("步骤1/3: 从arXiv获取论文...")
            progress_bar.progress(10)
            
            csv_filename = "papers.csv"
            pdf_folder = "pdf_folder"
            
            # 使用默认的查询字符串 "cat:cs.AI"
            query = "cat:cs.AI"
            
            papers_count = run_pipeline(
                csv_filename=csv_filename,
                pdf_folder=pdf_folder,
                query=query,
                days_back=days_back,
                target_orgs=target_orgs
            )
            
            if papers_count == 0:
                st.error("没有找到符合条件的论文，请调整查询参数后重试。")
                return
            
            progress_bar.progress(40)
            
            # 第二步：获取目标机构的论文索引
            st.info("步骤2/3: 模型筛选目标机构论文...")
            analyzer = affiliation_analyzer.AffiliationAnalyzer()
            indices_result = analyzer.process_csv(csv_filename, target_orgs)
            
            progress_bar.progress(70)
            
            # 第三步：下载论文并生成摘要
            st.info("步骤3/3: 生成论文摘要...")
            assistant = PaperAssistant(output_dir=pdf_folder)
            markdown_content = assistant.process_and_download(csv_filename, indices_result)
            
            
            progress_bar.progress(100)
            
            # 显示结果
            st.success(f"成功生成论文快报")
            
            # 使用新的display_markdown_with_images函数显示markdown内容
            display_markdown_with_images(markdown_content, pdf_folder)
            
            # 提供下载链接
            st.markdown(
                get_download_link(markdown_content, "每日arxiv精选论文.md", "点击下载Markdown文件"),
                unsafe_allow_html=True
            )

if __name__ == "__main__":
    main() 