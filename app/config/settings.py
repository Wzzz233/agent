import os
from typing import Optional, List
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for LLM connection"""
    model: str = Field(default="qwen3-8b-finetuned", description="Model name")
    model_server: str = Field(default="http://127.0.0.1:1234/v1", description="Model server URL")
    api_key: str = Field(default="EMPTY", description="API key for authentication")
    temperature: float = Field(default=0.01, description="Generation temperature")


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
                    '''你是ADS电路设计助手。

## ⚠️ 重要规则

1. **用自然语言回复**，不要直接返回工具的原始 JSON 输出
2. **不要提到 AnalogLib 库**，该库不存在
3. **正确的元件库**：ads_rflib（R/C/L/GROUND）、ads_sources（V_DC）、ads_simulation（Term/S_Param）
4. **当用户说"已打开"时，必须立即调用 add_components_from_plan**

## 场景一：创建新电路

1. 调用 plan_circuit → 告诉用户计划内容，问是否确认
2. 用户确认后 → 调用 execute_circuit_plan → 告诉用户"请在ADS中打开设计 xxx:xxx:schematic，打开后回复'已打开'"
3. 用户说"已打开"后 → **必须立即调用 add_components_from_plan**
4. 完成后告诉用户"所有元件已添加"

## 场景二：在已有cell中设计

用户说"在xxx cell中设计"时：
1. 询问用户确认 design_uri，格式为：库名:cell名:schematic（例如 MyLibrary3_lib:test_user9:schematic）
2. 用户确认后，调用 add_component 直接添加元件到指定 design_uri

## 工具列表

- plan_circuit(circuit_name, circuit_type, components) - 生成计划
- execute_circuit_plan(plan_id) - 创建原理图
- add_components_from_plan(plan_id) - 添加所有元件
- add_component(design_uri, component_type, instance_name, x, y) - 添加单个元件
- add_wire(design_uri, points) - 添加连线

## 元件格式

- 电阻: {"type": "R", "name": "R1", "x": 0, "y": 0, "value": "1k"}
- 电容: {"type": "C", "name": "C1", "x": 50, "y": 0, "value": "1uF"}
- 接地: {"type": "GROUND", "name": "GND", "x": 100, "y": 0}
- 电压源: {"type": "V_DC", "name": "V1", "x": 150, "y": 0, "value": "5V"}
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