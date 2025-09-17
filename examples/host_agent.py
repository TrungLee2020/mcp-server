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
        stdio_mcp_server_commands=[],
        sse_mcp_server_urls=[],
        streamable_http_mcp_server_urls=[],
        remote_agent_urls=["http://localhost:11001"],
    )

    await agent.serve_as_chat_ui()


if __name__ == "__main__":
    asyncio.run(main())
