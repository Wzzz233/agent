"""
快速检查 ADS 连接状态
"""
import sys
import os

# Add ads_plugin to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ads_plugin'))

from ads_client import get_ads_client


def test_ads():
    print("=" * 60)
    print("ADS 连接测试")
    print("=" * 60)
    
    client = get_ads_client()
    
    if not client:
        print("\n❌ ADS Client 不可用!")
        print("\n请确保:")
        print("1. ADS 2025 正在运行")
        print("2. 在 ADS Python Console 中运行了 boot_standalone.py")
        print("   - 打开 ADS -> Tools -> Command Line -> Python")
        print("   - 输入: exec(open(r'C:\\path\\to\\boot_standalone.py').read())")
        return False
    
    print("\n✅ ADS Client 已连接!")
    
    # Test get_project_structure
    print("\n测试 get_project_structure...")
    try:
        result = client._send_command('get_project_structure', {})
        print(f"结果: {result}")
        
        libraries = result.get('data', {}).get('libraries', [])
        if libraries:
            print(f"\n✅ 发现 {len(libraries)} 个库:")
            for lib in libraries:
                print(f"  - {lib.get('name', 'unknown')}")
        else:
            print("\n⚠️ 没有发现任何库")
            print("\n可能的原因:")
            print("1. ADS 中没有打开项目")
            print("2. 项目中没有创建库")
            print("3. Automation Server 需要重新启动")
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_ads()
