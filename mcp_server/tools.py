from .utils.mcp_server_utils import tool_wrapper
import requests

def add_tools(mcp):
    @mcp.tool()
    @tool_wrapper
    def greet(name: str) -> str:
        """Greet someone by name."""
        res = f"Hello, {name}!"
        return res

    @mcp.tool()
    @tool_wrapper
    def bye(name: str) -> str:
        """Good bye someone by name."""
        res = f"Bye, {name}!"
        return res
    
    @mcp.tool()
    @tool_wrapper
    def call_chat_api(query: str, session_id: str = "test_session") -> dict:
        """Call external chat API and return output as dict."""
        api_base_url = "http://localhost:6868"
        url = f"{api_base_url}/chat"
        payload = {
            "session_id": session_id,
            "query": query
        }
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
