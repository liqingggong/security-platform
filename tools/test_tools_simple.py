#!/usr/bin/env python3
"""
简单测试工具是否可以被系统调用（不依赖项目模块）
"""
import subprocess
import shutil
import platform


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
        # 使用 shutil.which 查找工具路径
        tool_path = shutil.which(tool_name)
        
        if tool_path:
            result["found"] = True
            result["path"] = tool_path
            
            # 尝试获取版本信息
            try:
                # 大多数工具支持 --version 或 -version
                for version_flag in ["--version", "-version", "-v"]:
                    try:
                        proc = subprocess.run(
                            [tool_name, version_flag],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if proc.returncode == 0:
                            # 提取第一行作为版本信息
                            version_line = proc.stdout.strip().split("\n")[0]
                            if version_line:
                                result["version"] = version_line
                                break
                    except:
                        continue
                
                # 如果还是没获取到版本，尝试直接运行工具（不带参数）
                if not result["version"]:
                    try:
                        proc = subprocess.run(
                            [tool_name],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        # 有些工具不带参数会显示版本或帮助信息
                        if proc.stdout:
                            first_line = proc.stdout.strip().split("\n")[0]
                            if "version" in first_line.lower() or tool_name.lower() in first_line.lower():
                                result["version"] = first_line
                    except:
                        pass
                        
            except Exception as e:
                result["error"] = f"无法获取版本信息: {str(e)}"
        else:
            result["error"] = "工具未在系统 PATH 中找到"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    """主测试函数"""
    tools_to_test = ["nmap", "subfinder", "httpx", "nuclei", "naabu"]
    
    print("=" * 70)
    print("工具调用测试")
    print("=" * 70)
    
    system = platform.system()
    machine = platform.machine()
    print(f"\n当前平台: {system} ({machine})\n")
    
    results = []
    for tool_name in tools_to_test:
        print(f"测试 {tool_name:12}...", end=" ")
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
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    
    found_count = sum(1 for r in results if r["found"])
    total_count = len(results)
    
    print(f"\n找到工具: {found_count}/{total_count}\n")
    
    for result in results:
        status = "✅" if result["found"] else "❌"
        info = result['path'] if result['path'] else result['error']
        print(f"{status} {result['name']:15} - {info}")
    
    print("\n" + "=" * 70)
    
    if found_count == total_count:
        print("🎉 所有工具都可以正常调用！")
        return 0
    else:
        print(f"⚠️  有 {total_count - found_count} 个工具未找到")
        print("\n提示：")
        print("1. 确保工具已安装并在系统 PATH 中")
        print("2. 可以使用 'which <tool_name>' 命令检查工具路径")
        print("3. 如果使用项目目录安装，需要确保文件有执行权限")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

