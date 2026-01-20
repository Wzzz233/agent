from typing import Dict, Type, List
from app.tools.base_tool import BaseTool


class ToolRegistry:
    """Registry for managing available tools in the system"""

    def __init__(self):
        """Initialize the tool registry"""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}

    def register_tool(self, tool_class: Type[BaseTool]):
        """Register a tool class in the registry"""
        if not hasattr(tool_class, 'name') or not tool_class.name:
            raise ValueError(f"Tool class {tool_class.__name__} must have a 'name' attribute")

        self._tools[tool_class.name] = tool_class
        return tool_class

    def get_tool_class(self, name: str) -> Type[BaseTool]:
        """Get a tool class by name"""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def create_tool_instance(self, name: str) -> BaseTool:
        """Create an instance of a registered tool"""
        tool_class = self.get_tool_class(name)
        instance = tool_class()
        self._instances[name] = instance
        return instance

    def get_tool_instance(self, name: str) -> BaseTool:
        """Get a cached instance of a tool, creating it if needed"""
        if name not in self._instances:
            self.create_tool_instance(name)
        return self._instances[name]

    def list_tool_names(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def list_tool_specs(self) -> List[Dict[str, any]]:
        """List all tool specifications"""
        specs = []
        for name, tool_class in self._tools.items():
            instance = self.get_tool_instance(name)
            specs.append(instance.get_spec())
        return specs

    def unregister_tool(self, name: str):
        """Remove a tool from the registry"""
        if name in self._tools:
            del self._tools[name]
        if name in self._instances:
            del self._instances[name]


# Global tool registry instance
registry = ToolRegistry()