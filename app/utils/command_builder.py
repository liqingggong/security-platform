"""
命令构建工具
支持从命令模板和变量构建最终的命令
"""
from typing import Dict, Any, List, Optional
import shlex


def build_command(
    command_template: Optional[str],
    variables: Dict[str, Any],
    tool_name: Optional[str] = None,
) -> List[str]:
    """
    根据命令模板和变量构建命令
    
    Args:
        command_template: 命令模板，例如 "nmap -sV -p {ports} {targets}"
        variables: 变量字典，例如 {"ports": "80,443", "targets": "1.1.1.1"}
        tool_name: 工具名称，如果模板为空则使用默认命令
    
    Returns:
        命令列表，例如 ["nmap", "-sV", "-p", "80,443", "1.1.1.1"]
    """
    # 如果没有模板，使用默认命令
    if not command_template:
        if tool_name:
            return [tool_name]
        return []
    
    # 替换变量
    command_str = command_template
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        if placeholder in command_str:
            # 将值转换为字符串
            if isinstance(value, list):
                # 如果是列表，转换为空格分隔的字符串
                value_str = " ".join(str(v) for v in value)
            else:
                value_str = str(value)
            command_str = command_str.replace(placeholder, value_str)
    
    # 使用 shlex.split 安全地分割命令（处理引号等）
    try:
        return shlex.split(command_str)
    except ValueError:
        # 如果 shlex.split 失败，使用简单的空格分割
        return command_str.split()


def get_tool_command_from_config(
    tool_name: str,
    tool_config: Optional[Dict[str, Any]] = None,
    plan_tool_config: Optional[Dict[str, Any]] = None,
    default_template: Optional[str] = None,
) -> Optional[str]:
    """
    从配置中获取工具命令模板
    
    优先级：
    1. 扫描方案中的工具配置（plan_tool_config.command_template）
    2. 工具配置（tool_config.command_template）
    3. 默认模板（default_template）
    
    Args:
        tool_name: 工具名称
        tool_config: 工具配置（从数据库 Tool 表）
        plan_tool_config: 扫描方案中的工具配置（从 ScanPlanTool.config）
        default_template: 默认模板（硬编码的默认值）
    
    Returns:
        命令模板字符串，如果都没有则返回 None
    """
    # 优先级1: 扫描方案中的配置
    if plan_tool_config and plan_tool_config.get("command_template"):
        return plan_tool_config["command_template"]
    
    # 优先级2: 工具配置
    if tool_config and tool_config.get("command_template"):
        return tool_config["command_template"]
    
    # 优先级3: 默认模板
    if default_template:
        return default_template
    
    return None

