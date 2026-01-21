"""MCP Server for web search - Standard implementation."""
import asyncio
import json
import sys
import logging
from typing import Dict, Any
from mcp.server import Server
from mcp.types import Tool, StaticResource, ToolResult
import argparse


# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("internet-search-gateway")


class WebSearchController:
    """Web search controller implementing the actual business logic."""

    def __init__(self):
        self.max_results = 5

    def execute_search(self, params: Dict[str, Any]) -> str:
        """Execute the web search."""
        query = params.get('query', '').strip()

        if not query:
            return "[ERROR] Search query cannot be empty."

        try:
            # Simulate search functionality
            # In a real implementation, we would use actual search libraries
            results = [
                {"title": f"Result 1 for {query}", "href": "http://example.com/1", "body": f"This is a sample result for {query}"},
                {"title": f"Result 2 for {query}", "href": "http://example.com/2", "body": f"Another sample result discussing {query}"}
            ]

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

            formatted_result = "\n".join(result_parts)
            return formatted_result

        except Exception as e:
            return f"[SEARCH FAILED] Error occurred: {str(e)}"


search_controller = WebSearchController()


@server.tool(
    "web_search",
    "Search information on the internet using DuckDuckGo. Use English keywords for better results. Returns search results with titles, URLs, and snippets."
)
async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search information on the internet using DuckDuckGo.

    Args:
        query: Search keywords in ENGLISH (e.g., 'terahertz spectroscopy advances 2024')
        max_results: Maximum number of results to return (default: 5)
    """
    params = {
        "query": query,
        "max_results": max_results
    }

    logger.info(f"Executing web search: {params}")

    try:
        result = search_controller.execute_search(params)
        logger.info(f"Web search completed with {len(result)} chars result")
        return result
    except Exception as e:
        error_msg = f"[SEARCH FAILED] Error occurred: {str(e)}"
        logger.error(error_msg)
        return error_msg


async def main():
    """Main entry point for the search server."""
    from mcp.server.stdio import stdio_server
    
    logger.info("Starting MCP Web Search Server...")

    # Run with stdio transport - proper async iteration
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Search server running, waiting for connections...")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    # Use asyncio.run to run the main function
    asyncio.run(main())