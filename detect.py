import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

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

    def on_created(self, event):
        if not event.is_directory:
            msg = f"New file created - {event.src_path}"
            print(msg)  # 控制台输出，也会在GUI中显示
            self.output_area.insert(tk.END, msg + "\n")
            self.output_area.see(tk.END)  # 自动滚动到底部
            # 省略上传文件的代码
            if not event.is_directory:
                print(f"New file created - {event.src_path}")
                # 调用外部接口
                try:
                    files = {'file': open(event.src_path, 'rb')}
                    response = requests.post(self.api_url, files=files)
                    print(response.text)
                except Exception as e:
                    print(f"Failed to call API: {e}")


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
        start_button.config(state='disabled')
        stop_button.config(state='normal')
        print(f"Started watching {directory} for new files...")


def stop_watching():
    watcher_thread.stop()
    directory_entry.config(state='normal')
    api_url_entry.config(state='normal')
    select_button.config(state='normal')
    start_button.config(state='normal')
    stop_button.config(state='disabled')
    print("Stopped watching for new files.")


def select_directory():
    directory = filedialog.askdirectory()
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


app = tk.Tk()
app.title("File Watcher GUI")
app.geometry("600x400")  # 窗口大小调整
app.protocol("WM_DELETE_WINDOW", on_closing)

directory_entry = tk.Entry(app, width=50)
directory_entry.pack(pady=5)

select_button = tk.Button(app, text="Select Directory",
                          command=select_directory)
select_button.pack(pady=5)

api_url_entry = tk.Entry(app, width=50)
api_url_entry.pack(pady=5)
api_url_entry.insert(0, "http://127.0.0.1:5000/upload")  # 设置默认值

start_button = tk.Button(app, text="Start Watching", command=start_watching)
start_button.pack(pady=5)

stop_button = tk.Button(app, text="Stop Watching", command=stop_watching)
stop_button.pack(pady=5)
stop_button.config(state='disabled')  # 初始时禁用停止按钮

output_text = scrolledtext.ScrolledText(app, height=10)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

stdout_redirector = OutputRedirector(output_text)
stderr_redirector = OutputRedirector(output_text)

sys.stdout = stdout_redirector
sys.stderr = stderr_redirector

app.mainloop()
