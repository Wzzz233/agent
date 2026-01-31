"""
快速配置 API 密钥
"""
import os
from pathlib import Path

def setup_api():
    """Interactive API setup"""
    print("=" * 60)
    print("ADS Agent - API 配置向导")
    print("=" * 60)
    
    print("\n请选择 LLM 提供商:")
    print("1. DeepSeek API (推荐，性价比最高)")
    print("2. OpenAI API (GPT-4o-mini)")
    print("3. OpenAI API (GPT-4o)")
    print("4. 本地模型 (LM Studio)")
    print("5. 自定义 OpenAI 兼容 API")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    configs = {
        "1": {
            "model": "deepseek-chat",
            "server": "https://api.deepseek.com/v1",
            "name": "DeepSeek"
        },
        "2": {
            "model": "gpt-4o-mini",
            "server": "https://api.openai.com/v1",
            "name": "OpenAI GPT-4o-mini"
        },
        "3": {
            "model": "gpt-4o",
            "server": "https://api.openai.com/v1",
            "name": "OpenAI GPT-4o"
        },
        "4": {
            "model": "qwen3-8b-finetuned",
            "server": "http://127.0.0.1:1234/v1",
            "name": "本地模型",
            "api_key": "EMPTY"
        }
    }
    
    if choice in configs:
        config = configs[choice]
        print(f"\n已选择: {config['name']}")
        
        if choice != "4":
            api_key = input(f"\n请输入 {config['name']} 的 API Key: ").strip()
            config["api_key"] = api_key
        
    elif choice == "5":
        print("\n自定义配置:")
        config = {
            "model": input("模型名称: ").strip(),
            "server": input("API 服务器地址: ").strip(),
            "api_key": input("API Key: ").strip(),
            "name": "自定义"
        }
    else:
        print("无效选项")
        return
    
    # Write .env file
    env_path = Path(__file__).parent / '.env'
    
    env_content = f"""# ============== LLM Configuration ==============
# 当前使用: {config['name']}

LLM_MODEL={config['model']}
LLM_MODEL_SERVER={config['server']}
LLM_API_KEY={config.get('api_key', 'YOUR_API_KEY_HERE')}
LLM_TEMPERATURE=0.3

# ============== Agent Configuration ==============
AGENT_NAME=ADS_Designer
AGENT_DESCRIPTION=ADS电路设计助手

# ============== MCP Configuration ==============
MCP_ENABLED=true
MCP_SERVERS=[{{"name":"ads_server","transport_type":"sse","url":"http://localhost:5000/sse"}}]

# ============== Web Search ==============
WEB_SEARCH_ENABLED=false

# ============== Server Configuration ==============
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false
"""
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"\n✅ 配置已保存到: {env_path}")
    print(f"\n下一步:")
    print(f"1. 运行测试: python test_llm_connection.py")
    print(f"2. 启动 Agent: python start_agent.py")

if __name__ == "__main__":
    setup_api()
