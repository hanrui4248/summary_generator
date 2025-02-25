import arxiv as arxiv
import csv
import pandas as pd
import logging
import os


QUERY = "cat:cs.AI"
SEARCHDATE = "202502011200"
SEARCHDATE2 = "202502081200"
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


def fetch_papers(pdf_folder_path, csv_filename=FILENAME):
    """
    抓取论文并下载PDF文件
    :param pdf_folder_path: PDF文件保存路径
    :param csv_filename: CSV文件保存路径
    :return: 下载的论文数量
    """
    key_authors = load_authors_csv()
    final_query = QUERY + " AND ("
    for author in key_authors[0]: #testing google for now
        final_query = final_query + author + " OR "
    final_query = final_query[:-4] + ")" #Removing final " OR "
    
    client = arxiv.Client()
    search = arxiv.Search(
        query =  "submittedDate:[202501081200 TO 202502151200] AND " + final_query,
        sort_by = arxiv.SortCriterion.LastUpdatedDate,
        sort_order = arxiv.SortOrder.Descending,
        max_results = 10 
    )
    results = client.results(search)
    
    # 确保PDF保存目录存在
    os.makedirs(pdf_folder_path, exist_ok=True)
    
    # 写入CSV文件
    header = ["Title", "Authors", "Abstract", "Primary Category", "Categories", "URL"]
    downloaded_count = 0
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "Title": r.title,
                "Authors": r.authors,
                "Abstract": r.summary,
                "Primary Category": r.primary_category,
                "Categories": r.categories,
                "URL": r
            })
            # 下载PDF文件
            try:
                r.download_pdf(dirpath = pdf_folder_path, filename=str(r.title) + ".pdf")
                downloaded_count += 1
            except Exception as e:
                logging.error(f"下载PDF失败 {r.title}: {str(e)}")
    
    return downloaded_count

def main():
    logging.basicConfig(level=logging.DEBUG)
    fetch_papers("pdf_folder")

if __name__ == "__main__":
    main()