import asyncio
import time

from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    print("Đang kết nối đến mcp server...")
    async with sse_client(url="http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"✅ Danh sách tool: {[t.name for t in tools.tools]}")

            # Call tool
            start = time.perf_counter()
            result = await session.call_tool("greet", arguments={"name": "hi"})
            end = time.perf_counter()
            print(f"✅ Kết quả chạy tool:\n{result.content[0].text}")
            print(f"✅ Thời gian chạy tool: {end-start:.4f}s")


if __name__ == "__main__":
    asyncio.run(main())
