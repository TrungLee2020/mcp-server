class Tool:
    """Lớp đại diện cho một công cụ (tool) được cung cấp cho LLM.

    Tool thường được dùng để đóng gói cả định nghĩa tool (Tool Schema, dùng để cung cấp thông tin cho LLM)
    và hàm thực thi tool.

    Attributes:
        tool_name (str): Tên của tool.
        tool_define (dict): Định nghĩa schema mô tả tool (để cung cấp cho LLM).
        call_tool_function (Callable): Hàm sẽ được gọi khi thực thi tool.
    """

    def __init__(
        self,
        tool_name: str,
        tool_define: dict,
        call_tool_function: callable,
    ) -> None:
        """Khởi tạo một Tool.

        Args:
            tool_name (str): Tên tool.
            tool_define (dict): Cấu hình schema mô tả tool.
            call_tool_function (Callable): Hàm thực thi logic khi gọi tool.

        Example:
            ```python
                tool_name = "call_agent"
                tool_define = {
                    "type": "function",
                    "function": {
                        "name": "call_agent",
                        "description": 'Hỏi các agent khác. Danh sách các agent:\n- Agent "Hello Good bye agent": Hello Good bye agent\n    - Khả năng:\n        - Đưa ra lời chào hoặc lời tạm biệt khi được cung cấp tên người cụ thể.\n    - Ví dụ: \n        - Tạo lời chào cho John\n        - Gửi lời chào tới Tom\n        - Nói tạm biệt với Scott\n',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Yêu cầu hoặc câu hỏi gửi đến agent",
                                },
                                "agent_name": {"type": "string", "description": "Tên agent"},
                            },
                            "required": ["message", "agent_name"],
                        },
                        "strict": True,
                    },
                }
                call_tool_function = lambda x: f"Hello, {x}"
                tool = Tool(
                    tool_name=tool_name,
                    tool_define=tool_define,
                    call_tool_function=call_tool_function,
                )
                print(tool("Alice"))
            ```
        """
        self.tool_name = tool_name
        self.tool_define = tool_define
        self.call_tool_function = call_tool_function

    def __call__(self, *args, **kwds) -> object:
        """Thực thi tool bằng cách gọi đến call_tool_function.

        Các tham số sẽ được truyền vào call_tool_function
        Args:
            *args: Các đối số truyền vào hàm.
            **kwds: Các đối số keyword truyền vào hàm.

        Returns:
            object: Kết quả trả về từ `call_tool_function`.

        Example:
            ```python
                tool_name = "call_agent"
                tool_define = {
                    "type": "function",
                    "function": {
                        "name": "call_agent",
                        "description": 'Hỏi các agent khác. Danh sách các agent:\n- Agent "Hello Good bye agent": Hello Good bye agent\n    - Khả năng:\n        - Đưa ra lời chào hoặc lời tạm biệt khi được cung cấp tên người cụ thể.\n    - Ví dụ: \n        - Tạo lời chào cho John\n        - Gửi lời chào tới Tom\n        - Nói tạm biệt với Scott\n',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Yêu cầu hoặc câu hỏi gửi đến agent",
                                },
                                "agent_name": {"type": "string", "description": "Tên agent"},
                            },
                            "required": ["message", "agent_name"],
                        },
                        "strict": True,
                    },
                }
                call_tool_function = lambda x: f"Hello, {x}"
                tool = Tool(
                    tool_name=tool_name,
                    tool_define=tool_define,
                    call_tool_function=call_tool_function,
                )
                print(tool("Alice"))
            ```
        """
        return self.call_tool_function(*args, **kwds)
