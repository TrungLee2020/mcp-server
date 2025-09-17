from agent_code_chay.mcp_client import STDIOMCPClient, SSEMCPClient, StreamableHTTPMCPClient
import asyncio

async def main():
    stdio_mcp_client = await STDIOMCPClient.create("python", ["-m", "mcp_server"])
    # stdio_mcp_client = await SSEMCPClient.create("http://localhost:8000/sse")
    # stdio_mcp_client = await StreamableHTTPMCPClient.create("http://localhost:8000/mcp")
    print(stdio_mcp_client.tools)

    result = await stdio_mcp_client.tools["greet"]({"name": "ABC"})
    print(f"Tool result:\n{result}\n===")

    await stdio_mcp_client.close()

if __name__ == "__main__":
    asyncio.run(main())
