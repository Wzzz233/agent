import json
from qwen_agent.tools.base import BaseTool
from typing import Dict, Any
from app.config.settings import config


class WebSearchTool(BaseTool):
    """Tool for searching information on the internet using DuckDuckGo"""

    name = "web_search"
    description = "Search information on the internet using DuckDuckGo. Use English keywords for better results. Returns search results with titles, URLs, and snippets."
    parameters = [{
        "name": "query",
        "type": "string",
        "description": "Search keywords in ENGLISH (e.g., 'terahertz spectroscopy advances 2024')",
        "required": True
    }]

    def __init__(self):
        """Initialize the web search tool"""
        super().__init__()
        self._ddgs_available = False
        self._import_ddgs()

    def _import_ddgs(self):
        """Import the DDGS library"""
        try:
            from ddgs import DDGS
            self.DDGS = DDGS
            self._ddgs_available = True
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                self.DDGS = DDGS
                self._ddgs_available = True
            except ImportError:
                self._ddgs_available = False

    def call(self, params: str, **kwargs) -> str:
        """Execute the web search"""
        if not self._ddgs_available:
            return (
                "[ERROR] ddgs package is not installed. "
                "Please install it using: pip install ddgs"
            )

        try:
            args = json.loads(params)
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON format in parameters."

        query = args.get('query', '').strip()
        if not query:
            return "[ERROR] Search query cannot be empty."

        try:
            # Use duckduckgo_search for searching
            ddgs = self.DDGS()
            results = list(ddgs.text(query, max_results=config.web.max_results))

            if not results:
                return (
                    f"[NO RESULTS] No search results found for: '{query}'\n"
                    f"Try using different or more general keywords."
                )

            # Format search results
            result_parts = [f"[SEARCH RESULTS] Query: '{query}'\n"]
            result_parts.append("Search Results:")
            result_parts.append("=" * 60)

            for i, r in enumerate(results, 1):
                result_parts.append(f"\n{i}. {r.get('title', 'No title')}")
                result_parts.append(f"   URL: {r.get('href', 'No URL')}")
                result_parts.append(f"   {r.get('body', 'No description')[:200]}...")

            result_parts.append("\n" + "=" * 60)
            result_parts.append("[NOTE] Please use the above information to answer the user's question.")

            return "\n".join(result_parts)

        except Exception as e:
            return (
                f"[SEARCH FAILED] Error occurred: {str(e)}\n"
                f"Please try again with a different query or answer based on existing knowledge."
            )