# 本地控制 MCP Server 快速入门

## 已完成的工作

### 1. 创建的文件

| 文件 | 说明 |
|------|------|
| `servers/local_control_server.py` | 本地控制MCP服务器，提供8个工具 |
| `servers/local_server_requirements.txt` | 依赖包列表 |
| `test_mcp_tools.py` | 工具直接测试脚本（命令行交互） |
| `test_local_agent.py` | 完整Agent测试（使用LM Studio） |

### 2. 可用工具列表

| 工具名 | 功能 | 安全级别 |
|--------|------|----------|
| `get_screenshot` | 截取屏幕截图 | 🟢 安全 |
| `get_system_info` | 获取系统信息 | 🟢 安全 |
| `get_mouse_position` | 获取鼠标位置 | 🟢 安全 |
| `open_app` | 打开白名单应用 | 🟡 中等 |
| `click_at` | 鼠标点击指定坐标 | 🟡 中等 |
| `type_string` | 键盘输入文本 | 🟡 中等 |
| `move_mouse` | 移动鼠标 | 🟡 中等 |
| `kill_process` | 终止白名单进程 | 🔴 受限 |

### 3. 安全设计

- ✅ **禁止任意命令执行** - 没有 `os.system()` 或 `subprocess.run(cmd)`
- ✅ **应用启动白名单** - 只能打开 notepad/calc/mspaint/explorer
- ✅ **进程终止白名单** - 只能终止特定进程
- ✅ **文本输入安全过滤** - 阻止危险命令模式
- ✅ **坐标范围检查** - 防止越界操作

---

## 快速测试

### 方式一：直接测试工具（不需要LLM）

```powershell
cd c:\Users\Wzzz2\OneDrive\Desktop\agent
python test_mcp_tools.py
```

按提示选择要测试的工具（1-9）。

### 方式二：使用LM Studio进行自然语言控制

1. **启动 LM Studio** 并加载 `qwen3-8b-finetuned` 模型
2. **确保服务器运行** 在 `http://127.0.0.1:1234`
3. **运行测试脚本**：

```powershell
cd c:\Users\Wzzz2\OneDrive\Desktop\agent
python test_local_agent.py
```

4. **尝试这些命令**：
   - "请截取当前屏幕"
   - "打开记事本"
   - "查看系统信息"
   - "把鼠标移动到屏幕中间"
   - "关闭记事本"

---

## 下一步：网络穿透（Sakura Frp）

本地测试通过后，可以进行网络穿透设置：

1. 注册 [Sakura Frp](https://www.natfrp.com/) 账号
2. 下载并配置客户端
3. 创建 HTTP 隧道指向本地 MCP Server
4. 更新 Modal Agent 配置使用隧道 URL

需要我帮你配置 Sakura Frp 隧道吗？
