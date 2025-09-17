import argparse
import contextlib

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from .log_config import setup_logging
from .tools import add_tools

setup_logging()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run MCP server with chosen transport and port."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport type to use: stdio, sse, streamable-http (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number (only used for streamable-http, default: 8000)",
    )
    parser.add_argument(
        "--mount-path",
        type=str,
        default="/",
        help="Mount path of the MCP server (only used for sse and streamable-http, default: /)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Lấy argument
    args = parse_args()

    # Định nghĩa MCP server và danh sách tool
    mcp = FastMCP("MCP server", port=args.port)

    # Thêm tool
    add_tools(mcp)

    # Chạy server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        # Tạo Starlette app và mount the MCP servers
        # Server sẽ được serve tại http://localhost:{port}{mount_path}, ví dụ: http://localhost:8000/abcd
        # Đối với sse, end point sẽ là http://localhost:{port}{mount_path}/sse
        # Đối với streamable-http (được tạo ra để thay thế dần sse), end point sẽ là http://localhost:{port}{mount_path}/mcp
        if args.transport == "sse":
            app = Starlette(
                routes=[
                    Mount(args.mount_path, mcp.sse_app()),
                ],
            )
        elif args.transport == "streamable-http":

            @contextlib.asynccontextmanager
            async def lifespan(app: Starlette):
                async with contextlib.AsyncExitStack() as stack:
                    await stack.enter_async_context(mcp.session_manager.run())
                    yield

            app = Starlette(
                routes=[
                    Mount(args.mount_path, mcp.streamable_http_app()),
                ],
                lifespan=lifespan,
            )

        uvicorn.run(app, host="0.0.0.0", port=args.port)
