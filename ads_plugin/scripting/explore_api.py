"""
ADS API Explorer Script

在 ADS Python Console 中运行此脚本，可以发现所有可用的 API 函数。

使用方法:
exec(open("C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/explore_api.py").read())
"""

import sys

def explore_ads_api():
    """探索 keysight.ads.de 模块的可用 API"""
    
    print("=" * 70)
    print("ADS API Explorer")
    print("=" * 70)
    
    # 导入模块
    try:
        import keysight.ads.de as de
        from keysight.ads.de import db_uu
        print("[OK] keysight.ads.de 模块已导入")
    except ImportError as e:
        print(f"[ERROR] 无法导入 keysight.ads.de: {e}")
        return
    
    print("\n" + "=" * 70)
    print("1. keysight.ads.de 模块中的所有公开函数/属性")
    print("=" * 70)
    
    de_members = [m for m in dir(de) if not m.startswith('_')]
    for i, member in enumerate(de_members, 1):
        obj = getattr(de, member, None)
        obj_type = type(obj).__name__
        print(f"  {i:3}. {member:40} ({obj_type})")
    
    print("\n" + "=" * 70)
    print("2. 与 'design' 相关的函数")
    print("=" * 70)
    
    design_funcs = [m for m in de_members if 'design' in m.lower()]
    for func_name in design_funcs:
        func = getattr(de, func_name, None)
        print(f"  - de.{func_name}")
        if hasattr(func, '__doc__') and func.__doc__:
            doc = func.__doc__.strip().split('\n')[0][:60]
            print(f"    说明: {doc}")
    
    print("\n" + "=" * 70)
    print("3. 与 'active' 或 'current' 相关的函数")
    print("=" * 70)
    
    active_funcs = [m for m in de_members if 'active' in m.lower() or 'current' in m.lower()]
    for func_name in active_funcs:
        func = getattr(de, func_name, None)
        print(f"  - de.{func_name}")
        # 尝试调用
        if callable(func):
            try:
                result = func()
                print(f"    调用结果: {result}")
            except Exception as e:
                print(f"    调用失败: {e}")
    
    print("\n" + "=" * 70)
    print("4. db_uu 模块中的函数")
    print("=" * 70)
    
    dbuu_members = [m for m in dir(db_uu) if not m.startswith('_')]
    for member in dbuu_members[:20]:  # 只显示前20个
        print(f"  - db_uu.{member}")
    if len(dbuu_members) > 20:
        print(f"  ... 还有 {len(dbuu_members) - 20} 个")
    
    print("\n" + "=" * 70)
    print("5. 测试获取当前工作区和库")
    print("=" * 70)
    
    try:
        ws = de.active_workspace() if hasattr(de, 'active_workspace') else None
        print(f"  active_workspace(): {ws}")
    except Exception as e:
        print(f"  active_workspace() 失败: {e}")
    
    try:
        libs = de.get_open_writable_library_names() if hasattr(de, 'get_open_writable_library_names') else None
        print(f"  get_open_writable_library_names(): {libs}")
    except Exception as e:
        print(f"  get_open_writable_library_names() 失败: {e}")
    
    print("\n" + "=" * 70)
    print("6. 测试获取当前设计")
    print("=" * 70)
    
    # 尝试各种方法获取当前设计
    methods_to_try = [
        'active_design',
        'get_active_design', 
        'current_design',
        'get_current_design',
        'active_schematic',
        'get_active_schematic',
        'get_active_cellview',
        'active_cellview',
    ]
    
    for method_name in methods_to_try:
        if hasattr(de, method_name):
            func = getattr(de, method_name)
            if callable(func):
                try:
                    result = func()
                    print(f"  de.{method_name}() = {result}")
                    if result is not None:
                        print(f"    类型: {type(result)}")
                        # 尝试获取设计的属性
                        if hasattr(result, 'name'):
                            print(f"    name: {result.name()}")
                except Exception as e:
                    print(f"  de.{method_name}() 失败: {e}")
    
    print("\n" + "=" * 70)
    print("7. 如果已打开设计，测试 design 对象的属性")
    print("=" * 70)
    
    # 尝试用已知的 design_uri 打开设计
    try:
        libs = de.get_open_writable_library_names()
        if libs:
            lib_name = list(libs)[0]
            print(f"  使用库: {lib_name}")
            lib = de.get_open_library(lib_name)
            if lib and hasattr(lib, 'cells'):
                cells = list(lib.cells)
                if cells:
                    cell = cells[0]
                    design_uri = f"{lib_name}:{cell.name}:schematic"
                    print(f"  尝试打开: {design_uri}")
                    
                    design = db_uu.open_design(design_uri)
                    if design:
                        print(f"  设计对象: {design}")
                        print(f"  设计属性:")
                        design_attrs = [a for a in dir(design) if not a.startswith('_')]
                        for attr in design_attrs[:15]:
                            print(f"    - {attr}")
                        if len(design_attrs) > 15:
                            print(f"    ... 还有 {len(design_attrs) - 15} 个")
    except Exception as e:
        print(f"  测试失败: {e}")
    
    print("\n" + "=" * 70)
    print("探索完成！请将以上输出分享给开发者以修复 API 调用。")
    print("=" * 70)


# 自动运行
explore_ads_api()
