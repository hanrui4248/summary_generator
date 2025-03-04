import streamlit as st
import fitz
from openai import OpenAI
import argparse
import os
from datetime import datetime, timedelta
import arxiv_pdf
import time
import pandas as pd

# 在最开始添加页面配置
st.set_page_config(
    page_title="论文快报生成器",
    layout="wide",  # 使用宽屏布局
    initial_sidebar_state="collapsed"  # 默认收起侧边栏
)

parser = argparse.ArgumentParser(description="PDF 摘要生成器")
parser.add_argument("--api_key", type=str, required=True, help="API Key")
args = parser.parse_args()

client_openrouter = OpenAI(
    api_key=args.api_key,
    base_url="https://openrouter.ai/api/v1"
)

# 可用模型列表
MODEL_OPTIONS = [
    "google/gemini-2.0-flash-lite-001", 
    "google/gemini-2.0-flash-thinking-exp:free", 
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free",
]

def extract_text_from_pdf(pdf_path):
    """从 PDF 文件中提取文本"""
    text = ""
    with fitz.open(pdf_path) as pdf_doc:
        for page in pdf_doc:
            text += page.get_text("text") + "\n"
    return text

def summarize_text(text, model_name):
    """使用 OpenAI API 生成摘要"""
    try:
        # # 限制输入文本长度，避免超出模型限制
        # max_length = 14000  # 根据实际模型限制调整
        # text = text[:max_length]
        
        completion = client_openrouter.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "请为以下内容生成简洁明了的中文摘要，请你的摘要中包含以下几个关键点\n 1.整体内容, 2.主要贡献 3.实现方法 4.实验与评估结果\n 我只想让你输出摘要内容，不要回复我的任何话。"},
                {"role": "user", "content": text}
            ],
            timeout=60  # 设置超时时间
        )
        
        if completion and completion.choices and len(completion.choices) > 0:
            return completion.choices[0].message.content
        else:
            raise Exception("API 返回结果为空")
            
    except Exception as e:
        raise Exception(f"生成摘要时出错: {str(e)}")

def generate_daily_report_from_df(df, model_name):
    """根据DataFrame中的论文生成每日快报"""
    summaries = []
    errors = []
    
    # 获取images文件夹中的图片列表
    images_folder = "images"
    image_files = []
    if os.path.exists(images_folder):
        image_files = sorted([f for f in os.listdir(images_folder) 
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
    
    # 使用enumerate来获取连续的索引
    for paper_idx, (_, row) in enumerate(df.iterrows()):
        try:
            # 显示当前处理的论文标题
            status_text = st.empty()
            status_text.text(f"正在处理: {row['Title']}")
            
            # 使用论文的摘要生成中文总结
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    summary = summarize_text(row['Abstract'], model_name)
                    if summary:
                        # 使用paper_idx代替index进行图片匹配
                        image_path = None
                        if paper_idx < len(image_files):
                            image_path = os.path.join(images_folder, image_files[paper_idx])
                        summaries.append((row['Title'], summary, image_path))
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        error_msg = f"处理论文 {row['Title']} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                        st.error(error_msg)
                        errors.append((row['Title'], str(e)))
                    time.sleep(2)
                    
        except Exception as e:
            error_msg = f"处理论文 {row['Title']} 时出错: {str(e)}"
            st.error(error_msg)
            errors.append((row['Title'], str(e)))
    
    # 清除状态文本
    if 'status_text' in locals():
        status_text.empty()
    
    # 生成markdown格式的报告
    report = f"# 论文快报_{df['Date'].dt.date.iloc[0]}\n\n"
    
    if summaries:
        for i, (title, summary, image_path) in enumerate(summaries, 1):
            report += f"## {i}. {title}\n\n{summary}\n\n"
            # 如果有图片，添加图片链接
            if image_path and os.path.exists(image_path):
                relative_path = image_path.replace('images/', './images/')
                report += f"![论文图片]({relative_path})\n\n"
            report += "---\n\n"
    
    # 添加错误报告部分
    if errors:
        report += "\n## 处理失败的论文\n\n"
        for title, error in errors:
            report += f"- {title}: {error}\n"
    
    return report, summaries  # 返回报告文本和摘要列表

# Streamlit 界面
st.title("论文快报生成器")

# 添加一个新的选项卡
tab1, tab2 = st.tabs(["论文总结", "论文抓取"])

with tab1:
    # 使用固定的文件夹路径
    folder_path = "pdf_folder"
    model_name = st.selectbox("选择模型", MODEL_OPTIONS)

    # 添加论文列表显示
    csv_filename = "papers.csv"
    if os.path.exists(csv_filename):
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_filename)
            
            # 将Date列转换为datetime类型
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 获取所有可用的日期
            available_dates = df['Date'].dt.date.unique()
            
            # 添加日期选择器
            selected_date = st.selectbox(
                "选择日期",
                options=available_dates,
                format_func=lambda x: x.strftime('%Y-%m-%d')
            )
            
            # 根据选择的日期筛选数据
            filtered_df = df[df['Date'].dt.date == selected_date]
            
            # 处理Abstract列中的换行符
            filtered_df['Abstract'] = filtered_df['Abstract'].str.replace('\n', ' ')
            
            # 使用st.dataframe显示数据，设置列宽和高度
            st.dataframe(
                filtered_df[['Title', 'Authors', 'Abstract', 'Date', 'URL']],
                column_config={
                    "Title": st.column_config.TextColumn(
                        "Title",
                        width="medium"
                    ),
                    "Authors": st.column_config.TextColumn(
                        "Authors",
                        width="small"
                    ),
                    "Abstract": st.column_config.TextColumn(
                        "Abstract",
                        width="large"
                    ),
                    "Date": st.column_config.DateColumn(
                        "Date",
                        width="small"
                    ),
                    "URL": st.column_config.LinkColumn(
                        "URL",
                        width="small"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"读取CSV文件时发生错误: {str(e)}")

    # 修改生成按钮部分
    if st.button("生成论文快报"):
        if filtered_df.empty:
            st.error("所选日期没有论文数据")
        else:
            with st.spinner("正在生成论文快报..."):
                report, summaries = generate_daily_report_from_df(filtered_df, model_name)
                
                # 在UI中显示每篇论文的摘要和图片
                for i, (title, summary, image_path) in enumerate(summaries, 1):
                    st.markdown(f"## {i}. {title}")
                    
                    # 如果有图片，显示图片（放在摘要上方，并设置固定宽度）
                    if image_path and os.path.exists(image_path):
                        # 创建三列，图片显示在中间列
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(image_path, 
                                    caption=f"论文 {i} 的图片",
                                    width=400)  # 设置固定宽度为400像素
                    
                    # 显示摘要
                    st.markdown(summary)
                    st.markdown("---")
                
                # 准备下载文件
                report_filename = f"论文快报_{selected_date}.md"
                
                # 创建一个临时目录来存放报告和图片
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 复制图片文件夹到临时目录
                    if os.path.exists("images"):
                        shutil.copytree("images", os.path.join(temp_dir, "images"))
                    
                    # 将报告写入临时目录
                    report_path = os.path.join(temp_dir, report_filename)
                    with open(report_path, "w", encoding="utf-8") as f:
                        f.write(report)
                    
                    # 将整个临时目录打包成zip文件
                    zip_filename = f"论文快报_{selected_date}.zip"
                    shutil.make_archive(
                        os.path.join(os.getcwd(), zip_filename.replace('.zip', '')),
                        'zip',
                        temp_dir
                    )
                
                # 提供zip文件下载
                with open(zip_filename, "rb") as f:
                    st.download_button(
                        label="下载论文快报(包含图片)",
                        data=f,
                        file_name=zip_filename,
                        mime="application/zip"
                    )

with tab2:
    st.header("arxiv论文抓取")
    
    # 使用固定的CSV文件名
    csv_filename = "papers.csv"
    
    if st.button("开始抓取论文"):
        with st.spinner("正在从arxiv抓取论文..."):
            try:
                downloaded_count = arxiv_pdf.fetch_papers(folder_path, csv_filename, query= "cat:cs.AI", author_filter=False, start_date=datetime.today()-timedelta(1), end_date=datetime.today())
                st.success(f"成功下载 {downloaded_count} 篇论文到 {folder_path} 文件夹")
                st.info(f"论文信息已保存到 {csv_filename}")
            except Exception as e:
                st.error(f"抓取论文时发生错误: {str(e)}")
