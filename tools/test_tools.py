#!/usr/bin/env python3
"""
测试工具是否可以被系统调用
"""
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tools.utils import find_tool_path, get_tool_command, get_platform_info


def test_tool(tool_name: str) -> dict:
    """测试单个工具"""
    result = {
        "name": tool_name,
        "found": False,
        "path": None,
        "version": None,
        "error": None,
    }
    
    try:
        # 使用工具路径解析函数
        tool_path = find_tool_path(tool_name)
        
        if tool_path:
            result["found"] = True
            result["path"] = str(tool_path)
            
            # 尝试获取版本信息
            try:
                cmd = get_tool_command(tool_name)
                # 大多数工具支持 --version 或 -version
                version_cmd = cmd + ["--version"]
                proc = subprocess.run(
                    version_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    result["version"] = proc.stdout.strip().split("\n")[0]
                else:
                    # 尝试 -version
                    version_cmd = cmd + ["-version"]
                    proc = subprocess.run(
                        version_cmd,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if proc.returncode == 0:
                        result["version"] = proc.stdout.strip().split("\n")[0]
            except Exception as e:
                result["error"] = f"无法获取版本信息: {str(e)}"
        else:
            result["error"] = "工具未找到"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    """主测试函数"""
    tools_to_test = ["nmap", "subfinder", "httpx", "nuclei", "naabu"]
    
    print("=" * 60)
    print("工具调用测试")
    print("=" * 60)
    
    platform_name, arch = get_platform_info()
    print(f"\n当前平台: {platform_name} ({arch})\n")
    
    results = []
    for tool_name in tools_to_test:
        print(f"测试 {tool_name}...", end=" ")
        result = test_tool(tool_name)
        results.append(result)
        
        if result["found"]:
            print("✅ 找到")
            print(f"   路径: {result['path']}")
            if result["version"]:
                print(f"   版本: {result['version']}")
            if result["error"]:
                print(f"   警告: {result['error']}")
        else:
            print("❌ 未找到")
            if result["error"]:
                print(f"   错误: {result['error']}")
        print()
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    found_count = sum(1 for r in results if r["found"])
    total_count = len(results)
    
    print(f"\n找到工具: {found_count}/{total_count}\n")
    
    for result in results:
        status = "✅" if result["found"] else "❌"
        print(f"{status} {result['name']:15} - {result['path'] or result['error']}")
    
    if found_count == total_count:
        print("\n🎉 所有工具都可以正常调用！")
        return 0
    else:
        print(f"\n⚠️  有 {total_count - found_count} 个工具未找到")
        return 1


if __name__ == "__main__":
    sys.exit(main())

