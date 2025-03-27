import os
import shutil
import psutil
import subprocess
import sys
import time

def clean_folder(folder_path):
    """
    清空指定文件夹中的所有文件和子文件夹
    如果文件夹不存在，则创建它
    
    参数:
        folder_path: 要清空的文件夹路径
    """
    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    else:
        os.makedirs(folder_path)

def is_pipeline_running():
    """检查paper_pipeline.py是否已经在运行"""
    # 首先检查锁文件
    if os.path.exists("paper_pipeline.lock"):
        try:
            with open("paper_pipeline.lock", "r") as f:
                pid = int(f.read().strip())
            # 验证PID是否存在
            if psutil.pid_exists(pid):
                return True
            else:
                # PID不存在，可能是异常退出，删除锁文件
                os.remove("paper_pipeline.lock")
        except (ValueError, IOError):
            # 锁文件格式错误或无法读取，删除它
            if os.path.exists("paper_pipeline.lock"):
                os.remove("paper_pipeline.lock")
    
    # 然后使用进程检测作为备选
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # 检查命令行中是否包含paper_pipeline.py
            if proc.info['cmdline'] and 'python' in proc.info['cmdline'][0].lower():
                cmdline = ' '.join(proc.info['cmdline'])
                if 'paper_pipeline.py' in cmdline:
                    # 找到进程，创建锁文件
                    with open("paper_pipeline.lock", "w") as f:
                        f.write(str(proc.info['pid']))
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_pipeline_background(st):
    """启动paper_pipeline.py作为完全独立的后台进程，确保使用相同的Python环境"""
    if not is_pipeline_running():
        try:
            # 获取当前Python解释器的完整路径
            python_executable = sys.executable
            print(f"当前Python解释器路径: {python_executable}")
            
            # 获取当前工作目录的绝对路径
            current_dir = os.path.abspath(os.getcwd())
            pipeline_script = os.path.join(current_dir, "paper_pipeline.py")
            print(f"流水线脚本路径: {pipeline_script}")
            
            if os.name == 'nt':  # Windows
                print("在Windows上启动新的进程")
                # 创建启动信息对象以隐藏窗口
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # 隐藏窗口
                
                # 使用完整路径的Python解释器启动脚本
                subprocess.Popen(
                    [python_executable, pipeline_script],
                    stdout=open("pipeline.log", "w"),
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            else:  # Linux/Mac
                print("在Linux/Mac上启动新的进程")
                # 使用完整路径的Python解释器启动脚本
                cmd = f"nohup {python_executable} {pipeline_script} > pipeline.log 2>&1 &"
                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 start_new_session=True)
            
            # 等待一小段时间，确保进程已启动并创建了日志文件
            time.sleep(2)
            
            # 检查日志文件
            if os.path.exists("pipeline.log"):
                print("pipeline.log已创建")
                with open("pipeline.log", "r") as log_file:
                    log_content = log_file.read()
                    print(f"pipeline.log初始内容:\n{log_content}")
            else:
                print("警告: pipeline.log未创建")
            
            print("已启动论文处理流水线后台任务")
            st.success("已成功启动论文处理流水线")
        except Exception as e:
            error_msg = f"启动论文处理流水线失败: {str(e)}"
            print(error_msg)
            st.error(error_msg)
    else:
        print("论文处理流水线已在运行中") 