import os
import subprocess

# 查询当前目录下的除了自己以外的所有.py文件
scripts = [file for file in os.listdir() if file.endswith('.py')
           and file != 'build.py']
# 列出所有的.py文件，让用户通过键盘上下键选择
print("请选择要打包的Python脚本：")
for i, script in enumerate(scripts):
    print(f"{i + 1}. {script}")
index = int(input("输入序号：")) - 1
script_name = scripts[index]

# 询问是否需要console窗口
need_console = input("是否需要console窗口？（y/n）")

# PyInstaller的命令参数
# --onefile 创建单个可执行文件
# --clean 清理打包过程中的临时文件
# --noconsole 不显示命令行窗口（适用于GUI应用）
if need_console.lower() == 'y':
    command = f'pyinstaller --onefile --clean  {script_name}'
else:
    command = f'pyinstaller --onefile --clean --noconsole {script_name}'


# 执行命令
process = subprocess.run(command, shell=True)

# 检查命令执行结果
if process.returncode == 0:
    print("打包成功!")
else:
    print("打包失败。")
