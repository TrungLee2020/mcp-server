import asyncio
import os

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv
from openai import OpenAI

from agent_code_chay.agent import Agent
from log_config import setup_logging

load_dotenv()
setup_logging()


def load_text_file(path: str) -> str:
    """Load text file. Dùng để load file md chứa system message"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Không tìm thấy file {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Lỗi khi đọc file {path}: {e}")


async def main():
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )

    agent = await Agent.create(
        openai_client=client,
        model_name=os.environ["MODEL_NAME"],
        temperature=0,
        system_message=load_text_file("system_prompt.md"),
        stdio_mcp_server_commands=[["python", ["-m", "mcp_server"]]],
        sse_mcp_server_urls=[],
        streamable_http_mcp_server_urls=[],
        remote_agent_urls=[],
    )

    agent_card = AgentCard(
        name="Hello Good bye agent",
        description="Hello Good bye agent",
        url=f"http://localhost:11001",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="tao_loi_chao_va_tam_biet",
                name="Tạo lời chào và tạm biệt",
                description="Đưa ra lời chào hoặc lời tạm biệt khi được cung cấp tên người cụ thể.",
                tags=[],
                examples=[
                    "Tạo lời chào cho John",
                    "Gửi lời chào tới Tom",
                    "Nói tạm biệt với Scott",
                ],
            )
        ],
    )

    await agent.serve_as_remote_agent(
        agent_card=agent_card,
        port=11001,
    )


if __name__ == "__main__":
    asyncio.run(main())
