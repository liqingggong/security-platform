"""
工具路径解析工具
根据当前平台和架构自动选择正确的工具路径
"""
import platform
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings


def get_platform_info() -> tuple[str, str]:
    """
    获取当前平台和架构信息
    
    Returns:
        (platform_name, architecture): 例如 ('linux', 'x86_64') 或 ('darwin', 'arm64')
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # 标准化平台名称
    if system == "linux":
        platform_name = "linux"
    elif system == "darwin":
        platform_name = "darwin"
    elif system == "windows":
        platform_name = "windows"
    else:
        platform_name = system
    
    # 标准化架构名称
    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("arm", "armv7l"):
        arch = "arm"
    else:
        arch = machine
    
    return platform_name, arch


def find_tool_path(tool_name: str, custom_path: Optional[str] = None) -> Optional[Path]:
    """
    查找工具的完整路径
    
    优先级：
    1. 自定义路径（用户上传的工具）
    2. 内置工具目录（根据平台和架构）
    3. 系统 PATH
    
    Args:
        tool_name: 工具名称（如 'nmap', 'subfinder'）
        custom_path: 自定义工具路径（相对于 tools/plugins/）
    
    Returns:
        工具的完整路径，如果找不到则返回 None
    """
    base_dir = settings.BASE_DIR
    platform_name, arch = get_platform_info()
    
    # 1. 优先使用自定义路径（用户上传的工具）
    if custom_path:
        custom_full_path = base_dir / "tools" / "plugins" / custom_path
        if custom_full_path.exists() and custom_full_path.is_file():
            return custom_full_path
    
    # 2. 查找内置工具目录
    builtin_path = base_dir / "tools" / "builtin" / platform_name / arch / tool_name
    if builtin_path.exists() and builtin_path.is_file():
        return builtin_path
    
    # Windows 需要 .exe 扩展名
    if platform_name == "windows":
        builtin_path_exe = builtin_path.with_suffix(".exe")
        if builtin_path_exe.exists() and builtin_path_exe.is_file():
            return builtin_path_exe
    
    # 3. 尝试系统 PATH（使用 shutil.which）
    import shutil
    system_tool = shutil.which(tool_name)
    if system_tool:
        return Path(system_tool)
    
    return None


def get_tool_command(tool_name: str, custom_path: Optional[str] = None) -> list[str]:
    """
    获取工具的执行命令
    
    Args:
        tool_name: 工具名称
        custom_path: 自定义工具路径
    
    Returns:
        命令列表，例如 ['/path/to/nmap', ...] 或 ['nmap', ...]
    """
    tool_path = find_tool_path(tool_name, custom_path)
    
    if tool_path:
        return [str(tool_path)]
    else:
        # 如果找不到，返回工具名称（假设在系统 PATH 中）
        return [tool_name]


def ensure_builtin_tools_dir() -> Path:
    """
    确保内置工具目录存在
    
    Returns:
        当前平台和架构对应的内置工具目录路径
    """
    platform_name, arch = get_platform_info()
    builtin_dir = settings.BASE_DIR / "tools" / "builtin" / platform_name / arch
    builtin_dir.mkdir(parents=True, exist_ok=True)
    return builtin_dir

