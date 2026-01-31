# SiliconFlow API 配置示例

## 正确的配置格式

```env
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
LLM_MODEL_SERVER=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-你的密钥
LLM_TEMPERATURE=0.3
```

## 常见错误

❌ **错误 1**: URL 包含 `/chat/completions`
```env
LLM_MODEL_SERVER=https://api.siliconflow.cn/v1/chat/completions  # 错误！
```

✅ **正确**: 只到 `/v1`
```env
LLM_MODEL_SERVER=https://api.siliconflow.cn/v1  # 正确
```

❌ **错误 2**: 模型名称不正确
```env
LLM_MODEL=Qwen3-8B  # 错误！
```

✅ **正确**: 使用完整的模型路径
```env
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct  # 正确
```

## SiliconFlow 可用模型

推荐用于工具调用的模型：

1. **Qwen/Qwen2.5-7B-Instruct** (推荐)
   - 7B 参数，工具调用能力强
   - 速度快，成本低

2. **Qwen/Qwen2.5-14B-Instruct**
   - 14B 参数，更强的推理能力
   - 稍慢但效果更好

3. **deepseek-ai/DeepSeek-V2.5**
   - 强大的推理能力
   - 适合复杂任务

4. **meta-llama/Meta-Llama-3.1-8B-Instruct**
   - Meta 的开源模型
   - 工具调用能力不错

## 查看可用模型

访问 SiliconFlow 控制台查看完整模型列表：
https://cloud.siliconflow.cn/models

## 测试连接

配置完成后运行：
```bash
python test_llm_connection.py
```

应该看到类似输出：
```
[Info] Corrected base_url to: https://api.siliconflow.cn/v1
✅ Connection successful!
Model response:
我是来自阿里云的大规模语言模型，我叫通义千问。
```
