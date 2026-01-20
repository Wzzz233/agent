import json
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool  # <--- 修改1: 引入 register_tool 装饰器 (虽然不是必须，但推荐规范)

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

# --- 修改2: 显式给你的工具类加上 name 属性 ---
class MockLaserControl(BaseTool):
    # 必须显式定义 name，且要和类名或下方调用的名字一致
    name = "mock_laser_control"  
    description = "控制飞秒激光器的开关和功率"
    parameters = [{
        "name": "command",
        "type": "string",
        "description": "指令内容，只能是 'on', 'off' 或 'set_power'",
        "required": True
    }, {
        "name": "value",
        "type": "integer",
        "description": "当指令为 'set_power' 时，设置的具体功率值(mW)",
        "required": False
    }]

    def call(self, params: str, **kwargs):
        # 注意：这里加个 try-except 防止 JSON 解析炸了
        try:
            args = json.loads(params)
        except json.JSONDecodeError:
            return "参数格式错误，请使用 JSON"
            
        cmd = args.get('command')
        if cmd == 'on':
            return "【硬件反馈】激光器已开启，预热中..."
        elif cmd == 'set_power':
            val = args.get('value', 0)
            return f"【硬件反馈】功率已调节至 {val} mW"
        return "【硬件反馈】指令无效"

# --- 新增: 网络搜索工具（改进版 - 使用 duckduckgo_search）---
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search information on the internet using DuckDuckGo. Use English keywords for better results. Returns search results with titles, URLs, and snippets."
    parameters = [{
        "name": "query",
        "type": "string",
        "description": "Search keywords in ENGLISH (e.g., 'terahertz spectroscopy advances 2024')",
        "required": True
    }]

    def call(self, params: str, **kwargs):
        # 检查依赖是否可用
        if not DDGS_AVAILABLE:
            return (
                "[ERROR] ddgs package is not installed. "
                "Please install it using: pip install ddgs"
            )

        try:
            args = json.loads(params)
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON format in parameters."

        query = args.get('query', '').strip()
        if not query:
            return "[ERROR] Search query cannot be empty."

        try:
            # 使用 duckduckgo_search 进行搜索
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=5))

            if not results:
                return (
                    f"[NO RESULTS] No search results found for: '{query}'\n"
                    f"Try using different or more general keywords."
                )

            # 格式化搜索结果
            result_parts = [f"[SEARCH RESULTS] Query: '{query}'\n"]
            result_parts.append("Search Results:")
            result_parts.append("=" * 60)

            for i, r in enumerate(results, 1):
                result_parts.append(f"\n{i}. {r.get('title', 'No title')}")
                result_parts.append(f"   URL: {r.get('href', 'No URL')}")
                result_parts.append(f"   {r.get('body', 'No description')[:200]}...")

            result_parts.append("\n" + "=" * 60)
            result_parts.append("[NOTE] Please use the above information to answer the user's question.")

            return "\n".join(result_parts)

        except Exception as e:
            return (
                f"[SEARCH FAILED] Error occurred: {str(e)}\n"
                f"Please try again with a different query or answer based on existing knowledge."
            )

# --- 修改3: 在 Assistant 初始化时，传入的是【实例】而不是【类】 ---
# 或者传入字典配置（这是 qwen-agent 最稳妥的方式）
tool_config = {
    'mock_laser_control': MockLaserControl  # 将名称映射到类
}

# 这里的 function_list 也可以直接传 name 字符串，只要上面定义对了
# 但为了避坑，我们直接传入 "工具的名字" 字符串列表，并依靠 qwen-agent 的自动发现机制
# 最简单粗暴的修复：直接把工具【名称】传进去，并在外部注册，或者直接传【实例对象】
# 下面这种写法在较新版本的 qwen-agent 中最稳：

bot = Assistant(
    llm={
        "model": "qwen3-8b-finetuned",  # 请确保这和 vLLM/Ollama 里的名字完全一样！
        "model_server": "http://127.0.0.1:1234/v1", 
        "api_key": "EMPTY",
        "generate_cfg": {"temperature": 0.01}
    },
    name="THz_Operator",
    description="实验操作员",
    # !!! 核心修复点 !!!
    # 不要传 [MockLaserControl]，而是传实例化后的对象列表，或者使用 name 字符串
    # 如果不想用装饰器注册，最直接的办法是把 tools 列表单独传给 extra_tools
    function_list=[MockLaserControl(), WebSearchTool()], # <--- 添加了网络搜索工具
    system_message="你是一个太赫兹实验助手。收到操作指令时，可以调用激光控制工具或网络搜索工具获取信息。重要提示：每个问题最多只搜索一次，如果搜索无结果，请基于已有知识回答，不要重复搜索。使用英文关键词搜索效果更好。"
)

print("--- 测试开始 ---")

# 测试1: 激光器控制
print("\n=== 测试1: 激光器控制 ===")
instruction1 = "帮我打开激光器，然后把功率调到 500mW"
for response in bot.run(messages=[{'role': 'user', 'content': instruction1}]):
    print(response)

# 测试2: 网络搜索（使用英文关键词）
print("\n=== 测试2: 网络搜索 ===")
instruction2 = "Search for information about terahertz spectroscopy technology advances in 2024"
for response in bot.run(messages=[{'role': 'user', 'content': instruction2}]):
    print(response)
