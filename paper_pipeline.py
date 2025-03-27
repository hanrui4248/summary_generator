import os
import datetime as dt
import time
import schedule
import arxiv_pdf
import paper_affiliation_classifier
import affiliation_analyzer
from paper_assistant import PaperAssistant
from orgs import orgs
from tools import clean_folder

def run_pipeline(csv_filename="papers.csv",
                pdf_folder="pdf_folder",
                query="cat:cs.AI", 
                author_filter=False,
                days_back=1,
                target_orgs=None):
    """
    运行完整的论文处理流水线
    
    参数:
        csv_filename: CSV文件名（保存在当前目录）
        pdf_folder: PDF文件保存文件夹
        query: arXiv查询字符串
        author_filter: 是否使用作者过滤
        days_back: 往前查询的天数
        target_orgs: 目标机构列表
        
    返回:
        下载的论文数量
    """
    try:
        # 清空pdf_folder和images文件夹
        clean_folder("pdf_folder")
        clean_folder("default_images")
        
        # 设置默认目标机构
        if target_orgs is None:
            target_orgs = orgs
        
        # 1. 设置日期范围
        end_date = dt.datetime.today()
        start_date = end_date - dt.timedelta(days=days_back)
        print(f"使用日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        
        # 2. 使用arxiv_pdf模块获取论文列表
        print("第1步: 从arXiv获取论文列表...")
        papers_count = arxiv_pdf.fetch_papers(
            pdf_folder, 
            csv_filename=csv_filename,
            query=query,
            author_filter=author_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        if papers_count == 0:
            print("没有找到符合条件的论文，流程终止")
            return 0
        
        print(f"成功获取{papers_count}篇论文信息")
        
        # 3. 使用paper_affiliation_classifier模块分类论文机构
        print("第2步: 模型分类论文机构...")
        classifier = paper_affiliation_classifier.PaperAffiliationClassifier()
        classifier.process_csv(csv_filename)
        print("论文机构分类完成")
        
        # 4. 使用affiliation_analyzer模块分析机构
        print("第3步: 模型筛选目标机构论文...")
        analyzer = affiliation_analyzer.AffiliationAnalyzer()
        indices_result = analyzer.process_csv(csv_filename, target_orgs)
        print(f"机构分析完成，找到的索引: {indices_result}")
         # 第四步：下载论文并生成摘要
        print("第4步: 生成图文摘要...")
        assistant = PaperAssistant(output_dir=pdf_folder, image_dir="default_images")
        markdown_content = assistant.process_and_download(csv_filename, indices_result)
        
        # 将内容写入markdown文件
        markdown_filename = "每日默认精选论文.md"
        with open(markdown_filename, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        print(f"已将论文摘要保存到 {markdown_filename}")
        
        # 6. 输出结果摘要
        print("=== 论文处理流水线完成 ===")
        print(f"- 获取论文数量: {papers_count}")
        
        return papers_count
        
    except Exception as e:
        print(f"论文处理流水线运行失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0

def run_scheduled_pipeline():
    """运行计划任务的包装函数，记录运行时间"""
    # 每次运行时清空日志文件
    with open("pipeline.log", "w") as log_file:
        current_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{current_time}] 开始执行计划任务...\n")
    
    print(f"\n[{current_time}] 开始执行计划任务...")
    run_pipeline()
    
    # 记录完成时间
    with open("pipeline.log", "a") as log_file:
        current_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{current_time}] 计划任务执行完成\n")
    
    print(f"[{current_time}] 计划任务执行完成")

def schedule_pipeline():
    """设置定时任务，每12小时运行一次pipeline"""
    # 创建锁文件，记录PID
    with open("paper_pipeline.lock", "w") as f:
        f.write(str(os.getpid()))
    
    try:
        # 立即运行一次
        run_scheduled_pipeline()
        
        # 设置每12小时运行一次
        schedule.every(12).hours.do(run_scheduled_pipeline)
        
        print("已设置每12小时自动运行一次论文处理流水线")
        print("按Ctrl+C可以停止自动运行")
        
        # 持续运行，等待计划任务
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次是否有待运行的任务
        except KeyboardInterrupt:
            print("自动运行已停止")
    finally:
        # 删除锁文件
        if os.path.exists("paper_pipeline.lock"):
            os.remove("paper_pipeline.lock")

def main():
    """主函数"""
    # 直接调用schedule_pipeline函数
    schedule_pipeline()

if __name__ == "__main__":
    main() 