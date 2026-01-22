"""
本地Agent测试脚本 - 使用本地LLM和本地/云端MCP工具

本脚本模拟了 Agent 的运作：
1. 所有的 MCP 工具被加载（包括本地控制和模拟的云端搜索）
2. LLM (Qwen) 决定调用哪些工具
3. 脚本执行这些工具并返回结果给 LLM

架构变更适配：
- servers_local: 物理机控制 (control.py)
- servers_cloud: 云端工具 (search.py, laser.py)
"""
import os
import sys
import json
import asyncio
import httpx
from typing import Optional, List, Dict, Any

# 设置Windows事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 添加服务目录到路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CURRENT_DIR, 'servers_local'))
sys.path.insert(0, os.path.join(CURRENT_DIR, 'servers_cloud'))

# LM Studio 配置
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "qwen3-8b-finetuned"

# 系统提示词
SYSTEM_PROMPT = """你是一个智能电脑控制助手。你可以通过以下工具来控制用户的电脑或获取信息：

【本地控制工具】(物理机执行)
1. get_screenshot() - 截取屏幕截图
2. click_at(x, y) - 鼠标点击
3. type_string(text) - 键盘输入
4. open_app(app_name) - 打开应用
5. get_system_info() - 系统信息
6. kill_process(name) - 终止进程

【云端/网络工具】(远程执行)
7. web_search(query) - 网络搜索

当用户请求操作时，调用相应的工具并报告结果。
如果是需要查询信息，请优先使用 web_search。
"""

# 工具映射
TOOLS = None

def load_tools():
    """加载所有 MCP 工具"""
    global TOOLS
    if TOOLS is not None:
        return TOOLS
    
    TOOLS = {}
    
    # 1. 加载本地控制工具
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
        TOOLS.update({
            "get_screenshot": get_screenshot,
            "get_system_info": get_system_info,
            "get_mouse_position": get_mouse_position,
            "click_at": click_at,
            "type_string": type_string,
            "open_app": open_app,
            "move_mouse": move_mouse,
            "kill_process": kill_process
        })
        print("✓ 本地控制工具已加载")
    except ImportError as e:
        print(f"⚠️ 本地控制工具加载失败: {e}")

    # 2. 加载云端搜索工具
    try:
        from search import web_search
        TOOLS.update({
            "web_search": web_search
        })
        print("✓ 云端搜索工具已加载")
    except ImportError as e:
        print(f"⚠️ 云端搜索工具加载失败: {e}")

    return TOOLS


def get_tool_definitions() -> List[Dict[str, Any]]:
    """返回OpenAI格式的工具定义"""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "执行网络搜索",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "max_results": {"type": "integer", "default": 5}
                    }, 
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_screenshot",
                "description": "截取当前屏幕截图",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "获取系统信息",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_mouse_position",
                "description": "获取当前鼠标位置",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "click_at",
                "description": "在指定坐标点击",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "button": {"type": "string", "enum": ["left", "right"], "default": "left"}
                    },
                    "required": ["x", "y"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "type_string",
                "description": "模拟键盘输入",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "打开应用 (notepad/calc/mspaint/explorer)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "enum": ["notepad", "calc", "mspaint", "explorer"]}
                    },
                    "required": ["app_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "kill_process",
                "description": "终止指定进程",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "process_name": {"type": "string"}
                    },
                    "required": ["process_name"]
                }
            }
        }
    ]


async def call_tool(name: str, arguments: Dict[str, Any]) -> str:
    """调用工具并返回结果"""
    tools = load_tools()
    if name not in tools:
        return f"未知工具: {name}"
    
    try:
        # FastMCP 包装的函数可能是异步的
        result = await tools[name](**arguments)
        return result
    except Exception as e:
        return f"工具调用失败: {str(e)}"


async def chat_with_llm(messages: List[Dict[str, str]], use_tools: bool = True) -> Dict[str, Any]:
    """与LM Studio进行对话"""
    url = f"{LM_STUDIO_URL}/chat/completions"
    
    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    if use_tools:
        payload["tools"] = get_tool_definitions()
        payload["tool_choice"] = "auto"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def process_user_input(user_input: str, history: List[Dict[str, str]]) -> str:
    """处理用户输入"""
    history.append({"role": "user", "content": user_input})
    
    try:
        response = await chat_with_llm(history)
    except Exception as e:
        return f"❌ LLM调用失败: {str(e)}"
    
    assistant_message = response["choices"][0]["message"]
    
    # 检查工具调用
    if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
        tool_results = []
        for tool_call in assistant_message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except:
                tool_args = {}
            
            print(f"  🔧 调用: {tool_name}({tool_args})")
            result = await call_tool(tool_name, tool_args)
            
            # 截取过长的结果以便显示
            display_result = str(result)
            if len(display_result) > 100:
                display_result = display_result[:100] + "..."
            print(f"     结果: {display_result}")
            
            tool_results.append(f"[{tool_name}]: {result}")
        
        history.append(assistant_message)
        history.append({
            "role": "tool",
            "content": "\n".join(tool_results),
            "tool_call_id": assistant_message["tool_calls"][0]["id"]
        })
        
        # 再次调用LLM
        try:
            final_response = await chat_with_llm(history, use_tools=False)
            final_content = final_response["choices"][0]["message"]["content"]
        except:
            final_content = "工具执行完毕。"
        
        history.append({"role": "assistant", "content": final_content})
        return final_content
    else:
        content = assistant_message.get("content", "")
        history.append({"role": "assistant", "content": content})
        return content


async def main():
    print("=" * 60)
    print("🖥️  混合 Agent (本地控制 + 云端搜索)")
    print("=" * 60)
    print(f"本地模块: servers_local/control.py")
    print(f"云端模块: servers_cloud/search.py")
    print("=" * 60)
    
    # 加载工具
    if not load_tools():
        print("❌ 未加载任何工具，请检查依赖")
        return
        
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            if user_input.lower() in ["exit", "quit"]: break
            if not user_input: continue
            
            print("助手: ", end="", flush=True)
            response = await process_user_input(user_input, history)
            print(response)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    asyncio.run(main())
