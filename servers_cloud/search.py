"""MCP Server for web search - Standard implementation using FastMCP (MCP 1.25+)."""
import asyncio
import sys
import logging
import platform

# MCP imports - 使用新版 FastMCP
from mcp.server import FastMCP

# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Create MCP server instance using FastMCP
mcp = FastMCP("search-server")


@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> str:
    """
    执行网络搜索并返回结果

    Args:
        query: 搜索查询关键词
        max_results: 返回的最大结果数量，默认5条
    """
    logger.info(f"Web search: query='{query}', max_results={max_results}")
    
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
                if i >= max_results - 1:
                    break
        
        if not results:
            return f"【搜索结果】未找到与 '{query}' 相关的结果"
        
        # 格式化输出
        output = f"【搜索结果】找到 {len(results)} 条关于 '{query}' 的结果:\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r['title']}\n"
            output += f"   链接: {r['url']}\n"
            output += f"   摘要: {r['snippet'][:200]}...\n\n" if len(r['snippet']) > 200 else f"   摘要: {r['snippet']}\n\n"
        
        logger.info(f"Search completed: {len(results)} results")
        return output
        
    except ImportError as e:
        error_msg = f"缺少依赖库: {e}. 请运行: pip install duckduckgo-search"
        logger.error(error_msg)
        return f"【错误】{error_msg}"
    except Exception as e:
        error_msg = f"搜索失败: {str(e)}"
        logger.error(error_msg)
        return f"【错误】{error_msg}"


if __name__ == "__main__":
    logger.info("Starting MCP Search Server...")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    mcp.run()