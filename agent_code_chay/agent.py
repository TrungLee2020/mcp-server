import json
import logging
import time
import traceback
from typing import Any

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from openai import OpenAI

from agent_code_chay.utils import process_stream

from .a2a_client import CustomA2AClient
from .mcp_client import SSEMCPClient, STDIOMCPClient, StreamableHTTPMCPClient

llm_logger = logging.getLogger("LLM")


class Agent:
    """Class đại diện cho một agent tích hợp với LLM (tương tác dưới dạng OpenAI client) có khả năng gọi tool, giao tiếp với MCP server và hoạt động như remote agent.

    Class này có thể stream dữ liệu từ LLM, xử lý tool calls, phục vụ trên giao diện người dùng (Streamlit) hoặc như một remote agent.

    Attributes:
        openai_client (OpenAI): Client tương thích với thư viện OpenAI để gọi API LLM.
        model_name (str): Tên mô hình LLM được sử dụng.
        temperature (float): Temperature khi gọi LLM, ảnh hưởng đến độ sáng tạo của đầu ra.
        system_message (str): System message để định hướng cách trả lời của LLM.
        stream (bool): Phản hồi của LLM có ở dạng stream hay không
        tools (dict): Danh sách các tool mà agent có thể gọi.
        stdio_mcp_server_commands (list[list[Any]]): Danh sách lệnh để khởi tạo stdio MCP servers. Các tool từ mcp server sẽ được cập nhật vào danh sách tool của agent.
        sse_mcp_server_urls (list[str]): Danh sách URL SSE MCP servers. Các tool từ mcp server sẽ được cập nhật vào danh sách tool của agent.
        streamable_http_mcp_server_urls (list[str]): Danh sách URL streamable HTTP MCP servers. Các tool từ mcp server sẽ được cập nhật vào danh sách tool của agent.
        remote_agent_urls (list[str]): Danh sách URL remote agents. Các remote agent sẽ được cung cấp cho agent dưới dạng tool.
    """

    def __init__(
        self,
        openai_client: OpenAI,
        model_name: str,
        temperature: float,
        system_message: str,
        stream: bool=False,
        tools: dict = [],
        stdio_mcp_server_commands: list[list[Any]] = [],
        sse_mcp_server_urls: list[str] = [],
        streamable_http_mcp_server_urls: list[str] = [],
        remote_agent_urls: list[str] = [],
    ):
        self.openai_client = openai_client
        self.model_name = model_name
        self.temperature = temperature
        self.system_message = system_message
        self.stream = stream
        # self.tools = tools # TODO: Cho phép cung cấp tool trực tiếp khi khởi tạo Agent
        self.stdio_mcp_server_commands = stdio_mcp_server_commands
        self.sse_mcp_server_urls = sse_mcp_server_urls
        self.streamable_http_mcp_server_urls = streamable_http_mcp_server_urls
        self.remote_agent_urls = remote_agent_urls

    @classmethod
    async def create(cls, *args, **kwargs) -> "Agent":
        """Khởi tạo agent cùng với MCP servers và remote agents.

        Sử dụng method này để tạo instance thay vì __init__.
        Lý do: trong python hàm __init__ không được phép là hàm async -> Dùng async classmethod create để khởi tạo.

        Returns:
            Agent: Một instance của Agent đã được cấu hình với tools và MCP servers.

        Raises:
            KeyError: Nếu có tool trùng lặp giữa các MCP servers hoặc remote agents.

        Example:
            ```python
            client = OpenAI(
                base_url=os.getenv("LLM_BASE_URL"),
                api_key=os.getenv("LLM_API_KEY"),
            )

            agent = await Agent.create(
                openai_client=client,
                model_name=os.getenv("MODEL_NAME"),
                temperature=0,
                system_message="Bạn là trợ lý ảo hữu ích.",
                tools=[],
                stdio_mcp_server_commands=[["python", ["-m", "mcp_server"]]],
                # sse_mcp_server_urls=["http://localhost:8001/sse"],
                # streamable_http_mcp_server_urls=["http://localhost:8001/mcp"],
                # remote_agent_urls=[],
            )
            ```
        """
        self = cls(*args, **kwargs)
        self.tools = {}
        self.mcp_servers = []

        # Thêm stdio MCP servers
        for stdio_mcp_server_command in self.stdio_mcp_server_commands:
            stdio_mcp_client = None
            try:
                stdio_mcp_client = await STDIOMCPClient.create(
                    *stdio_mcp_server_command
                )
                conflict = set(self.tools) & set(stdio_mcp_client.tools)
                if conflict:
                    raise KeyError(f"❌ Tool trùng lặp: {', '.join(conflict)}")

                self.mcp_servers.append(stdio_mcp_client)
                self.tools.update(stdio_mcp_client.tools)
                logging.info(
                    f"✅ Đã thêm stdio MCP server: {stdio_mcp_server_command} với tools: {list(stdio_mcp_client.tools.keys())}"
                )
            except:
                logging.info(
                    f"❌ Thêm stdio MCP server thất bại: {stdio_mcp_server_command}\n{traceback.format_exc()}"
                )
                if stdio_mcp_client:
                    await stdio_mcp_client.close()

        # Thêm SSE MCP servers
        for sse_mcp_server_url in self.sse_mcp_server_urls:
            sse_mcp_client = None
            try:
                sse_mcp_client = await SSEMCPClient.create(sse_mcp_server_url)
                conflict = set(self.tools) & set(sse_mcp_client.tools)
                if conflict:
                    raise KeyError(f"❌ Tool trùng lặp: {', '.join(conflict)}")

                self.mcp_servers.append(sse_mcp_client)
                self.tools.update(sse_mcp_client.tools)
                logging.info(
                    f"✅ Đã thêm SSE MCP server: {sse_mcp_server_url} với tools: {list(sse_mcp_client.tools.keys())}"
                )
            except:
                logging.info(
                    f"❌ Thêm SSE MCP server thất bại: {sse_mcp_server_url}\n{traceback.format_exc()}"
                )
                if sse_mcp_client:
                    await sse_mcp_client.close()

        # Thêm streamable HTTP MCP servers
        for streamable_http_mcp_server_url in self.streamable_http_mcp_server_urls:
            streamable_http_mcp_client = None
            try:
                streamable_http_mcp_client = await StreamableHTTPMCPClient.create(
                    streamable_http_mcp_server_url
                )
                conflict = set(self.tools) & set(streamable_http_mcp_client.tools)
                if conflict:
                    raise KeyError(f"❌ Tool trùng lặp: {', '.join(conflict)}")

                self.mcp_servers.append(streamable_http_mcp_client)
                self.tools.update(streamable_http_mcp_client.tools)
                logging.info(
                    f"✅ Đã thêm Streamable HTTP MCP server: {streamable_http_mcp_server_url} với tools: {list(streamable_http_mcp_client.tools.keys())}"
                )
            except:
                logging.info(
                    f"❌ Thêm Streamable HTTP MCP server thất bại: {streamable_http_mcp_server_url}\n{traceback.format_exc()}"
                )
                if streamable_http_mcp_client:
                    await streamable_http_mcp_client.close()

        # Thêm remote agents
        if self.remote_agent_urls:
            try:
                a2a_client = CustomA2AClient(a2a_server_urls=self.remote_agent_urls)
                conflict = set(self.tools) & set(a2a_client.tools)
                if conflict:
                    raise KeyError(f"❌ Tool trùng lặp: {', '.join(conflict)}")
                self.tools.update(a2a_client.tools)
            except:
                logging.info(
                    f"❌ Thêm remote agent thất bại: {self.remote_agent_urls}\n{traceback.format_exc()}"
                )

        return self

    async def invoke(self, messages: list[dict]) -> list[dict]:
        """Gọi LLM với danh sách messages và xử lý tool calls nếu có.

        Args:
            messages (list[dict]): Danh sách messages đầu vào.

        Returns:
            list[dict]: Danh sách messages sau khi LLM phản hồi và xử lý tool calls.
        """
        # Thêm system message
        if self.system_message:
            messages.insert(0, {"role": "system", "content": self.system_message})

        if self.stream:
            # Gọi đến LLM (stream)
            t0 = time.perf_counter()
            stream = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=[t.tool_define for t in self.tools.values()],
                stream=True,
                temperature=self.temperature,
            )

            # Xử lý stream
            message, first_response_time, end_response_time = process_stream(
                stream, print_output=False, streamlit_display=False
            )
        else:
            # Gọi đến LLM (non-stream)
            t0 = time.perf_counter()
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=[t.tool_define for t in self.tools.values()],
                stream=False,
                temperature=self.temperature,
            )
            first_response_time = end_response_time = time.perf_counter()
            message = {
                "role": "assistant",
                "content": response.choices[0].message.content.strip(),
                "tool_calls": response.choices[0].message.tool_calls,
            }

        messages.append(message)

        # Log LLM Call
        llm_logger.debug(
            f"\n\tBắt đầu phản hồi: {first_response_time-t0:.4f}s. "
            f"\n\tTổng thời gian: {end_response_time-t0:.4f}s."
            f"\n\tTools: {[t.tool_define for t in self.tools.values()]}"
            f"\n\tMessages: {messages}"
        )

        # Lặp lại cho đến khi không còn tool calls
        tool_calls = message["tool_calls"]
        while tool_calls:
            for tool_call in tool_calls:
                # Gọi tool
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = await self.tools[name](args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

            # Gọi lại LLM với kết quả tool
            if self.stream:
                # Gọi đến LLM (stream)
                t0 = time.perf_counter()
                stream = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=[t.tool_define for t in self.tools.values()],
                    stream=True,
                    temperature=self.temperature,
                )
                message, first_response_time, end_response_time = process_stream(
                    stream, print_output=False, streamlit_display=False
                )
            else:
                # Gọi đến LLM (non-stream)
                t0 = time.perf_counter()
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=[t.tool_define for t in self.tools.values()],
                    stream=False,
                    temperature=self.temperature,
                )
                first_response_time = end_response_time = time.perf_counter()
                message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content.strip(),
                    "tool_calls": response.choices[0].message.tool_calls,
                }

            messages.append(message)
            llm_logger.debug(
                f"\n\tBắt đầu phản hồi: {first_response_time-t0:.4f}s."
                f"\n\tTổng thời gian: {end_response_time-t0:.4f}s."
                f"\n\tTools: {[t.tool_define for t in self.tools.values()]}"
                f"\n\tMessages: {messages}"
            )
            tool_calls = message["tool_calls"]

        # Xóa system message trước khi trả về
        if messages[0]["role"] == "system":
            messages.pop(0)
        return messages

    async def serve_as_chat_ui(self):
        """Khởi chạy giao diện chatbot với Streamlit.

        Cho phép người dùng chat, hiển thị tool calls và kết quả thực thi ngay trong UI.

        Example:
            ```python
            await agent.serve_as_chat_ui()
            ```
        """
        import streamlit as st

        st.title("Chatbot")

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "system", "content": self.system_message}
            ]

        # Hiển thị lịch sử chat (user + assistant)
        messages = [
            m for m in st.session_state.messages if m["role"] in ["user", "assistant"]
        ]
        i = 0
        while i < len(messages):
            if messages[i]["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(messages[i]["content"])
                i += 1
                continue

            if messages[i]["role"] == "assistant":
                with st.chat_message("assistant"):
                    while i < len(messages) and messages[i]["role"] != "user":
                        response_placeholder = st.empty()
                        if messages[i]["content"].strip():
                            response_placeholder.markdown(
                                messages[i]["content"].strip()
                            )
                        # Hiển thị tool calls
                        tool_calls = messages[i].get("tool_calls")
                        if tool_calls:
                            for tool_call in tool_calls:
                                tool_id = tool_call.id
                                with st.popover(f"🔧 {tool_call.function.name}"):
                                    st.code(
                                        f"Arguments: {tool_call.function.arguments}"
                                    )
                                    # Tìm kết quả tool call theo id
                                    for m in st.session_state.messages:
                                        if (
                                            m["role"] == "tool"
                                            and m["tool_call_id"] == tool_id
                                        ):
                                            st.code(f"Result: {m['content']}")
                                            break
                        i += 1

        # Xử lý input từ người dùng
        if prompt := st.chat_input("Bạn muốn hỏi gì?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if self.stream:
                    t0 = time.perf_counter()
                    stream = self.openai_client.chat.completions.create(
                        model=self.model_name,
                        messages=st.session_state.messages,
                        tools=[t.tool_define for t in self.tools.values()],
                        stream=True,
                        temperature=self.temperature,
                    )
                    message, first_response_time, end_response_time = process_stream(
                        stream, print_output=False, streamlit_display=True
                    )
                else:
                    t0 = time.perf_counter()
                    response = self.openai_client.chat.completions.create(
                        model=self.model_name,
                        messages=st.session_state.messages,
                        tools=[t.tool_define for t in self.tools.values()],
                        stream=False,
                        temperature=self.temperature,
                    )
                    first_response_time = end_response_time = time.perf_counter()
                    message = {
                        "role": "assistant",
                        "content": response.choices[0].message.content.strip(),
                        "tool_calls": response.choices[0].message.tool_calls,
                    }
                    response_placeholder = st.empty()
                    if message["content"].strip():
                        response_placeholder.markdown(message["content"].strip())

                st.session_state.messages.append(message)

                llm_logger.debug(
                    f"\n\tBắt đầu phản hồi: {first_response_time-t0:.4f}s. "
                    f"\n\tTổng thời gian: {end_response_time-t0:.4f}s."
                    f"\n\tTools: {[t.tool_define for t in self.tools.values()]}"
                    f"\n\tMessages: {st.session_state.messages}"
                )

                # Xử lý tool calls trong Streamlit
                tool_calls = message["tool_calls"]
                while tool_calls:
                    for tool_call in tool_calls:
                        name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        with st.popover(f"🔧 {tool_call.function.name}"):
                            st.code(f"Arguments: {tool_call.function.arguments}")
                            result = await self.tools[name](args)
                            st.code(f"Result: {result}")

                        st.session_state.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(result),
                            }
                        )

                    # Gọi lại LLM với kết quả tool
                    if self.stream:
                        t0 = time.perf_counter()
                        stream = self.openai_client.chat.completions.create(
                            model=self.model_name,
                            messages=st.session_state.messages,
                            tools=[t.tool_define for t in self.tools.values()],
                            stream=True,
                            temperature=self.temperature,
                        )
                        message, first_response_time, end_response_time = process_stream(
                            stream, print_output=False, streamlit_display=True
                        )
                    else:
                        t0 = time.perf_counter()
                        response = self.openai_client.chat.completions.create(
                            model=self.model_name,
                            messages=st.session_state.messages,
                            tools=[t.tool_define for t in self.tools.values()],
                            stream=False,
                            temperature=self.temperature,
                        )
                        first_response_time = end_response_time = time.perf_counter()
                        message = {
                            "role": "assistant",
                            "content": response.choices[0].message.content.strip(),
                            "tool_calls": response.choices[0].message.tool_calls,
                        }
                        response_placeholder = st.empty()
                        if message["content"].strip():
                            response_placeholder.markdown(message["content"].strip())
                    st.session_state.messages.append(message)

                    llm_logger.debug(
                        f"\n\tBắt đầu phản hồi: {first_response_time-t0:.4f}s. "
                        f"\n\tTổng thời gian: {end_response_time-t0:.4f}s."
                        f"\n\tTools: {[t.tool_define for t in self.tools.values()]}"
                        f"\n\tMessages: {st.session_state.messages}"
                    )
                    tool_calls = message["tool_calls"]

        await self.close()

    async def close(self):
        """Đóng tất cả kết nối"""
        for mcp_server in self.mcp_servers:
            await mcp_server.close()

    async def serve_as_remote_agent(self, agent_card: AgentCard, port: int = 11001):
        """Khởi chạy agent như một remote agent với A2A protocol.

        Args:
            agent_card (AgentCard): Agent card của agent.
            port (int, optional): Cổng chạy server. Mặc định là 11001.
        """

        class CustomAgentExecutor(AgentExecutor):
            """Custom executor dùng để xử lý request từ remote agent."""

            def __init__(self, agent: "Agent"):
                self.agent = agent

            async def execute(
                self,
                context: RequestContext,
                event_queue: EventQueue,
            ) -> None:
                """Xử lý yêu cầu từ user và phản hồi lại qua event queue."""
                messages = await self.agent.invoke(
                    [{"role": "user", "content": context.get_user_input()}]
                ) # System message sẽ được thêm trong method invoke
                final_message = messages[-1]["content"]
                await event_queue.enqueue_event(new_agent_text_message(final_message))

            async def cancel(
                self, context: RequestContext, event_queue: EventQueue
            ) -> None:
                """Hiện tại chưa hỗ trợ cancel request."""
                raise Exception("cancel not supported")

        request_handler = DefaultRequestHandler(
            agent_executor=CustomAgentExecutor(self),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        # Chạy uvicorn trong async context
        config = uvicorn.Config(server.build(), host="0.0.0.0", port=port)
        server_instance = uvicorn.Server(config)
        await server_instance.serve()
