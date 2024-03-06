import os
import subprocess

# 要打包的Python脚本的名称
script_name = input("请输入要打包的Python脚本的名称（包括扩展名）：")

# 检查输入名相同的旧文件是否存在，如果存在则删除
if os.path.exists('dist/' + script_name):
    os.remove('dist/' + script_name)

# PyInstaller的命令参数
# --onefile 创建单个可执行文件
# --noconsole 不显示命令行窗口（适用于GUI应用）
# --icon=app.ico 添加图标，如果需要的话，路径需替换为实际图标的路径
# 如果不需要图标，可以从命令中移除 --icon 参数
pyinstaller_command = f'pyinstaller --onefile --noconsole {script_name}'

# 执行命令
process = subprocess.run(pyinstaller_command, shell=True)

# 检查命令执行结果
if process.returncode == 0:
    print("打包成功!")
else:
    print("打包失败。")
