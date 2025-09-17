# 📂 agent_code_chay

Thư mục `agent_code_chay` chứa mã nguồn Python phục vụ cho việc xây dựng và chạy một **AI Agent** có khả năng:
- Kết nối tới nhiều loại **MCP (Model Context Protocol) server** khác nhau (stdio, SSE, streamable HTTP).
- Quản lý và gọi **tool** do MCP server cung cấp.
- Xử lý phản hồi **streaming** từ LLM (Large Language Model), bao gồm cả text và tool calls.
- Cung cấp các hàm tiện ích hỗ trợ hiển thị và xử lý dữ liệu.

Cấu trúc thư mục:

```

agent_code_chay/
│── a2a_client.py       # Client kết nối Agent-to-Agent
│── agent.py            # Định nghĩa Agent, điều phối tool và luồng hội thoại
│── mcp_client.py       # Định nghĩa các client kết nối tới MCP server
│── tool.py             # Định nghĩa lớp Tool và logic gọi tool
│── utils.py            # Xử lý stream từ LLM, tiện ích hỗ trợ
└── __init__.py         # Đánh dấu đây là Python package

````

---

## 📌 Nội dung chi tiết các file

### 1. `a2a_client.py`
- Quản lý **kết nối Agent-to-Agent** (A2A).
- Cho phép một agent có thể giao tiếp hoặc gọi tool từ agent khác thông qua chuẩn MCP.
- Đóng vai trò kết nối giữa các agent khi triển khai **multi-agent system**.

### 2. `agent.py`
- Chứa định nghĩa lớp `Agent`, chịu trách nhiệm:
  - Kết nối tới MCP server thông qua các client trong `mcp_client.py`.
  - Lấy danh sách tool, gọi tool, và duy trì session.
  - Xử lý logic điều phối giữa LLM, mcp server và người dùng .
- Đây là file chính của package, đóng vai trò điều phối toàn bộ workflow.

### 3. `mcp_client.py`
- Định nghĩa các class client để kết nối tới MCP server:
  - `STDIOMCPClient`: kết nối qua **stdio**.
  - `SSEMCPClient`: kết nối qua **SSE (Server-Sent Events)**.
  - `StreamableHTTPMCPClient`: kết nối qua **Streamable HTTP**.

### 4. `tool.py`
- Định nghĩa class `Tool`
- Đối tượng từ class này sẽ bao gồm tên tool, định nghĩa tool (để cung cấp cho LLM) và cách để thực thi tool

### 5. `utils.py`
- Chứa hàm **`process_stream()`**:
  - Xử lý output stream từ LLM (bao gồm text + tool calls).
  - Hiển thị text dần dần trên **Streamlit UI**.
  - Tách riêng tool calls và gom chúng lại bằng `StreamToolAggregator`.
- Cung cấp **thời gian phản hồi đầu tiên và cuối cùng** → hữu ích để benchmark tốc độ LLM.

### 6. `__init__.py`
- Đánh dấu thư mục là Python package.

---

## 🚀 Cách sử dụng

### 1. Tạo môi trường

- Môi trường được tạo bằng uv tại thư mục gốc của project
```bash
uv sync
```

### 2. Ví dụ

```python
import asyncio
import os

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv
from openai import OpenAI

from agent_code_chay.agent import Agent
from log_config import setup_logging

load_dotenv()
setup_logging()


async def main():
    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )

    agent = await Agent.create(
        openai_client=client,
        model_name=os.getenv("MODEL_NAME"),
        temperature=0,
        system_message="Bạn là trợ lý hữu dụng",
        # stdio_mcp_server_commands=[["python", ["-m", "mcp_server"]]],
        # sse_mcp_server_urls=["http://localhost:8001/sse"],
        # streamable_http_mcp_server_urls=["http://localhost:8001/mcp"],
        # remote_agent_urls=[],
    )

    # # Bỏ comment để tạo giao diện chat streamlit
    # await agent.serve_as_chat_ui()

    # # Bỏ comment để tạo server remote agent
    # agent_card = AgentCard(
    #     name="Hello Good bye agent",
    #     description="Hello Good bye agent",
    #     url=f"http://localhost:11001",
    #     version="1.0.0",
    #     defaultInputModes=["text"],
    #     defaultOutputModes=["text"],
    #     capabilities=AgentCapabilities(streaming=False),
    #     skills=[
    #         AgentSkill(
    #             id="tao_loi_chao_va_tam_biet",
    #             name="Tạo lời chào và tạm biệt",
    #             description="Đưa ra lời chào hoặc lời tạm biệt khi được cung cấp tên người cụ thể.",
    #             tags=[],
    #             examples=[
    #                 "Tạo lời chào cho John",
    #                 "Gửi lời chào tới Tom",
    #                 "Nói tạm biệt với Scott",
    #             ],
    #         )
    #     ],
    # )
    # await agent.serve_as_remote_agent(
    #     agent_card=agent_card,
    #     port=11001,
    # )

if __name__ == "__main__":
    asyncio.run(main())
```

### Lưu ý
- Class Agent cho phép khởi tạo với stream=True, tức là cho phép phản hồi từ phía LLM có dạng stream. Tuy nhiên hiện tại đang có lỗi tool trả về bị parse sai khi sử dụng stream=True và kết quả trả về chứa tool call. Recommend: Sử dụng stream=False (giá trị False là mặc định) khi khởi tạo agent.
https://github.com/vllm-project/vllm/issues/17614