# Keysight ADS Python API 参考手册 (Live Automation Mode)

## ⚠️ 重要：工作模式变更

本系统现已升级为 **Live Automation Mode**（实时自动化模式）。
Agent 可以直接控制 ADS，无需用户手动运行脚本。

---

## 🔌 连接要求

在使用自动化功能前，确保：

1. **ADS 2025** 已打开并加载了工作区
2. **Socket 服务器** 已在 ADS Python Console 中启动：
   ```python
   exec(open("C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py").read())
   ```
3. 服务器正在 `localhost:5000` 监听

---

## 📋 Agent 工作流程

### 标准流程（推荐）

1. **检查连接**：调用 `check_connection` 确认 ADS 服务器可用
2. **获取项目结构**：调用 `get_project_structure` 了解可用库
3. **生成计划**：调用 `plan_circuit` 生成电路创建计划
4. **等待确认**：将计划返回给用户确认
5. **执行计划**：用户确认后调用 `execute_circuit_plan` 执行

### 直接操作（高级）

对于简单操作，可以直接调用：
- `create_schematic` - 创建原理图
- `add_component` - 添加元件
- `save_current_design` - 保存设计

---

## 🛠️ 可用工具

### check_connection
检查 ADS 服务器连接状态。

### get_project_structure
获取工作区路径和可用库列表。

### plan_circuit
生成电路计划，等待用户确认。

参数：
- `circuit_name`: 电路名称
- `circuit_type`: 电路类型
- `components`: 元件列表
- `library_name`: 目标库（可选）
- `description`: 描述（可选）

### execute_circuit_plan
执行已确认的计划。

参数：
- `plan_id`: 计划 ID

### add_component
直接添加元件。

参数：
- `design_uri`: 设计 URI
- `component_type`: 元件类型
- `instance_name`: 实例名称
- `x, y`: 坐标
- `component_lib`: 元件库
- `angle`: 旋转角度

---

## 🔧 元件参考

| 类型 | 库 | 说明 |
|------|-----|------|
| R | ads_rflib | 电阻 |
| C | ads_rflib | 电容 |
| L | ads_rflib | 电感 |
| GROUND | ads_rflib | 接地 |
| V_DC | ads_sources | 直流电压源 |
| V_AC | ads_sources | 交流电压源 |
| I_DC | ads_sources | 直流电流源 |
| Term | ads_simulation | 端口 |
| S_Param | ads_simulation | S参数仿真 |
| DC | ads_simulation | 直流仿真 |

---

## 📐 坐标建议

- X 范围：0 ~ 500
- Y 范围：0 ~ 500
- 元件间距：50 ~ 100

---

## 💡 对话示例

**用户**: 帮我创建一个简单的 RC 滤波器

**Agent**:
1. 首先检查连接 → 调用 `check_connection`
2. 获取可用库 → 调用 `get_project_structure`
3. 生成计划：
```python
plan_circuit(
    circuit_name="rc_filter",
    circuit_type="low_pass_filter",
    components=[
        {"type": "Term", "name": "Port1", "x": 0, "y": 100},
        {"type": "R", "name": "R1", "x": 100, "y": 100, "value": "50 Ohm"},
        {"type": "C", "name": "C1", "x": 200, "y": 50, "value": "10 pF"},
        {"type": "Ground", "name": "GND1", "x": 200, "y": 0},
        {"type": "Term", "name": "Port2", "x": 300, "y": 100}
    ]
)
```
4. 返回计划给用户确认
5. 用户确认后 → 调用 `execute_circuit_plan`