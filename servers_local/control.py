"""
Local Control MCP Server - 本地电脑控制服务器

提供截图、鼠标点击、键盘输入、进程终止等安全的远程控制功能。
安全设计原则：
- 禁止任意命令执行
- 应用启动使用白名单函数
- 所有操作有日志记录

使用 MCP 1.25+ FastMCP API
"""
import asyncio
import sys
import os
import logging
import base64
import io
import platform
import subprocess
from typing import Optional
from datetime import datetime

# MCP imports - 使用新版 FastMCP
from mcp.server import FastMCP

# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(
    level=logging.INFO, 
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("local-control")

# Create MCP server instance using FastMCP
mcp = FastMCP("local-control-server")


# ============== 安全白名单应用启动函数 ==============
# 禁止任意命令执行，只允许以下预定义的函数

ALLOWED_APPS = {
    "notepad": "记事本",
    "calc": "计算器", 
    "mspaint": "画图",
    "explorer": "文件资源管理器",
}

def open_notepad():
    """打开记事本"""
    if platform.system() == "Windows":
        subprocess.Popen(["notepad.exe"], shell=False)
        return "记事本已启动"
    return "仅支持Windows系统"

def open_calc():
    """打开计算器"""
    if platform.system() == "Windows":
        subprocess.Popen(["calc.exe"], shell=False)
        return "计算器已启动"
    return "仅支持Windows系统"

def open_mspaint():
    """打开画图工具"""
    if platform.system() == "Windows":
        subprocess.Popen(["mspaint.exe"], shell=False)
        return "画图工具已启动"
    return "仅支持Windows系统"

def open_explorer():
    """打开文件资源管理器"""
    if platform.system() == "Windows":
        subprocess.Popen(["explorer.exe"], shell=False)
        return "文件资源管理器已启动"
    return "仅支持Windows系统"

# 应用名到启动函数的映射
APP_LAUNCHERS = {
    "notepad": open_notepad,
    "calc": open_calc,
    "mspaint": open_mspaint,
    "explorer": open_explorer,
}


# ============== MCP 工具定义 ==============

@mcp.tool()
async def get_screenshot() -> str:
    """
    截取当前屏幕截图，返回截图保存路径和base64编码的PNG图像摘要
    """
    try:
        import pyautogui
        from PIL import Image
        
        logger.info("正在截取屏幕...")
        
        # 截取屏幕
        screenshot = pyautogui.screenshot()
        
        # 转换为base64
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 保存到本地用于调试
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = os.path.dirname(__file__)
        save_path = os.path.join(save_dir, f"screenshot_{timestamp}.png")
        screenshot.save(save_path)
        
        logger.info(f"截图成功，已保存到 {save_path}")
        
        return f"【截图成功】分辨率: {screenshot.width}x{screenshot.height}，已保存到: {save_path}"
        
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install pyautogui pillow"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"截图失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """
    在屏幕指定坐标位置执行鼠标点击
    
    Args:
        x: 屏幕X坐标（像素）
        y: 屏幕Y坐标（像素）
        button: 鼠标按钮，'left', 'right' 或 'middle'，默认 'left'
        clicks: 点击次数，默认1次，2为双击
    """
    try:
        import pyautogui
        
        # 安全检查：确保坐标在屏幕范围内
        screen_width, screen_height = pyautogui.size()
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            return f"【错误】坐标超出屏幕范围。屏幕尺寸: {screen_width}x{screen_height}，请求坐标: ({x}, {y})"
        
        # 验证按钮参数
        if button not in ["left", "right", "middle"]:
            return f"【错误】无效的鼠标按钮: {button}。允许值: left, right, middle"
        
        # 验证点击次数
        if clicks < 1 or clicks > 3:
            return f"【错误】点击次数必须在1-3之间，当前: {clicks}"
        
        logger.info(f"执行点击: ({x}, {y}), 按钮={button}, 次数={clicks}")
        
        # 执行点击
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        
        return f"【点击成功】在坐标 ({x}, {y}) 执行了 {clicks} 次 {button} 键点击"
        
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install pyautogui"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"点击操作失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def type_string(text: str, interval: float = 0.05) -> str:
    """
    模拟键盘输入指定文本
    
    Args:
        text: 要输入的文本内容
        interval: 每个字符之间的间隔时间（秒），默认0.05秒
    """
    try:
        import pyautogui
        
        # 安全检查：限制文本长度
        MAX_LENGTH = 1000
        if len(text) > MAX_LENGTH:
            return f"【错误】文本过长，最大允许 {MAX_LENGTH} 字符，当前: {len(text)}"
        
        # 安全检查：过滤危险字符组合
        dangerous_patterns = ["rm -rf", "format", "del /", "shutdown", "reboot"]
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern in text_lower:
                logger.warning(f"检测到危险文本模式: {pattern}")
                return f"【安全拦截】检测到潜在危险命令模式，已阻止输入"
        
        logger.info(f"输入文本: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # 执行输入 - pyautogui.typewrite 只支持ASCII
        if text.isascii():
            pyautogui.typewrite(text, interval=interval)
        else:
            # 对于非ASCII字符，使用剪贴板方式
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        
        return f"【输入成功】已输入 {len(text)} 个字符"
        
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install pyautogui pyperclip"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"文本输入失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def kill_process(process_name: str) -> str:
    """
    终止指定名称的进程（用于紧急停止，仅支持白名单进程）
    
    Args:
        process_name: 要终止的进程名称，如 'notepad.exe'
    """
    try:
        import psutil
        
        # 安全白名单：只允许终止特定进程
        ALLOWED_TO_KILL = [
            "notepad.exe", "calc.exe", "mspaint.exe",
            "python.exe", "pythonw.exe",
            "cmd.exe", "powershell.exe"
        ]
        
        # 标准化进程名
        process_name_lower = process_name.lower()
        if not process_name_lower.endswith('.exe'):
            process_name_lower += '.exe'
        
        # 检查是否在白名单中
        if process_name_lower not in [p.lower() for p in ALLOWED_TO_KILL]:
            return f"【安全拦截】不允许终止进程: {process_name}。允许终止的进程: {', '.join(ALLOWED_TO_KILL)}"
        
        logger.info(f"尝试终止进程: {process_name}")
        
        # 查找并终止进程
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name_lower:
                    proc.terminate()
                    killed_count += 1
                    logger.info(f"已终止进程 PID={proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if killed_count > 0:
            return f"【成功】已终止 {killed_count} 个 {process_name} 进程"
        else:
            return f"【未找到】没有找到运行中的 {process_name} 进程"
            
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install psutil"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"终止进程失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def open_app(app_name: str) -> str:
    """
    打开白名单中的应用程序
    
    Args:
        app_name: 应用名称，支持: notepad(记事本), calc(计算器), mspaint(画图), explorer(资源管理器)
    """
    app_name_lower = app_name.lower().strip()
    
    if app_name_lower not in APP_LAUNCHERS:
        available = ", ".join([f"{k}({v})" for k, v in ALLOWED_APPS.items()])
        return f"【错误】不支持的应用: {app_name}。可用应用: {available}"
    
    logger.info(f"启动应用: {app_name}")
    
    try:
        result = APP_LAUNCHERS[app_name_lower]()
        return f"【成功】{result}"
    except Exception as e:
        error_msg = f"启动应用失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def get_system_info() -> str:
    """
    获取当前系统信息（操作系统、CPU、内存等）
    """
    try:
        import psutil
        
        # 收集系统信息
        info = {
            "操作系统": f"{platform.system()} {platform.release()}",
            "主机名": platform.node(),
            "处理器": platform.processor(),
            "Python版本": platform.python_version(),
            "CPU核心数": psutil.cpu_count(),
            "CPU使用率": f"{psutil.cpu_percent()}%",
            "内存总量": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
            "内存使用率": f"{psutil.virtual_memory().percent}%",
        }
        
        # Windows磁盘
        if platform.system() == "Windows":
            info["磁盘使用率(C:)"] = f"{psutil.disk_usage('C:').percent}%"
        else:
            info["磁盘使用率(/)"] = f"{psutil.disk_usage('/').percent}%"
        
        # 获取屏幕分辨率
        try:
            import pyautogui
            screen_size = pyautogui.size()
            info["屏幕分辨率"] = f"{screen_size.width}x{screen_size.height}"
        except:
            info["屏幕分辨率"] = "无法获取"
        
        # 格式化输出
        result = "【系统信息】\n"
        for key, value in info.items():
            result += f"  {key}: {value}\n"
        
        logger.info("获取系统信息成功")
        return result
        
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install psutil"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"获取系统信息失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


@mcp.tool()
async def get_mouse_position() -> str:
    """
    获取当前鼠标位置坐标
    """
    try:
        import pyautogui
        
        pos = pyautogui.position()
        screen_size = pyautogui.size()
        
        return f"【鼠标位置】当前坐标: ({pos.x}, {pos.y})，屏幕尺寸: {screen_size.width}x{screen_size.height}"
        
    except ImportError as e:
        return f"【错误】缺少依赖库: {e}. 请运行: pip install pyautogui"
    except Exception as e:
        return f"【错误】获取鼠标位置失败: {str(e)}"


@mcp.tool()
async def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    将鼠标移动到指定坐标
    
    Args:
        x: 目标X坐标
        y: 目标Y坐标
        duration: 移动持续时间（秒），默认0.5秒
    """
    try:
        import pyautogui
        
        # 安全检查
        screen_width, screen_height = pyautogui.size()
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            return f"【错误】坐标超出屏幕范围。屏幕尺寸: {screen_width}x{screen_height}"
        
        logger.info(f"移动鼠标到: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=duration)
        
        return f"【成功】鼠标已移动到 ({x}, {y})"
        
    except ImportError as e:
        return f"【错误】缺少依赖库: {e}. 请运行: pip install pyautogui"
    except Exception as e:
        return f"【错误】鼠标移动失败: {str(e)}"


# ============== 主函数 ==============

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Local Control MCP Server 启动中...")
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    logger.info("可用工具: get_screenshot, click_at, type_string, kill_process, open_app, get_system_info, get_mouse_position, move_mouse")
    logger.info("=" * 50)
    
    # 使用 FastMCP 的 run 方法
    mcp.run()
