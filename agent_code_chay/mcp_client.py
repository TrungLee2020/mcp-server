from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .tool import Tool


class MCPConnectionError(Exception):
    """Ngoại lệ được raise khi kết nối tới MCP server thất bại."""

    pass


class MCPClient:
    """Lớp cơ sở cho các client MCP.

    Lớp này định nghĩa các phương thức cơ bản để:
    - Kết nối tới MCP server
    - Lấy danh sách tool từ MCP server
    - Gọi tool từ MCP server
    - Đóng kết nối khi không sử dụng nữa

    Các class kế thừa MCPClient (STDIOMCPClient, SSEMCPClient, StreamableHTTPMCPClient) cần implement method __init__ và connect
    """

    @classmethod
    async def create(cls, *args, **kwargs) -> "MCPClient":
        """Khởi tạo MCP client và tự động kết nối.

        Phương thức này tạo một instance của MCPClient (hoặc lớp con),
        thực hiện kết nối tới server, sau đó lấy danh sách tool và đăng ký
        vào thuộc tính `self.tools`.

        Sử dụng method này để tạo instance cho STDIOMCPClient, SSEMCPClient, StreamableHTTPMCPClient thay vì __init__.
        Lý do: trong python hàm __init__ không được phép là hàm async -> Dùng async classmethod create để khởi tạo.

        Args:
            *args: Các tham số khởi tạo truyền cho constructor.
            **kwargs: Các tham số keyword truyền cho constructor.

        Returns:
            MCPClient: Đối tượng MCP client đã được kết nối và sẵn sàng sử dụng.

                Ví dụ:
            ```python
            client = await StreamableHTTPMCPClient.create("http://localhost:12001/mcp")
            await client.close() # Luôn close connection khi không sử dụng
            ```
        """
        self = cls(*args, **kwargs)

        self.closed = False  # Thuộc tính kiểu bool để kiểm tra kết nối đã được đóng hay chưa (tránh đóng kết nối nhiều lần gây lỗi)

        await self.connect()

        # Khởi tạo danh sách tool dựa trên server response
        self.tools = {
            tool.name: Tool(
                tool_name=tool.name,
                tool_define={
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                        "strict": True,
                    },
                },
                call_tool_function=lambda arguments, name=tool.name: self.call_tool(
                    name, arguments
                ),
            )
            for tool in (await self.list_tools()).tools
        }

        return self

    async def list_tools(self) -> Any:
        """Lấy danh sách tool từ MCP server.

        Returns:
            Any: Kết quả trả về từ server, bao gồm danh sách các tool.

        Ví dụ:
            ```python
            client = await StreamableHTTPMCPClient.create("http://localhost:12001/mcp")
            print(await client.list_tools())
            await client.close() # Luôn close connection khi không sử dụng
            ```
        """
        return await self._session.list_tools()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Gọi tool từ MCP server.

        Args:
            name (str): Tên của tool cần gọi.
            arguments (Dict[str, Any]): Tham số đầu vào cho tool.

        Returns:
            str: Kết quả text từ tool.

        Ví dụ:
            ```python
            client = await StreamableHTTPMCPClient.create("http://localhost:12001/mcp")
            print(
                await client.call_tool(
                    name="greet",
                    arguments={"name": "Alice"},
                )
            )
            await client.close() # Luôn close connection khi không sử dụng
            ```
        """
        result = await self._session.call_tool(name, arguments)
        return result.content[0].text

    async def close(self) -> None:
        """Đóng session và giải phóng tài nguyên."""
        if not self.closed:
            self.closed = True
            if self._session_cm:
                await self._session_cm.__aexit__(None, None, None)
            if self._client_cm:
                await self._client_cm.__aexit__(None, None, None)


class STDIOMCPClient(MCPClient):
    """MCP Client kết nối qua STDIO."""

    def __init__(self, command: str, args: list[str]):
        """Khởi tạo STDIO MCP client.

        Lưu ý: Sử dụng method create để khởi tạo thay vì dùng __init__

        Args:
            command (str): Lệnh thực thi MCP server.
            args (list[str]): Danh sách tham số truyền cho command.

        Ví dụ:
            ```python
            client = await STDIOMCPClient.create(
                command="python",
                args=["-m", "mcp_server"],
            )
            print(
                await client.call_tool(
                    name="greet",
                    arguments={"name": "Alice"},
                )
            )
            await client.close()  # Luôn close connection khi không sử dụng
            ```
        """
        self.command = command
        self.args = args
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
        )
        self._session = None
        self._read = None
        self._write = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self) -> None:
        """Mở kết nối STDIO tới MCP server. Được gọi tự động khi chạy method create."""
        self._client_cm = stdio_client(self.server_params)
        self._read, self._write = await self._client_cm.__aenter__()

        self._session_cm = ClientSession(self._read, self._write)
        self._session = await self._session_cm.__aenter__()

        try:
            await self._session.initialize()
        except Exception as e:
            await self.close()
            raise MCPConnectionError(
                f"Kết nối tới mcp server thất bại: {self.command}, {self.args}: {e}"
            ) from e


class SSEMCPClient(MCPClient):
    """MCP Client kết nối qua SSE (Server-Sent Events)."""

    def __init__(self, mcp_server_url: str):
        """Khởi tạo SSE MCP client.

        Lưu ý: Sử dụng method create để khởi tạo thay vì dùng __init__

        Args:
            mcp_server_url (str): URL MCP server hỗ trợ SSE.

        Ví dụ:
            ```python
            client = await SSEMCPClient.create("http://localhost:12001/sse")  # endpoint Streamable HTTP mặc định là /sse
            print(
                await client.call_tool(
                    name="greet",
                    arguments={"name": "Alice"},
                )
            )
            await client.close()  # Luôn close connection khi không sử dụng
            ```
        """
        self.mcp_server_url = mcp_server_url
        self._session = None
        self._read = None
        self._write = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self) -> None:
        """Mở kết nối SSE tới MCP server. Được gọi tự động khi chạy method create."""
        self._client_cm = sse_client(self.mcp_server_url)
        self._read, self._write = await self._client_cm.__aenter__()

        self._session_cm = ClientSession(self._read, self._write)
        self._session = await self._session_cm.__aenter__()

        try:
            await self._session.initialize()
        except Exception as e:
            await self.close()
            raise MCPConnectionError(
                f"MCP protocol error with {self.mcp_server_url}: {e}"
            ) from e


class StreamableHTTPMCPClient(MCPClient):
    """MCP Client kết nối qua Streamable HTTP."""

    def __init__(self, mcp_server_url: str):
        """Khởi tạo Streamable HTTP MCP client.

        Lưu ý: Sử dụng method create để khởi tạo thay vì dùng __init__

        Args:
            mcp_server_url (str): URL MCP server hỗ trợ Streamable HTTP.

        Ví dụ:
            ```python
            client = await StreamableHTTPMCPClient.create("http://localhost:12001/mcp") # endpoint Streamable HTTP mặc định là /mcp
            print(
                await client.call_tool(
                    name="greet",
                    arguments={"name": "Alice"},
                )
            )
            await client.close()  # Luôn close connection khi không sử dụng
            ```
        """
        self.mcp_server_url = mcp_server_url
        self._session = None
        self._read = None
        self._write = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self) -> None:
        """Mở kết nối streaming HTTP tới MCP server. Được gọi tự động khi chạy method create."""
        self._client_cm = streamablehttp_client(self.mcp_server_url)
        self._read, self._write, _ = await self._client_cm.__aenter__()

        self._session_cm = ClientSession(self._read, self._write)
        self._session = await self._session_cm.__aenter__()

        try:
            await self._session.initialize()
        except Exception as e:
            await self.close()
            raise MCPConnectionError(
                f"Kết nối tới mcp server thất bại: {self.mcp_server_url}: {e}"
            ) from e
