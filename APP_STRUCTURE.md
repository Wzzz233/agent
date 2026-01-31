# App 目录结构详解

## 目录树

```
app/
├── main.py                      # FastAPI 应用入口
├── config/                      # 配置管理
│   └── settings.py             # 应用配置（LLM、Web搜索、MCP等）
├── agents/                      # Agent 核心逻辑 ⭐核心
│   ├── control_layer.py        # 【新增】控制层 - 物理熔断
│   ├── tool_wrapper.py         # 【新增】工具包装层 - 双重视图
│   ├── adapter_layer.py        # 【新增】适配器层 - 动态提示注入
│   ├── services/               # Agent 服务
│   │   └── agent_service.py   # Agent 主逻辑、执行循环
│   ├── adapters/               # LLM 适配器
│   │   └── qwen_adapter.py    # Qwen 模型适配器
│   ├── base_agent.py          # Agent 基类
│   └── thz_agent.py           # THz 专用 Agent
├── mcp/                         # MCP 客户端 ⭐核心
│   ├── client.py               # MCP 客户端管理器
│   ├── protocol.py             # MCP 协议定义
│   ├── handlers/               # MCP 处理器
│   │   └── agent_handler.py   # Agent 消息处理
│   └── transport/              # MCP 传输层
│       └── http_transport.py  # HTTP 传输
├── tools/                       # 工具层
│   ├── base_tool.py            # 工具基类
│   ├── web_search_tool.py      # Web 搜索工具
│   ├── mock_laser_control.py   # 激光控制模拟工具
│   ├── registry.py             # 工具注册表
│   └── tool_factory.py         # 工具工厂
├── api/                         # FastAPI 路由
│   ├── routes/
│   │   ├── agent_routes.py     # Agent 消息接口
│   │   └── tool_routes.py      # 工具管理接口
│   └── middleware/
│       └── cors.py             # CORS 中间件
└── utils/                       # 工具函数
    ├── logger.py               # 日志工具
    └── validators.py           # 验证器
```

## 各模块详细说明

### 1. **main.py** - 应用入口
**作用**：FastAPI 应用的启动点

```python
# 主要功能：
- 创建 FastAPI 应用实例
- 注册路由（agent_routes, tool_routes）
- 配置中间件（CORS）
- 启动 MCP 服务器连接
- 启动 uvicorn 服务器
```

---

### 2. **config/settings.py** - 配置中心
**作用**：集中管理所有配置项

```python
# 配置项包括：
class Config(BaseModel):
    # LLM 配置
    llm: LLMConfig  # 模型、API地址、密钥、温度
    
    # Web 搜索配置
    web: WebConfig  # 是否启用、搜索API
    
    # MCP 配置
    mcp: MCPConfig  # 服务器列表、传输类型
    
    # 其他配置
    debug: bool
    log_level: str
```

---

### 3. **agents/** - Agent 核心模块 ⭐⭐⭐

#### 3.1 **services/agent_service.py** - Agent 服务层
**作用**：Agent 的主逻辑和执行循环

```python
class AgentService:
    # 核心功能：
    1. 初始化 Agent 和工具
    2. 管理消息历史
    3. 执行 Agent 循环（max_turns=10）
    4. 解析工具调用（XML 格式）
    5. 集成 ControlLayer 进行终止检测
    6. 处理工具返回结果
    
    # 关键方法：
    - process_message_async()  # 处理用户消息
    - run_agent_worker()       # 执行循环
```

#### 3.2 **control_layer.py** - 【新增】控制层 ⭐⭐⭐
**作用**：物理熔断机制，防止无限循环

```python
class ControlLayer:
    # 核心功能：
    1. 终止动作检测
    2. 无限循环检测（相同工具调用3次）
    3. 工具调用限制（总计15次，单个5次）
    4. 生成终止消息
    
    # 关键配置：
    TERMINATION_ACTIONS = {
        "add_components_from_plan",  # 任务完成
        "execute_circuit_plan",      # 等待用户打开
    }
    
    CONFIRMATION_REQUIRED_ACTIONS = {
        "plan_circuit",              # 需要用户确认
    }
```

#### 3.3 **tool_wrapper.py** - 【新增】工具包装层 ⭐⭐⭐
**作用**：双重视图，防止 JSON 泄漏

```python
class ToolResult:
    # 包装工具返回值：
    {
        "status": "success|error",     # 机器可读状态
        "summary": "✅ 操作成功",       # 人类可读摘要
        "instruction": "下一步提示",    # 操作指引
        "data": {...}                  # 原始数据
    }
    
    # 特殊包装器：
    - _wrap_get_current_design_result()  # 场景判断 ⭐关键
    - _wrap_add_components_result()      # 任务完成提示
    - _wrap_check_cell_exists_result()   # 错误引导
```

#### 3.4 **adapter_layer.py** - 【新增】适配器层 ⭐⭐⭐
**作用**：动态提示注入，引导模型决策

```python
class AdapterLayer:
    # 核心功能：
    1. 在工具描述中注入约束
    2. 添加决策引导（先调用 get_current_design）
    3. 添加警告（不要重复调用工具）
    
    # 关键配置：
    DISCOVERY_TOOLS = {
        "get_current_design": "CRITICAL: 先调用此工具判断场景"
    }
    
    DECISION_GUIDANCE = {
        "workflow_selection": 
            "1) 调用 get_current_design
             2) 如果有设计打开 → 直接设计
             3) 如果没有 → 询问用户"
    }
```

#### 3.5 **adapters/qwen_adapter.py** - LLM 适配器
**作用**：将 MCP 工具转换为 Qwen 格式

```python
# 核心功能：
1. 工具格式转换（MCP → Qwen）
2. 全局调用计数器（防止无限循环）
3. 集成 tool_wrapper 和 adapter_layer
4. 代理工具调用到 MCP 客户端

class MCPProxyTool(BaseTool):
    def call(params):
        # 1. 检查调用次数限制
        # 2. 调用 MCP 工具
        # 3. 包装返回值
        # 4. 返回结果
```

---

### 4. **mcp/** - MCP 客户端模块 ⭐⭐⭐

#### 4.1 **client.py** - MCP 客户端管理器
**作用**：管理 MCP 服务器连接和工具调用

```python
class MCPClientManager:
    # 核心功能：
    1. 连接多个 MCP 服务器（stdio、HTTP）
    2. 发现和注册工具
    3. 路由工具调用到对应服务器
    4. 提供同步/异步调用接口
    
    # 关键方法：
    - connect_all()              # 连接所有服务器
    - list_tools()               # 列出所有工具
    - call_tool(name, args)      # 调用工具
    - call_tool_sync()           # 同步调用
```

#### 4.2 **protocol.py** - MCP 协议定义
**作用**：定义 MCP 协议的数据结构

```python
# 定义：
- JSON-RPC 消息格式
- 工具定义（Tool、InputSchema）
- 资源定义（Resource）
- 提示定义（Prompt）
```

#### 4.3 **handlers/agent_handler.py** - Agent 消息处理
**作用**：处理 Agent 与 MCP 之间的消息

#### 4.4 **transport/** - 传输层
**作用**：实现不同的传输协议

```python
- stdio_client:    标准输入输出通信（本地）
- http_transport:  HTTP 通信（远程）
```

---

### 5. **tools/** - 工具模块

#### 5.1 **base_tool.py** - 工具基类
**作用**：定义工具的统一接口

```python
class BaseTool(ABC):
    @abstractmethod
    def call(params: str) -> str:
        """工具调用接口"""
```

#### 5.2 **web_search_tool.py** - Web 搜索工具
**作用**：提供网络搜索能力

#### 5.3 **mock_laser_control.py** - 激光控制模拟工具
**作用**：模拟激光设备控制（测试用）

#### 5.4 **registry.py** - 工具注册表
**作用**：管理所有可用工具

#### 5.5 **tool_factory.py** - 工具工厂
**作用**：动态创建工具实例

---

### 6. **api/** - API 路由模块

#### 6.1 **routes/agent_routes.py** - Agent 路由
**作用**：提供 Agent 消息接口

```python
@router.post("/message")
async def send_message(message: str):
    """发送消息给 Agent"""
    
@router.post("/reset")
async def reset_conversation():
    """重置对话"""
```

#### 6.2 **routes/tool_routes.py** - 工具路由
**作用**：提供工具管理接口

```python
@router.get("/list")
async def list_tools():
    """列出所有工具"""
```

#### 6.3 **middleware/cors.py** - CORS 中间件
**作用**：处理跨域请求

---

### 7. **utils/** - 工具函数

#### 7.1 **logger.py** - 日志工具
**作用**：统一日志格式和输出

#### 7.2 **validators.py** - 验证器
**作用**：输入参数验证

---

## 核心流程图

```
用户请求
  ↓
[main.py] FastAPI 接收
  ↓
[api/routes/agent_routes.py] /agent/message
  ↓
[agents/services/agent_service.py] process_message_async()
  ↓
[agents/control_layer.py] 初始化控制层
  ↓
[agents/adapters/qwen_adapter.py] 转换工具格式
  ↓
[agents/adapter_layer.py] 注入动态提示
  ↓
LLM 决策（调用 get_current_design）
  ↓
[mcp/client.py] call_tool_sync()
  ↓
[servers_local/ads_server.py] 执行工具
  ↓
[agents/tool_wrapper.py] 包装结果
  ↓
[agents/control_layer.py] 检测是否需要终止
  ↓
返回给用户
```

## 总结

| 模块 | 文件数 | 作用 | 重要性 |
|------|--------|------|--------|
| **agents/** | 9 | Agent 核心逻辑 | ⭐⭐⭐ |
| **mcp/** | 6 | MCP 客户端 | ⭐⭐⭐ |
| **api/** | 5 | Web 接口 | ⭐⭐ |
| **tools/** | 5 | 工具实现 | ⭐⭐ |
| **config/** | 2 | 配置管理 | ⭐ |
| **utils/** | 2 | 工具函数 | ⭐ |

**最核心的文件**：
1. `agent_service.py` - Agent 主逻辑
2. `control_layer.py` - 控制层（新增）
3. `tool_wrapper.py` - 工具包装（新增）
4. `adapter_layer.py` - 适配器层（新增）
5. `qwen_adapter.py` - LLM 适配器
6. `client.py` - MCP 客户端
