"""
MCP Tool Converter - Convert MCP tools to OpenAI function calling format

This module handles the conversion of MCP tool definitions to standard
OpenAI JSON Schema format, and creates proxy tool instances.
"""
from typing import Dict, Any, List
from app.tools.base_tool import BaseTool, MCPProxyTool


def mcp_schema_to_openai(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP input schema to OpenAI parameters format.
    
    MCP uses JSON Schema, which is directly compatible with OpenAI.
    This function just ensures the format is correct.
    
    Args:
        input_schema: MCP input schema (JSON Schema format)
        
    Returns:
        OpenAI parameters schema
    """
    # MCP already uses JSON Schema, so we mostly pass through
    # Just ensure required fields exist
    schema = {
        "type": input_schema.get("type", "object"),
        "properties": input_schema.get("properties", {}),
    }
    
    # Include required if present
    if "required" in input_schema:
        schema["required"] = input_schema["required"]
    
    # Include additional properties if present
    for key in ["additionalProperties", "description"]:
        if key in input_schema:
            schema[key] = input_schema[key]
    
    return schema


def mcp_tool_to_openai_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single MCP tool definition to OpenAI tool format.
    
    Args:
        mcp_tool: MCP tool definition with name, description, inputSchema
        
    Returns:
        OpenAI tool definition
    """
    input_schema = mcp_tool.get("inputSchema", {})
    
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.get("name", ""),
            "description": mcp_tool.get("description", ""),
            "parameters": mcp_schema_to_openai(input_schema)
        }
    }


def mcp_tools_to_openai_tools(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert a list of MCP tool definitions to OpenAI tools format.
    
    Args:
        mcp_tools: List of MCP tool definitions
        
    Returns:
        List of OpenAI tool definitions
    """
    return [mcp_tool_to_openai_tool(tool) for tool in mcp_tools]


def create_mcp_proxy_tools(
    mcp_tools: List[Dict[str, Any]], 
    mcp_client_manager
) -> List[MCPProxyTool]:
    """
    Create MCPProxyTool instances from MCP tool definitions.
    
    Args:
        mcp_tools: List of MCP tool definitions from MCPClientManager
        mcp_client_manager: The MCPClientManager instance for tool calls
        
    Returns:
        List of MCPProxyTool instances that can be registered with ToolRegistry
    """
    proxy_tools = []
    
    for mcp_tool in mcp_tools:
        name = mcp_tool.get("name", "")
        description = mcp_tool.get("description", "")
        input_schema = mcp_tool.get("inputSchema", {})
        mcp_server = mcp_tool.get("server", "unknown")
        
        # Convert input schema to OpenAI parameters format
        parameters = mcp_schema_to_openai(input_schema)
        
        # Create proxy tool instance
        proxy_tool = MCPProxyTool(
            name=name,
            description=description,
            parameters=parameters,
            mcp_server=mcp_server,
            mcp_client_manager=mcp_client_manager
        )
        
        proxy_tools.append(proxy_tool)
        print(f"[MCPConverter] Created proxy tool: {name}")
    
    return proxy_tools


def get_tool_schema_for_prompt(tools: List[BaseTool]) -> str:
    """
    Generate a human-readable tool schema for system prompts.
    
    Useful for including tool descriptions in prompts for models
    that don't support native function calling.
    
    Args:
        tools: List of tool instances
        
    Returns:
        Formatted string describing available tools
    """
    lines = ["Available Tools:", "=" * 50]
    
    for tool in tools:
        lines.append(f"\n## {tool.name}")
        lines.append(f"Description: {tool.description}")
        lines.append(f"Parameters: {tool.parameters}")
    
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)
