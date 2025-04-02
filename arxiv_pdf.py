import arxiv as arxiv
import csv
import pandas as pd
import logging
import os
import tarfile
import datetime as dt
import html_extractor as himage
import fitz
import asyncio
from tqdm.asyncio import tqdm as async_tqdm
import logging

QUERY = "(cat:cs.DC OR cat:cs.AR)"
# QUERY = "cat:cs.AI"
FILENAME = "test.csv"


def convert_to_lastfirst(authors):
    for i in range(len(authors)):
        name = authors[i]
        name = name.split(" ")
        first = name[0]
        last = name[-1]

        formatted_name = "au:" + last + "_" + first
        authors[i] = formatted_name
    return authors

def load_authors_csv():
    data = pd.read_csv("Researchers.csv")
    google_authors = data["Google"].tolist()
    meta_authors = data["Meta"].tolist()
    google_authors = convert_to_lastfirst(google_authors)
    meta_authors = convert_to_lastfirst(meta_authors)
    return [google_authors, meta_authors]

async def download_pdf_async(r, pdf_folder_path):
    """使用 arxiv 内置方法异步下载 PDF 文件，使用论文 ID 作为文件名"""
    # 使用论文 ID 作为文件名
    paper_id = r.get_short_id()
    pdf_path = os.path.join(pdf_folder_path, f"{paper_id}.pdf")
    
    try:
        # 使用 arxiv 内置的下载方法
        await asyncio.to_thread(r.download_pdf, dirpath=pdf_folder_path, filename=f"{paper_id}.pdf")
        return pdf_path
    except Exception as e:
        logging.error(f"下载 PDF 失败 {paper_id}: {str(e)}")
        return None

async def extract_pdf_content_async(pdf_path):
    """异步从PDF中提取文本内容"""
    return await asyncio.to_thread(extract_pdf_content, pdf_path)

def extract_pdf_content(pdf_path):
    """从PDF中提取文本内容 - 只提取第一页"""
    try:
        with fitz.open(pdf_path) as pdf_doc:
            if len(pdf_doc) > 0:
                return pdf_doc[0].get_text("text")
            else:
                logging.warning(f"PDF文件 {pdf_path} 没有页面")
                return ""
    except Exception as e:
        logging.error(f"PDF内容提取失败 {pdf_path}: {str(e)}")
        return ""

async def download_and_process_pdf(r, pdf_folder_path):
    """异步下载和处理PDF文件"""
    pdf_path = await download_pdf_async(r, pdf_folder_path)
    paper_content = ""
    
    if pdf_path:
        try:
            # 异步读取PDF内容
            paper_content = await extract_pdf_content_async(pdf_path)
            
            # 删除PDF文件
            await asyncio.to_thread(os.remove, pdf_path)
            
        except Exception as e:
            logging.error(f"处理PDF失败 {r.title}: {str(e)}")
    
    return paper_content

def get_arxiv_results(query, author_filter=True, start_date=None, end_date=None, max_results=350):
    """
    构建并执行arxiv搜索查询，返回搜索结果列表
    
    参数:
        query: 基础查询字符串
        author_filter: 是否应用作者过滤
        start_date: 开始日期
        end_date: 结束日期
        max_results: 最大结果数量
        
    返回:
        arxiv搜索结果列表
    """
    if author_filter:
        key_authors = load_authors_csv()
        final_query = query + " AND ("
        for author in key_authors[0]: #testing google for now
            final_query = final_query + author + " OR "
        final_query = final_query[:-4] + ")" #Removing final " OR "
    else:
        final_query = query
        
    if start_date == None or end_date == None:
        start_date, end_date = get_last_day()
    else:
        start_date = start_date.strftime("%Y%m%d") + "1200"
        end_date = end_date.strftime("%Y%m%d") + "1200"
    
    # print(start_date)
    # print(end_date)
    # print(final_query)
    
    # 使用同步方式获取论文列表
    client = arxiv.Client()
    search = arxiv.Search(
        query = f"submittedDate:[{start_date} TO {end_date}] AND {final_query}",
        sort_by = arxiv.SortCriterion.LastUpdatedDate,
        sort_order = arxiv.SortOrder.Descending,
        max_results = max_results
    )
    return list(client.results(search))

async def fetch_papers_async(pdf_folder_path, csv_filename=FILENAME, query=QUERY, author_filter=True, start_date=None, end_date=None):
    """
    异步抓取论文并下载PDF文件
    :param pdf_folder_path: PDF文件保存路径
    :param csv_filename: CSV文件保存路径
    :return: 下载的论文数量
    """
    # 获取arxiv搜索结果
    results = get_arxiv_results(query, author_filter, start_date, end_date)
    
    # 确保PDF保存目录存在
    os.makedirs(pdf_folder_path, exist_ok=True)
    
    # 写入CSV文件
    header = ["Paper_ID", "Title", "Authors", "Abstract", "Primary Category", "Categories", "URL", "Date", "Content"]
    downloaded_count = 0
    
    # 异步处理所有论文
    tasks = []
    for r in results:
        tasks.append(download_and_process_pdf(r, pdf_folder_path))
    
    # 使用异步进度条
    paper_contents = await async_tqdm.gather(*tasks, desc="异步处理论文", unit="篇")
    
    # 写入CSV
    await asyncio.to_thread(write_csv_data, csv_filename, header, results, paper_contents)
    
    return len([content for content in paper_contents if content])  # 返回成功下载的数量

def write_csv_data(filename, header, results, paper_contents):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        
        for i, r in enumerate(results):
            authors_strings = []
            for author in r.authors:
                authors_strings.append(str(author))
            
            # 获取论文ID
            paper_id = r.get_short_id()
            
            writer.writerow({
                "Paper_ID": paper_id,
                "Title": r.title,
                "Authors": authors_strings,
                "Abstract": r.summary,
                "Primary Category": r.primary_category,
                "Categories": r.categories,
                "URL": r,
                "Date": r.published,
                "Content": paper_contents[i]
            })

def fetch_papers(pdf_folder_path, csv_filename=FILENAME, query=QUERY, author_filter=True, start_date=None, end_date=None):
    """
    同步接口，调用异步函数
    """
    result = asyncio.run(fetch_papers_async(pdf_folder_path, csv_filename, query, author_filter, start_date, end_date))
    if result == 0:
        print("没有找到符合条件的论文")
    else:
        print(f"成功下载并处理了 {result} 篇论文")
    return result

def get_last_day():
    today = dt.datetime.today()
    yesterday = today - dt.timedelta(days=2)

    end_time = today.strftime("%Y%m%d") + "1200"
    start_time = yesterday.strftime("%Y%m%d") + "1200"
    return start_time, end_time

def unzip_archive():
    f = os.listdir('./temp')[0]
    f = os.path.join("./temp", f)
    if f.endswith("tar.gz"):
        tar = tarfile.open(f, "r:gz")
        tar.extractall(path = "./temp")
        tar.close()


# ... existing code ...
# def test_arxiv_results(paper_id):
#     client = arxiv.Client()
#     search = arxiv.Search(
#         id_list=paper_id,  # 例如: "2303.12712"
#         max_results=1
#     )
#     return list(client.results(search))
# ... existing code ...
def main():
    # logging.basicConfig(level=logging.DEBUG)
    # 使用支持时区的方法替代 utcnow()
    # today = dt.datetime.now(dt.timezone.utc).date()
    today = dt.datetime.today()
    end_date = today
    start_date = today - dt.timedelta(days=2)
    #logging.basicConfig(level=logging.DEBUG)
    fetch_papers("pdf_folder", author_filter=False, start_date=start_date, end_date=end_date)

    # a = test_arxiv_results(["2504.00520"])
    # print(a)

if __name__ == "__main__":
    main()