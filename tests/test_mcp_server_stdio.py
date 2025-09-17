import asyncio
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-m", "mcp_server"],
)


async def main():
    print("Đang kết nối đến mcp server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"✅ Danh sách tool: {[t.name for t in tools.tools]}")
            print(tools)

            # Call tool
            start = time.perf_counter()
            result = await session.call_tool("greet", arguments={"name": "hi"})
            end = time.perf_counter()
            print(f"✅ Kết quả chạy tool:\n{result.content[0].text}")
            print(f"✅ Thời gian chạy tool: {end-start:.4f}s")


if __name__ == "__main__":
    asyncio.run(main())
