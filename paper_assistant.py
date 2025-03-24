import pandas as pd
import os
import json
import logging
import arxiv
from tqdm import tqdm
# 使用fitz库提取PDF文本
from openai import OpenAI
import fitz  # PyMuPDF
# 导入html_extractor模块
from html_extractor import get_image

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class PaperAssistant:
    """
    论文助手，用于根据筛选的索引下载相应论文，并生成每日精选论文摘要
    """
    def __init__(self, output_dir="pdf_folder", image_dir="images"):
        self.output_dir = output_dir
        self.image_dir = image_dir
        # 创建输出目录（如果不存在）
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # 创建图片目录（如果不存在）
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        
        # 设置OpenAI API密钥
        
        self.api_key = os.environ["OPENAI_API_KEY"]
        self.client = OpenAI(api_key=self.api_key)
        
        # 系统提示
        self.summary_system_prompt = """
        请为以下内容生成简洁明了的中文摘要，严格按照以下格式输出，不要添加额外的文本，每个小节都是完整的一段，不要使用列表, 且机构要使用中文名称：
        机构：...
        整体内容：...
        主要贡献：...
        实现方法：...
        实验与评估结果：...
        """

    def extract_papers_by_indices(self, csv_path, indices_str):
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_path)
            logging.info(f"成功读取CSV文件，共{len(df)}条记录")
            
            # 解析索引字符串
            try:
                indices = json.loads(indices_str.replace("'", "\""))
                if not isinstance(indices, list):
                    raise ValueError("索引必须是列表格式")
            except json.JSONDecodeError:
                # 尝试使用eval解析（不推荐，但作为备选）
                indices = eval(indices_str)
            
            # 提取指定索引的行，现在包括URL字段
            extracted_df = df.iloc[indices][["Title", "Affiliation", "Paper_ID", "URL"]]
            
            return extracted_df
        
        except Exception as e:
            logging.error(f"提取论文信息失败: {str(e)}")
            raise
    

    def download_and_summarize(self, papers_df):
        if papers_df.empty:
            logging.warning("没有论文需要下载")
            return None
        
        downloaded_count = 0
        client = arxiv.Client()
        
        # 创建markdown内容
        markdown_content = "# 每日arxiv精选论文\n\n"
        markdown_content += f"生成日期: {pd.Timestamp.now().strftime('%Y-%m-%d')}\n\n"
        
        for _, paper in tqdm(papers_df.iterrows(), total=len(papers_df), desc="下载论文"):
            try:
                paper_id = paper["Paper_ID"]
                title = paper["Title"]
                affiliation = paper["Affiliation"]
                url = paper["URL"]
                
                filename = f"{title}.pdf"
                filepath = os.path.join(self.output_dir, filename)
                
                # 检查文件是否已存在
                if os.path.exists(filepath):
                    logging.info(f"论文已存在，跳过下载: {filename}")
                    downloaded_count += 1
                else:
                    # 下载论文
                    logging.info(f"正在下载论文: {paper_id} - {title}")
                    arxiv_paper = next(client.results(arxiv.Search(id_list=[paper_id])))
                    arxiv_paper.download_pdf(filename=filepath)
                    logging.info(f"成功下载论文: {filename}")
                    downloaded_count += 1
                
                # 生成论文摘要
                logging.info(f"正在生成论文摘要: {title}")
                summary = self.generate_summary(filepath, title, affiliation)
                
                # 将摘要添加到markdown内容
                paper_content = f"## [{title}]({url})\n\n"
                
                # 获取论文图片
                logging.info(f"正在获取论文图片: {paper_id}")
                # 从paper_id中提取short_id (例如: 2503.16203v1)
                img_count = get_image(paper_id)
                
                # 添加图片到markdown
                if img_count > 0:
                    # paper_content += "### 论文图片\n\n"
                    if img_count == 2:  # 如果有两张图片，将它们放在同一行
                        # 使用Markdown表格语法实现并排显示
                        img_paths = []
                        for i in range(img_count):
                            for suffix in ["png", "jpg"]:
                                img_path = f"{self.image_dir}/{paper_id}_{i}.{suffix}"
                                if os.path.exists(img_path):
                                    img_paths.append(img_path)
                                    break
                        
                        if len(img_paths) == 2:
                            paper_content += f"| ![图片1]({img_paths[0]}) | ![图片2]({img_paths[1]}) |\n"
                            paper_content += "| --- | --- |\n\n"
                    else:  # 其他情况，每张图片单独一行
                        for i in range(img_count):
                            for suffix in ["png", "jpg"]:
                                img_path = f"{self.image_dir}/{paper_id}_{i}.{suffix}"
                                if os.path.exists(img_path):
                                    paper_content += f"![图片{i+1}]({img_path})\n\n"
                                    break
                
                paper_content += f"{summary}\n\n"
                paper_content += "---\n\n"
                
                markdown_content += paper_content
                
            except Exception as e:
                logging.error(f"处理论文失败 {paper_id}: {str(e)}")
        
        logging.info(f"已成功下载 {downloaded_count}/{len(papers_df)} 篇论文")
        
        return markdown_content
    
    def generate_summary(self, pdf_path, title, affiliation):
        """使用OpenAI模型生成论文摘要"""
        try:
            # 提取PDF文本
            text = ""
            with fitz.open(pdf_path) as pdf_doc:
                # 只读取前5页用于摘要
                for page_num in range(min(5, len(pdf_doc))):
                    page = pdf_doc[page_num]
                    text += page.get_text("text") + "\n"
            
            # 限制文本长度以适应API限制
            # text = text[:10000]  
            
            # 调用OpenAI API生成摘要，将机构信息与论文内容一起提供
            response = self.client.chat.completions.create(
                model="gpt-4o",  # 或者您选择的其他模型
                messages=[
                    {"role": "system", "content": self.summary_system_prompt},
                    {"role": "user", "content": f"机构: {affiliation}\n\n论文内容: {text}"}
                ],
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            logging.info(f"成功生成论文摘要: {title}")
            return summary
            
        except Exception as e:
            logging.error(f"生成摘要失败: {str(e)}")
            return "无法生成摘要，请查看原文。"
    
    def process_and_download(self, csv_path, indices_str):
        try:
            # 提取论文信息
            papers_df = self.extract_papers_by_indices(csv_path, indices_str)
            
            # 下载论文并获取markdown内容
            markdown_content = self.download_and_summarize(papers_df)
            
            # 只返回markdown内容，不需要返回papers_df
            return markdown_content
        
        except Exception as e:
            logging.error(f"处理和下载论文失败: {str(e)}")
            raise

def main():
    # 从affiliation_analyzer.py获取的索引结果
    indices_result = "[0, 5, 10, 15]"  # 示例索引，请替换为实际结果
    
       
    downloader = PaperAssistant()
    markdown_content = downloader.process_and_download("test.csv", indices_result)
    
    # 将内容写入markdown文件
    with open("每日arxiv精选论文.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print("下载完成!")

if __name__ == "__main__":
    main() 