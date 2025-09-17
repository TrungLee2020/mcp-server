import json
import logging
import traceback
import uuid
from typing import Any, Dict, List

import httpx
import requests
from a2a.client import A2AClient
from a2a.types import AgentCard, MessageSendParams, SendMessageRequest
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from .tool import Tool


class CustomA2AClient:
    """A2A client tùy chỉnh để kết nối với các remote agent và gửi message.

    Lớp này cho phép:
    - Kết nối tới các agent bên ngoài thông qua URL
    - Quản lý danh sách agent đã kết nối
    - Gửi message đến các agent và nhận lại phản hồi

    Ví dụ:
        ```python
        client = CustomA2AClient(a2a_server_urls=["http://localhost:11001"])
        response = await client.call_remote_agent(
            agent_name="Hello Good bye agent", message="Tạo lời chào cho Alice"
        )
        print(response)
        ```
    """

    def __init__(self, a2a_server_urls: List[str], default_timeout: float = 600.0):
        """Khởi tạo client với danh sách server URL của agent.

        Args:
            a2a_server_urls (List[str]): Danh sách URL server của các agent.
            default_timeout (float, optional): Timeout mặc định khi gọi tới agent (giây). Mặc định: 600.0.
        """
        self.default_timeout = default_timeout
        self.agents: Dict[str, AgentCard] = {}

        # Thử kết nối tới từng agent trong danh sách URL
        for server_url in a2a_server_urls:
            server_url = server_url.rstrip("/")
            try:
                agent_info = requests.get(f"{server_url}{AGENT_CARD_WELL_KNOWN_PATH}")
                agent_data = agent_info.json()
                agent_card = AgentCard(**agent_data)
            except Exception:
                logging.info(
                    f"❌ Thêm remote agent thất bại: {server_url}\n{traceback.format_exc()}"
                )
                continue

            # Kiểm tra trùng tên agent
            if agent_card.name in self.agents:
                logging.info(
                    f"❌ Thêm remote agent thất bại: {server_url}. Agent tên '{agent_card.name}' đã tồn tại."
                )
            else:
                self.agents[agent_card.name] = agent_card
                logging.info(
                    f"✅ Đã thêm remote agent với url: {server_url}. Agent name: {agent_card.name}"
                )

        # Tạo tool call_agent để gọi tới các remote agent
        if self.agents:
            self.tools: Dict[str, Tool] = {
                "call_agent": Tool(
                    tool_name="call_agent",
                    tool_define=self.get_tool_define(),
                    call_tool_function=lambda arguments: self.call_remote_agent(
                        **arguments
                    ),
                )
            }
        else:
            # Trường hợp không lấy được remote agent nào
            self.tools = {}

    def get_tool_define(self) -> Dict[str, Any]:
        """Tạo mô tả tool `call_agent` để gọi các agent khác.

        Returns:
            Dict[str, Any]: Định nghĩa tool dưới dạng JSON Schema.

        Ví dụ:
            ```python
                client = CustomA2AClient(a2a_server_urls=["http://localhost:11001"])
                tool_define = client.get_tool_define()
                print(tool_define)
                print(tool_define["function"]["description"])
            ```
        """
        description = "Hỏi các agent khác. Danh sách các agent:"
        for agent_name, agent_card in self.agents.items():
            skills = [skill.description for skill in agent_card.skills]
            examples = [
                example for skill in agent_card.skills for example in skill.examples
            ]

            skills_str = "".join("\n        - " + s for s in skills)
            examples_str = "".join("\n        - " + e for e in examples)

            description += f"""- Agent "{agent_name}": {agent_card.description}
    - Khả năng:{skills_str}
    - Ví dụ: {examples_str}
"""

        return {
            "type": "function",
            "function": {
                "name": "call_agent",
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Yêu cầu hoặc câu hỏi gửi đến agent",
                        },
                        "agent_name": {
                            "type": "string",
                            "description": "Tên agent",
                        },
                    },
                    "required": ["message", "agent_name"],
                },
                "strict": True,
            },
        }

    async def call_remote_agent(self, agent_name: str, message: str) -> str:
        """Gửi message tới agent từ xa và nhận phản hồi.

        Args:
            agent_name (str): Tên agent muốn gọi.
            message (str): Nội dung message gửi tới agent.

        Returns:
            str: Phản hồi text từ agent, hoặc JSON string nếu không parse được.

        Ví dụ:
            ```python
                client = CustomA2AClient(a2a_server_urls=["http://localhost:11001"])
                response = await client.call_remote_agent(
                    agent_name="Hello Good bye agent", message="Tạo lời chào cho Alice"
                )
                print(response)
            ```
        """
        if agent_name not in self.agents:
            return f"Agent không tồn tại: {agent_name}. Danh sách agent: {list(self.agents.keys())}"

        # Cấu hình timeout cho httpx client
        timeout_config = httpx.Timeout(
            timeout=self.default_timeout,
            connect=10.0,
            read=self.default_timeout,
            write=10.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout_config) as httpx_client:
            agent_card = self.agents[agent_name]

            # Tạo A2A client với agent card
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            # Chuẩn bị payload message theo chuẩn A2A
            send_message_payload = {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": uuid.uuid4().hex,
                }
            }

            # Tạo request gửi đi
            request = SendMessageRequest(
                id=str(uuid.uuid4()), params=MessageSendParams(**send_message_payload)
            )

            # Gửi message với cấu hình timeout
            response = await client.send_message(request)

            # Trích xuất text từ response
            try:
                response_dict = response.model_dump(mode="json", exclude_none=True)
                if "result" in response_dict and "parts" in response_dict["result"]:
                    for part in response_dict["result"]["parts"]:
                        if "text" in part:
                            return part["text"]

                # Nếu không trích xuất được text thì trả về toàn bộ response dạng JSON
                return json.dumps(response_dict, indent=2)

            except Exception as e:
                # Log lỗi và trả về chuỗi mô tả response
                logging.error(f"Lỗi khi parse response: {e}")
                return str(response)
