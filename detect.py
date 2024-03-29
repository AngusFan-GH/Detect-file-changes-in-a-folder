import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import winreg as reg
from tkinter import filedialog, messagebox, scrolledtext

import chardet
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class OutputRedirector(object):
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        if self.text_widget and self.text_widget.winfo_exists():
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
        else:
            sys.__stdout__.write(string)

    def flush(self):
        pass


class ThreadedTask(threading.Thread):
    def __init__(self, directory, api_url, output_area):
        threading.Thread.__init__(self)
        self.directory = directory
        self.api_url = api_url
        self.output_area = output_area
        self.observer = Observer()
        self._stop_event = threading.Event()  # 线程停止事件

    def run(self):
        event_handler = Handler(self.api_url, self.output_area)
        event_handler.watch_directory = self.directory
        self.observer.schedule(event_handler, self.directory, recursive=True)
        self.observer.start()
        try:
            while not self._stop_event.is_set():  # 检查是否有停止请求
                self._stop_event.wait(timeout=1)  # 1秒超时来检查停止标志
        finally:
            self.observer.stop()
            self.observer.join()

    def stop(self):
        self._stop_event.set()  # 设置停止标志
        self.observer.stop()
        self.observer.join()  # 确保观察者线程完全停止
        self.join()  # 确保当前线程完全停止


class Handler(FileSystemEventHandler):
    def __init__(self, api_url, output_area):
        self.api_url = api_url
        self.output_area = output_area

    def is_target_file(self, file_path, root_path):
        # 将文件路径标准化（移除末尾的文件名，保留目录路径）
        file_dir = os.path.dirname(file_path)
        # print(f"file_dir: {file_dir}")
        # 计算根目录到当前文件目录的相对路径
        relative_dir = os.path.relpath(file_dir, root_path)
        # print(f"relative_dir: {relative_dir}")
        # 计算路径中包含的目录级数
        depth = len(relative_dir.split(os.path.sep))
        # print(f"depth: {depth}")
        # 检查文件是否是index.txt且位于第三级子目录中
        is_index_file = os.path.basename(file_path) == 'index.txt'
        # depth == 2
        return is_index_file and depth == 2

    def on_created(self, event):
        if not event.is_directory and self.is_target_file(event.src_path, self.watch_directory):
            msg = f"New file created - {event.src_path}"
            print(msg)  # 控制台输出，也会在GUI中显示
            self.output_area.see(tk.END)  # 自动滚动到底部
            log_file_path = os.path.join(
                os.path.dirname(event.src_path), 'log.txt')
            print(f"log_file_path: {log_file_path}")
            try:
                # 解析log.txt并转换为JSON
                log_data_json = parse_log_file(log_file_path)
                print(f"log data in JSON format: {log_data_json}")

                # files = {'file': open(event.src_path, 'rb')}
                # response = requests.post(self.api_url, files=files)
                # print(response.text)
            except Exception as e:
                print(f"Failed to call API: {e}")


def toggle_start_stop():
    global is_running
    if is_running:
        is_running = False
        toggle_button.config(text="Start Watching", command=start_watching)
    else:
        is_running = True
        toggle_button.config(text="Stop Watching", command=stop_watching)


def start_watching():
    directory = directory_entry.get()
    api_url = api_url_entry.get()
    if directory and api_url:
        global watcher_thread
        watcher_thread = ThreadedTask(directory, api_url, output_text)
        watcher_thread.start()
        directory_entry.config(state='disabled')
        api_url_entry.config(state='disabled')
        select_button.config(state='disabled')
        update_config(directory=directory, api_url=api_url)
        toggle_start_stop()
        print(f"Started watching {directory} for new files...")


def stop_watching():
    watcher_thread.stop()
    directory_entry.config(state='normal')
    api_url_entry.config(state='normal')
    select_button.config(state='normal')
    toggle_start_stop()
    print("Stopped watching for new files.")


def select_directory():
    directory = filedialog.askdirectory()
    if directory:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, directory)


def on_closing():
    if messagebox.askokcancel("退出", "是否退出应用程序？"):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        try:
            watcher_thread.stop()
        except NameError:
            pass
        app.destroy()
        sys.exit()


def set_auto_start_with_task_scheduler(enabled, app_name, app_path):
    """
    使用Windows任务计划程序设置或取消程序的开机自启动。
    :param enabled: True 设置自启动，False 取消自启动
    :param app_name: 任务计划中的任务名称
    :param app_path: 程序的路径
    """
    try:
        if enabled:
            # 创建任务计划命令
            command = f'schtasks /create /tn "{app_name}" /tr "{app_path}" /sc onlogon /rl highest /f'
        else:
            # 删除任务计划命令
            command = f'schtasks /delete /tn "{app_name}" /f'

        result = subprocess.run(
            command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Task scheduler command executed. Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing task scheduler command: {e.output}")
        return False


def toggle_auto_start():
    """切换自启动设置"""
    app_name = "DetectFileWatcher"
    app_path = os.path.realpath(sys.argv[0])  # 当前脚本路径
    if set_auto_start_with_task_scheduler(auto_start_var.get(), app_name, app_path):
        messagebox.showinfo("Success", "Setting updated successfully!")
        update_config(auto_start=auto_start_var.get())
    else:
        messagebox.showerror("Error", "Failed to update setting.")
        auto_start_var.set(not auto_start_var.get())  # 恢复之前的状态


def save_config(config):
    with open(config_file_path, 'w') as file:
        json.dump(config, file, indent=4)


def load_config():
    try:
        with open(config_file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        # 文件不存在，返回默认配置
        return {
            "directory": os.path.dirname(os.path.abspath(__file__)),
            "api_url": "http://127.0.0.1:5000/upload",
            "auto_start": False
        }


def update_config(**kwargs):
    # 如果kwargs有内容，则只更新指定的键值对
    if kwargs:
        for key, value in kwargs.items():
            config[key] = value
            print(f"Updated config: {key} = {value}")
    else:
        # 如果没有提供具体的键值对，更新所有配置项
        config['directory'] = directory_entry.get()
        config['api_url'] = api_url_entry.get()
        config['auto_start'] = auto_start_var.get()
        print(f"Updated config: {config}")

    save_config(config)


def parse_log_file(log_file_path):
    # 读取log.txt文件内容
    with open(log_file_path, 'rb') as f:
        raw_data = f.read()
        encoding = chardet.detect(raw_data)['encoding']
        print(f"encoding: {encoding}")
    with open(log_file_path, 'r', encoding=encoding) as file:
        lines = file.readlines()

    data = []
    for line in lines:
        print(line.strip())
        if line.startswith('车号:'):
            car_info = {}
            car_info['车号'] = line.split(':')[1].strip()
            data.append(car_info)
        elif '车速' in line:
            if data:
                data[-1]['车速'] = line.split(':')[1].strip()
        # elif '扫描行数' in line:
            # if data:
                # data[-1]['扫描行数'] = line.split(':')[1].strip()
        elif '顺位' in line:
            if data:
                data[-1]['顺位'] = line.split(':')[1].strip()

    return json.dumps(data, ensure_ascii=False)


# 配置文件路径
config_file_path = os.path.join(
    os.path.expanduser('~'), 'DetectFileWatcher', 'config.json')

# 确保配置文件的目录存在
os.makedirs(os.path.dirname(config_file_path), exist_ok=True)

config = load_config()
print(f"Loaded config: {config}")

app = tk.Tk()
app.title("File Watcher GUI")
app.geometry("600x400")  # 窗口大小调整
app.protocol("WM_DELETE_WINDOW", on_closing)

# 为目录输入创建一个容器Frame
directory_frame = tk.Frame(app)
directory_frame.pack(pady=5)  # 放置frame，并设置垂直外边距
# 在目录输入前加上标题
directory_label = tk.Label(directory_frame, text="Path:")
directory_label.pack(side=tk.LEFT)  # 标题放在左侧
directory_entry = tk.Entry(directory_frame, width=50)
directory_entry.pack(side=tk.LEFT, padx=10)
directory_entry.insert(0, config.get('directory'))

select_button = tk.Button(directory_frame, text="Select Directory",
                          command=select_directory)
select_button.pack(pady=5)

# 为API输入创建一个容器Frame
api_frame = tk.Frame(app)
api_frame.pack(pady=5)  # 放置frame，并设置垂直外边距
# 在API输入前加上标题
api_label = tk.Label(api_frame, text="API:")
api_label.pack(side=tk.LEFT)  # 标题放在左侧
api_url_entry = tk.Entry(api_frame, width=50)
api_url_entry.pack(side=tk.LEFT, padx=10)
api_url_entry.insert(0, config.get(
    'api_url'))  # 设置默认值

is_running = False  # 跟踪监听状态

toggle_button = tk.Button(app, text="Start Watching",
                          command=start_watching)
toggle_button.pack(pady=20)

output_text = scrolledtext.ScrolledText(app, height=10)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# 自启动勾选框的变量
auto_start_var = tk.BooleanVar()
auto_start_check = tk.Checkbutton(
    app, text="Enable Auto Start", var=auto_start_var, command=toggle_auto_start)
auto_start_check.pack(pady=20)
auto_start_var.set(config.get('auto_start', False))

stdout_redirector = OutputRedirector(output_text)
stderr_redirector = OutputRedirector(output_text)

sys.stdout = stdout_redirector
sys.stderr = stderr_redirector

app.mainloop()
