# 切换到 API 模型使用指南

## 步骤 1: 安装依赖

```bash
pip install python-dotenv openai
```

## 步骤 2: 选择 API 提供商并获取 API Key

### 推荐选项（按性价比排序）

#### 1. DeepSeek API（最推荐）
- **价格**: ¥1/百万tokens（输入），¥2/百万tokens（输出）
- **效果**: 接近 GPT-4 水平
- **注册**: https://platform.deepseek.com/
- **模型名**: `deepseek-chat`

#### 2. OpenAI API
- **价格**: $0.15/百万tokens（gpt-4o-mini）
- **效果**: 优秀的工具调用能力
- **注册**: https://platform.openai.com/
- **模型名**: `gpt-4o-mini` 或 `gpt-4o`

#### 3. 其他兼容 API
- **Groq**: 免费但有限额，速度极快
- **Together AI**: 多种开源模型
- **Anthropic**: Claude 系列（需要单独适配）

## 步骤 3: 配置 .env 文件

编辑 `.env` 文件，取消注释并填入你的配置：

### 使用 DeepSeek（推荐）
```env
LLM_MODEL=deepseek-chat
LLM_MODEL_SERVER=https://api.deepseek.com/v1
LLM_API_KEY=sk-你的DeepSeek密钥
LLM_TEMPERATURE=0.3
```

### 使用 OpenAI
```env
LLM_MODEL=gpt-4o-mini
LLM_MODEL_SERVER=https://api.openai.com/v1
LLM_API_KEY=sk-你的OpenAI密钥
LLM_TEMPERATURE=0.3
```

### 使用 Groq（免费）
```env
LLM_MODEL=llama-3.3-70b-versatile
LLM_MODEL_SERVER=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_你的Groq密钥
LLM_TEMPERATURE=0.3
```

## 步骤 4: 测试连接

```bash
python test_llm_connection.py
```

如果看到 `✅ LLM API is working correctly!` 说明配置成功！

## 步骤 5: 启动 Agent

```bash
# 终端 1: 启动 MCP Server
python servers_local/ads_server.py

# 终端 2: 启动 Agent
python start_agent.py

# 终端 3: 测试
python interactive_debug.py
```

## 常见问题

### Q: 提示 "openai package not installed"
A: 运行 `pip install openai`

### Q: 提示 "API key is invalid"
A: 检查 `.env` 文件中的 API key 是否正确复制

### Q: 连接超时
A: 检查网络连接，确保可以访问 API 服务器

### Q: 如何切换回本地模型？
A: 修改 `.env` 文件，使用本地配置：
```env
LLM_MODEL=qwen3-8b-finetuned
LLM_MODEL_SERVER=http://127.0.0.1:1234/v1
LLM_API_KEY=EMPTY
LLM_TEMPERATURE=0.3
```

## 性能对比

| 模型 | 推理速度 | 工具调用准确度 | 自然语言质量 | 成本 |
|------|---------|---------------|-------------|------|
| 本地 Q4-8B | 快 | ⭐⭐ | ⭐⭐ | 免费 |
| DeepSeek | 中等 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 极低 |
| GPT-4o-mini | 快 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 |
| GPT-4o | 中等 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中等 |

## 预期改进

切换到 API 模型后，您应该看到：

✅ 模型能正确理解自然语言指令
✅ 不再重复调用相同工具
✅ 返回自然流畅的中文回复
✅ 正确执行多步骤工作流
✅ 不再泄漏内部指令或 JSON 格式
