"""
测试 LLM API 连接
用于验证配置是否正确
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import config

def test_llm_connection():
    """Test LLM API connection"""
    print("=" * 60)
    print("LLM Configuration Test")
    print("=" * 60)
    
    print(f"\nModel: {config.llm.model}")
    print(f"Server: {config.llm.model_server}")
    print(f"API Key: {config.llm.api_key[:10]}..." if config.llm.api_key and config.llm.api_key != "EMPTY" else "API Key: Not set")
    print(f"Temperature: {config.llm.temperature}")
    
    # Fix common URL issues
    base_url = config.llm.model_server
    
    # Remove trailing /chat/completions if present (OpenAI SDK adds it automatically)
    if base_url.endswith('/chat/completions'):
        base_url = base_url.replace('/chat/completions', '')
        print(f"\n[Info] Corrected base_url to: {base_url}")
    
    # Ensure it ends with /v1 for most providers
    if not base_url.endswith('/v1') and 'siliconflow' in base_url:
        if not base_url.endswith('/'):
            base_url += '/v1'
        else:
            base_url += 'v1'
        print(f"[Info] Corrected base_url to: {base_url}")
    
    print("\n" + "=" * 60)
    print("Testing API Connection...")
    print("=" * 60)
    
    try:
        import openai
        
        # Create client
        client = openai.OpenAI(
            api_key=config.llm.api_key,
            base_url=base_url
        )
        
        # Test simple completion
        print("\nSending test message: '你好，请介绍一下你自己'")
        
        response = client.chat.completions.create(
            model=config.llm.model,
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍一下你自己"}
            ],
            temperature=config.llm.temperature,
            max_tokens=100
        )
        
        reply = response.choices[0].message.content
        print(f"\n✅ Connection successful!")
        print(f"\nModel response:\n{reply}")
        
        print("\n" + "=" * 60)
        print("✅ LLM API is working correctly!")
        print("=" * 60)
        
        return True
        
    except ImportError:
        print("\n❌ Error: openai package not installed")
        print("Install with: pip install openai")
        return False
        
    except openai.AuthenticationError as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\nPlease check your API key is correct")
        return False
        
    except openai.NotFoundError as e:
        print(f"\n❌ Model or endpoint not found: {e}")
        print("\nPossible issues:")
        print(f"1. Model name '{config.llm.model}' may be incorrect")
        print(f"2. Base URL '{base_url}' may be incorrect")
        print("\nFor SiliconFlow, use:")
        print("   - Base URL: https://api.siliconflow.cn/v1")
        print("   - Model: Qwen/Qwen2.5-7B-Instruct (or other available models)")
        return False
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        print("\nPlease check:")
        print("1. API key is correct")
        print("2. Model server URL is correct")
        print("3. Model name is correct")
        print("4. You have internet connection (if using cloud API)")
        return False

if __name__ == "__main__":
    success = test_llm_connection()
    sys.exit(0 if success else 1)
