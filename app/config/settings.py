import os
from typing import Optional
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
    server: ServerConfig = ServerConfig()

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
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
                    '你是一个太赫兹实验助手。收到操作指令时，可以调用激光控制工具或网络搜索工具获取信息。重要提示：每个问题最多只搜索一次，如果搜索无结果，请基于已有知识回答，不要重复搜索。使用英文关键词搜索效果更好。'
                )
            ),
            web=WebConfig(
                search_enabled=os.getenv('WEB_SEARCH_ENABLED', 'true').lower() == 'true',
                max_results=int(os.getenv('MAX_SEARCH_RESULTS', '5'))
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


# Global config instance
config = Config.from_env()
config.validate()