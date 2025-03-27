import os
import shutil
import psutil
import subprocess
import sys

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
    if os.path.exists("paper_pipeline.log"):
        print("paper_pipeline.log存在")
    else:
        print("paper_pipeline.log不存在！！！")
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
    """启动paper_pipeline.py作为完全独立的后台进程"""
    if not is_pipeline_running():
        try:
            # 创建一个完全分离的进程
            if os.name == 'nt':  # Windows
                print("在Windows上启动新的控制台窗口")
                # 使用start命令启动新的控制台窗口（隐藏）
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # 隐藏窗口
                
                # 使用pythonw.exe而不是python.exe以避免控制台窗口
                python_exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                
                subprocess.Popen(
                    [python_exe, 'paper_pipeline.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            else:  # Linux/Mac
                print("在Linux/Mac上启动新的进程")
                # 使用nohup命令确保进程在终端关闭后继续运行
                cmd = f"nohup python paper_pipeline.py > pipeline.log 2>&1 &"
                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 start_new_session=True)
            
            print("已启动论文处理流水线后台任务")
        except Exception as e:
            st.error(f"启动论文处理流水线失败: {str(e)}")
    else:
        print("论文处理流水线已在运行中") 