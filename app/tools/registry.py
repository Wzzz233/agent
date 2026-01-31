"""
Tool Registry - Central registry for all tools with OpenAI format export

This module provides:
1. Tool registration and discovery
2. Conversion to OpenAI function calling format
3. Tool lookup and execution
"""
from typing import Dict, Type, List, Any, Optional, Union
from app.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Registry for managing available tools in the system.
    
    Supports both class-based tools (that need instantiation) and
    instance-based tools (already instantiated, like MCP proxy tools).
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}

    def register_class(self, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """
        Register a tool class in the registry.
        Can be used as a decorator.
        
        Args:
            tool_class: The tool class to register
            
        Returns:
            The same tool class (for decorator use)
        """
        if not hasattr(tool_class, 'name') or not tool_class.name:
            raise ValueError(f"Tool class {tool_class.__name__} must have a 'name' attribute")

        self._tool_classes[tool_class.name] = tool_class
        return tool_class

    def register_instance(self, tool: BaseTool) -> BaseTool:
        """
        Register an already-instantiated tool.
        Used for MCP proxy tools and other dynamic tools.
        
        Args:
            tool: The tool instance to register
            
        Returns:
            The same tool instance
        """
        if not hasattr(tool, 'name') or not tool.name:
            raise ValueError("Tool instance must have a 'name' attribute")

        self._tool_instances[tool.name] = tool
        return tool

    def register_tools(self, tools: List[BaseTool]) -> None:
        """
        Register multiple tool instances at once.
        
        Args:
            tools: List of tool instances
        """
        for tool in tools:
            self.register_instance(tool)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        If it's a class, instantiate it first.
        If it's already an instance, return it.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        # Check instances first
        if name in self._tool_instances:
            return self._tool_instances[name]
        
        # Check classes and instantiate
        if name in self._tool_classes:
            if name not in self._tool_instances:
                self._tool_instances[name] = self._tool_classes[name]()
            return self._tool_instances[name]
        
        return None

    def list_tools(self) -> List[BaseTool]:
        """
        Get all registered tool instances.
        
        Returns:
            List of tool instances
        """
        # Instantiate any registered classes that haven't been instantiated
        for name, tool_class in self._tool_classes.items():
            if name not in self._tool_instances:
                self._tool_instances[name] = tool_class()
        
        return list(self._tool_instances.values())

    def list_tool_names(self) -> List[str]:
        """
        Get all registered tool names.
        
        Returns:
            List of tool names
        """
        names = set(self._tool_classes.keys())
        names.update(self._tool_instances.keys())
        return list(names)

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Export all tools in OpenAI tools format.
        
        This is the format used by chat completions API with tools parameter.
        
        Returns:
            List of OpenAI tool definitions
        """
        return [tool.to_openai_tool() for tool in self.list_tools()]

    def to_openai_functions(self) -> List[Dict[str, Any]]:
        """
        Export all tools in OpenAI functions format (legacy).
        
        Returns:
            List of OpenAI function definitions
        """
        return [tool.to_openai_function() for tool in self.list_tools()]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get JSON Schema definitions for all tools.
        
        Returns:
            List of tool schemas
        """
        return [tool.get_json_schema() for tool in self.list_tools()]

    def call_tool(self, name: str, arguments: Union[str, Dict[str, Any]]) -> str:
        """
        Call a tool by name with the given arguments.
        
        Args:
            name: Tool name
            arguments: Tool arguments (JSON string or dict)
            
        Returns:
            Tool result as string
        """
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        
        try:
            return tool.call(arguments)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tool_classes.clear()
        self._tool_instances.clear()


# Global tool registry instance
registry = ToolRegistry()


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    Decorator to register a tool class with the global registry.
    
    Example:
        @register_tool
        class MyTool(BaseTool):
            name = "my_tool"
            ...
    """
    return registry.register_class(tool_class)