import arxiv as arxiv
import csv
import pandas as pd
import logging
import os
import tarfile
import datetime as dt
import html_image_extractor as himage


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
    
    start_date, end_date = get_last_day()
    client = arxiv.Client()
    search = arxiv.Search(
        query =  f"submittedDate:[{start_date} TO {end_date}] AND {final_query}",
        sort_by = arxiv.SortCriterion.LastUpdatedDate,
        sort_order = arxiv.SortOrder.Descending,
        max_results = 10 
    )
    results = client.results(search)
    
    # 确保PDF保存目录存在
    os.makedirs(pdf_folder_path, exist_ok=True)
    
    # 写入CSV文件
    header = ["Title", "Authors", "Abstract", "Primary Category", "Categories", "URL", "Date"]
    downloaded_count = 0
    write_type = "a" if os.path.isfile(csv_filename) else "w"
    with open(csv_filename, write_type, newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader() if write_type == "w" else None
        for r in results:
            authors_strings = []
            for author in r.authors:
                authors_strings.append(str(author))
            writer.writerow({
                "Title": r.title,
                "Authors": authors_strings,
                "Abstract": r.summary,
                "Primary Category": r.primary_category,
                "Categories": r.categories,
                "URL": r,
                "Date": r.published
            })
            # 下载PDF文件
            short_id = r.get_short_id()
            #try:
                #r.download_pdf(dirpath = pdf_folder_path, filename=str(r.title) + ".pdf")
            downloaded_count += 1
            himage.get_image(f"https://arxiv.org/html/{short_id}",short_id, f"image{downloaded_count}")
            #except Exception as e:
             #   logging.error(f"下载PDF失败 {r.title}: {str(e)}")
    
    return downloaded_count

def get_last_day():
    today = dt.datetime.today()
    yesterday = today - dt.timedelta(10)

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

def main():
    #logging.basicConfig(level=logging.DEBUG)
    fetch_papers("pdf_folder")

if __name__ == "__main__":
    main()