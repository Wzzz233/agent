"""Temporary MCP server for web search - for local testing."""
import asyncio
import json
import sys
from typing import Dict, Any


class WebSearchTool:
    """Original web search implementation to reuse."""

    @staticmethod
    def execute_search(params: str) -> str:
        """Execute the web search"""
        try:
            args = json.loads(params)
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON format in parameters."

        query = args.get('query', '').strip()
        if not query:
            return "[ERROR] Search query cannot be empty."

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


# MCP protocol constants
MCP_PROTOCOL_VERSION = "2024-11-05"
PROTOCOL_HEADER = f"MCP {MCP_PROTOCOL_VERSION}"


class MCPSearchServer:
    """Simple MCP server implementation for web search."""

    def __init__(self):
        self.running = True

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")

        if method == "tools/list":
            return self._handle_list_tools(request.get("id"))
        elif method == "tools/call":
            return await self._handle_call_tool(request)
        else:
            return {
                "error": {
                    "code": 400,
                    "message": f"Unknown method: {method}"
                },
                "id": request.get("id")
            }

    def _handle_list_tools(self, req_id: str) -> Dict[str, Any]:
        """Handle list tools request."""
        tools = [{
            "name": "web_search",
            "description": "Search information on the internet using DuckDuckGo. Use English keywords for better results. Returns search results with titles, URLs, and snippets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords in ENGLISH (e.g., 'terahertz spectroscopy advances 2024')"
                    }
                },
                "required": ["query"]
            }
        }]

        return {
            "result": {"tools": tools},
            "id": req_id
        }

    async def _handle_call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request."""
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "web_search":
            # Convert arguments to JSON string to match original interface
            args_json = json.dumps(arguments)
            result = WebSearchTool.execute_search(args_json)

            return {
                "result": {"content": result},
                "id": request.get("id")
            }
        else:
            return {
                "error": {
                    "code": 404,
                    "message": f"Tool '{tool_name}' not found"
                },
                "id": request.get("id")
            }

    async def run(self):
        """Run the MCP server."""
        print(f"{PROTOCOL_HEADER}", file=sys.stderr)
        print(f"Content-Type: application/json", file=sys.stderr)
        print(file=sys.stderr)  # Empty line signals end of headers

        sys.stderr.flush()

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while self.running:
            try:
                # Read length header
                line = await reader.readline()
                if not line:
                    break

                line = line.decode().strip()
                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())

                    # Read empty line
                    await reader.readline()

                    # Read JSON body
                    data = await reader.readexactly(length)
                    request = json.loads(data.decode())

                    # Process request
                    response = await self.handle_request(request)

                    # Send response
                    response_json = json.dumps(response, ensure_ascii=False)
                    response_bytes = response_json.encode()

                    print(f"Content-Length: {len(response_bytes)}", file=sys.stdout)
                    print(file=sys.stdout)  # Empty line
                    sys.stdout.buffer.write(response_bytes)
                    sys.stdout.flush()

            except Exception as e:
                print(f"Error in MCP server: {e}", file=sys.stderr)
                break


async def main():
    """Main entry point for the search server."""
    server = MCPSearchServer()
    print("Starting MCP Web Search Server...", file=sys.stderr)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())