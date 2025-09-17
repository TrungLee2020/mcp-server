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
    def chat_with_vnpost_ai(
        user_message: str,
        topic: Optional[str] = None,
        user_id: str = "mcp_user",
        session_id: Optional[str] = None
    ) -> dict:
        """
        Gửi câu hỏi tới VNPost AI chatbot và nhận phản hồi.
        
        Args:
            user_message: Câu hỏi hoặc tin nhắn của người dùng
            topic: Chủ đề để lọc tài liệu (tùy chọn)
            user_id: ID người dùng (mặc định: "mcp_user")
            session_id: ID phiên chat (tự động tạo nếu không cung cấp)
            
        Returns:
            dict: Phản hồi từ chatbot bao gồm tin nhắn, tài liệu tham khảo và metadata
        """
        # Tự động tạo session_id nếu không được cung cấp
        if session_id is None:
            session_id = f"mcp_session_{int(time.time())}"
            
        # Tạo transaction_id
        transaction_id = str(uuid.uuid4())
        
        # URL API chat 
        api_base_url = "http://localhost:6868" 
        url = f"{api_base_url}/chat"
        
        # Chuẩn bị payload theo đúng format API
        payload = {
            "user_id": user_id,
            "session_id": session_id, 
            "transaction_id": transaction_id,
            "user_message": user_message,
            "chat_history": [],  # mở rộng để lưu lịch sử chat
            "topic": topic
        }
        
        try:
            # Gửi request tới API
            response = requests.post(
                url, 
                json=payload, 
                timeout=120,  # Timeout 2 phút để xử lý các truy vấn phức tạp
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Parse response JSON
            result = response.json()
            
            # Trả về kết quả được format đẹp
            formatted_result = {
                "bot_message": result.get("bot_message", ""),
                "show_references": bool(result.get("show_ref", 0)),
                "document_references": result.get("structured_references", []),
                "document_ids": result.get("doc_id", []),
                "timestamp": result.get("timestamp"),
                "session_info": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "transaction_id": transaction_id
                },
                "topic_used": topic,
                "error": result.get("err_id")
            }
            
            return formatted_result
            
        except requests.exceptions.Timeout:
            return {
                "error": "Timeout - API phản hồi quá lâu",
                "bot_message": "Xin lỗi, hệ thống đang xử lý quá lâu. Vui lòng thử lại.",
                "session_info": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "transaction_id": transaction_id
                }
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Không thể kết nối tới VNPost AI API",
                "bot_message": "Xin lỗi, không thể kết nối tới hệ thống AI. Vui lòng kiểm tra kết nối.",
                "session_info": {
                    "user_id": user_id, 
                    "session_id": session_id,
                    "transaction_id": transaction_id
                }
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"HTTP Error {response.status_code}: {e}",
                "bot_message": "Xin lỗi, có lỗi xảy ra từ phía server.",
                "session_info": {
                    "user_id": user_id,
                    "session_id": session_id, 
                    "transaction_id": transaction_id
                },
                "response_details": response.text if 'response' in locals() else None
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "bot_message": "Xin lỗi, có lỗi không mong đợi xảy ra.",
                "session_info": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "transaction_id": transaction_id
                }
            }
