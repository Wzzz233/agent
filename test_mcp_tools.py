"""
简单的命令行测试工具 - 直接测试本地控制MCP Server工具

用于快速验证MCP Server工具是否正常工作，
无需启动完整的Agent服务。

使用方法:
1. 安装依赖: pip install -r servers/local_server_requirements.txt  
2. 运行: python test_mcp_tools.py
"""
import asyncio
import sys
import os

# 设置Windows事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 添加 servers_local 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'servers_local'))


async def test_tools():
    """直接调用工具函数进行测试"""
    print("=" * 50)
    print("MCP 工具直接测试")
    print("=" * 50)
    
    try:
        from control import (
            get_screenshot,
            get_system_info,
            get_mouse_position,
            click_at,
            type_string,
            open_app,
            move_mouse,
            kill_process
        )
        print("✓ 工具导入成功")
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        print("请先安装依赖: pip install -r servers/local_server_requirements.txt")
        return
    
    while True:
        print("\n" + "=" * 50)
        print("可用测试命令:")
        print("  1. 截图测试 (get_screenshot)")
        print("  2. 系统信息 (get_system_info)")
        print("  3. 鼠标位置 (get_mouse_position)")
        print("  4. 打开记事本 (open_app notepad)")
        print("  5. 移动鼠标到屏幕中心 (move_mouse)")
        print("  6. 在指定位置点击 (click_at)")
        print("  7. 输入文本 (type_string)")
        print("  8. 终止记事本 (kill_process)")
        print("  9. 打开计算器 (open_app calc)")
        print("  0. 退出")
        print("-" * 50)
        
        try:
            choice = input("请选择 (0-9): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出测试")
            break
        
        if choice == "0":
            print("退出测试")
            break
        elif choice == "1":
            print("\n执行截图...")
            result = await get_screenshot()
            print(result)
        elif choice == "2":
            print("\n获取系统信息...")
            result = await get_system_info()
            print(result)
        elif choice == "3":
            print("\n获取鼠标位置...")
            result = await get_mouse_position()
            print(result)
        elif choice == "4":
            print("\n打开记事本...")
            result = await open_app("notepad")
            print(result)
        elif choice == "5":
            print("\n移动鼠标到屏幕中心...")
            try:
                import pyautogui
                w, h = pyautogui.size()
                result = await move_mouse(w // 2, h // 2)
                print(result)
            except Exception as e:
                print(f"错误: {e}")
        elif choice == "6":
            try:
                x = int(input("输入X坐标: "))
                y = int(input("输入Y坐标: "))
                result = await click_at(x, y)
                print(result)
            except ValueError:
                print("请输入有效的数字坐标")
        elif choice == "7":
            text = input("输入要输入的文本: ")
            if text:
                result = await type_string(text)
                print(result)
        elif choice == "8":
            print("\n终止记事本进程...")
            result = await kill_process("notepad.exe")
            print(result)
        elif choice == "9":
            print("\n打开计算器...")
            result = await open_app("calc")
            print(result)
        else:
            print("无效选择，请重试")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("本地控制 MCP 工具测试程序")
    print("=" * 50 + "\n")
    asyncio.run(test_tools())
