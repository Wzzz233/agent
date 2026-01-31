import os
from typing import Optional, List
from pydantic import BaseModel, Field
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Config] Loaded environment from: {env_path}")
    else:
        print(f"[Config] No .env file found at: {env_path}")
except ImportError:
    print("[Config] python-dotenv not installed, using environment variables only")


class LLMConfig(BaseModel):
    """Configuration for LLM connection"""
    model: str = Field(default="qwen3-8b-finetuned", description="Model name")
    model_server: str = Field(default="http://127.0.0.1:1234/v1", description="Model server URL")
    api_key: str = Field(default="EMPTY", description="API key for authentication")
    temperature: float = Field(default=0.3, description="Generation temperature")  # Increased from 0.01



class AgentConfig(BaseModel):
    """Configuration for the THz agent"""
    name: str = Field(default="THz_Operator", description="Agent name")
    description: str = Field(default="实验操作员", description="Agent description")
    system_message: str = Field(
        default="你是一个太赫兹实验助手。收到操作指令时，可以调用激光控制工具或网络搜索工具获取信息。重要提示：每个问题最多只搜索一次，如果搜索无结果，请基于已有知识回答，不要重复搜索。使用英文关键词搜索效果更好。",
        description="System message for the agent"
    )


class WebConfig(BaseModel):
    """Configuration for web search functionality"""
    search_enabled: bool = Field(default=True, description="Enable web search functionality")
    max_results: int = Field(default=5, description="Maximum number of search results")


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection"""
    name: str = Field(description="Name of the MCP server (e.g., 'laser_server')")
    transport_type: str = Field(default="stdio", description="Transport type: 'stdio' or 'sse'")
    command: Optional[str] = Field(default=None, description="Command to start the server (for stdio)")
    args: Optional[List[str]] = Field(default=None, description="Arguments for the command (for stdio)")
    url: Optional[str] = Field(default=None, description="URL for the server (for sse or http)")

    class Config:
        # Allow extra fields for flexibility
        extra = "allow"


class MCPConfig(BaseModel):
    """Configuration for MCP connections"""
    enabled: bool = Field(default=True, description="Enable MCP functionality")
    servers: List[MCPServerConfig] = Field(default=[], description="List of MCP server configurations")


class ServerConfig(BaseModel):
    """Configuration for the HTTP API server"""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")


class Config(BaseModel):
    """Main configuration class"""
    llm: LLMConfig = LLMConfig()
    agent: AgentConfig = AgentConfig()
    web: WebConfig = WebConfig()
    mcp: MCPConfig = MCPConfig()
    server: ServerConfig = ServerConfig()

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        # Load MCP servers from environment - allowing JSON format
        import json
        mcp_servers_json = os.getenv('MCP_SERVERS', '[]')
        mcp_servers = []
        try:
            if mcp_servers_json.strip():
                servers_data = json.loads(mcp_servers_json)
                for server_data in servers_data:
                    mcp_servers.append(MCPServerConfig(**server_data))
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, continue with empty list
            pass

        return cls(
            llm=LLMConfig(
                model=os.getenv('LLM_MODEL', 'qwen3-8b-finetuned'),
                model_server=os.getenv('LLM_MODEL_SERVER', 'http://127.0.0.1:1234/v1'),
                api_key=os.getenv('LLM_API_KEY', 'EMPTY'),
                temperature=float(os.getenv('LLM_TEMPERATURE', '0.01'))
            ),
            agent=AgentConfig(
                name=os.getenv('AGENT_NAME', 'THz_Operator'),
                description=os.getenv('AGENT_DESCRIPTION', '实验操作员'),
                system_message=os.getenv(
                    'AGENT_SYSTEM_MESSAGE',
                    '''你是ADS电路设计助手。用自然语言与用户对话，直接执行任务。

## 核心规则
1. **自己执行，不要让用户执行**：当用户请求时，直接调用工具完成任务
2. **用自然语言回复**：不要在回复中提到工具名称或返回JSON
3. **遵循工作流状态**：每个工具返回都会告诉你当前状态和可用工具，严格遵循
4. **绝对不要虚构参数**：plan_id 必须从 plan_circuit 返回中获取，不能编造
5. **检查工具返回的 has_plan 字段**：如果为 False，必须用 add_component

## 工作流状态机

状态 IDLE → 可用：get_project_structure, plan_circuit, open_existing_design
状态 PLAN_CREATED → 需调用 execute_circuit_plan 创建原理图
状态 WAITING_USER → 需调用 confirm_design_open 确认用户打开了设计
状态 COMPONENT_ADDING → 可用：add_component, add_wire, save_current_design

## 设计新电路的完整流程

1. 调用 get_project_structure 获取库名
2. 调用 plan_circuit → 返回 plan_id
3. 调用 execute_circuit_plan(plan_id)
4. 告诉用户在ADS中打开原理图
5. 用户确认后，调用 confirm_design_open
6. 调用 add_components_from_plan

## 在现有设计中添加元件（严格遵循！）

当用户说"在xxx原理图中添加元件"时：
1. 调用 get_project_structure 获取库名
2. 调用 open_existing_design(library_name, cell_name)
3. **必须使用 add_component**（不要用 add_components_from_plan！）
   - add_component 需要参数：design_uri, component_type, instance_name, x, y
   - 例如: add_component("MyLib:test:schematic", "R", "R1", 0, 0)

## 计算元件值

RC低通滤波器：fc = 1 / (2π × R × C)
例如 fc = 2kHz：R = 7960Ω, C = 10nF

## 回复示例

❌ 错误：虚构 plan_id 如 "plan_12345"
✅ 正确：使用工具返回的真实数据
'''
                )

            ),
            web=WebConfig(
                search_enabled=os.getenv('WEB_SEARCH_ENABLED', 'true').lower() == 'true',
                max_results=int(os.getenv('MAX_SEARCH_RESULTS', '5'))
            ),
            mcp=MCPConfig(
                enabled=os.getenv('MCP_ENABLED', 'true').lower() == 'true',
                servers=mcp_servers
            ),
            server=ServerConfig(
                host=os.getenv('SERVER_HOST', '0.0.0.0'),
                port=int(os.getenv('SERVER_PORT', '8000')),
                debug=os.getenv('DEBUG', 'false').lower() == 'true'
            )
        )

    def validate(self):
        """Validate configuration values"""
        if not self.llm.model_server.startswith(('http://', 'https://')):
            raise ValueError("LLM model server URL must start with http:// or https://")

        if self.llm.temperature < 0 or self.llm.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")

        if self.web.max_results <= 0:
            raise ValueError("Max search results must be positive")

        # Validate MCP configuration
        if self.mcp.enabled:
            for server in self.mcp.servers:
                if not server.name:
                    raise ValueError("MCP server name is required")
                if server.transport_type not in ['stdio', 'sse', 'http']:
                    raise ValueError(f"Invalid MCP transport type: {server.transport_type}")
                if server.transport_type == 'stdio' and not server.command:
                    raise ValueError(f"MCP server {server.name} requires a command for stdio transport")
                if server.transport_type in ['sse', 'http'] and not server.url:
                    raise ValueError(f"MCP server {server.name} requires a URL for {server.transport_type} transport")


# Global config instance
config = Config.from_env()
config.validate()