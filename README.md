# ADS Agent - Keysight ADS 自动化助手

基于 Qwen Agent 的 Keysight ADS 2025 电路设计自动化工具。

## 快速开始

### 1. 启动 ADS 服务器
在 ADS Python Console 中运行：
```python
exec(open("C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py").read())
```

### 2. 启动 Agent
```bash
python start_agent.py
```

### 3. 交互测试
```bash
python interactive_debug.py
```

## 使用场景

### 场景一：创建新电路
```
用户: 创建一个RC滤波器
Agent: 调用 plan_circuit → 展示计划
用户: 确认
Agent: 调用 execute_circuit_plan → 创建原理图
Agent: 请在ADS中打开设计 xxx:xxx:schematic
用户: 已打开
Agent: 调用 add_components_from_plan → 添加所有元件
```

### 场景二：在已有cell中设计
```
用户: 在 test_cell 中添加一个电阻
Agent: 请确认 design_uri: MyLibrary3_lib:test_cell:schematic
用户: 确认
Agent: 调用 add_component 添加元件
```

## 项目结构

```
agent/
├── app/                    # 主应用代码
├── ads_plugin/            # ADS 插件
│   └── scripting/
│       ├── boot_standalone.py  # 主服务器
│       └── explore_api.py      # API 探索
├── servers_local/         # MCP 服务器
├── start_agent.py         # 启动入口
└── interactive_debug.py   # 交互测试
```

## 元件库参考

| 元件 | 库名 | Cell 名 |
|-----|------|---------|
| 电阻 | ads_rflib | R |
| 电容 | ads_rflib | C |
| 电感 | ads_rflib | L |
| 接地 | ads_rflib | GROUND |
| 直流电压源 | ads_sources | V_DC |
| 端口 | ads_simulation | Term |
| S参数仿真 | ads_simulation | S_Param |

## 已知限制

- ADS API 不支持获取当前 GUI 中打开的设计
- 需要用户提供 design_uri 或通过 Agent 创建新设计
