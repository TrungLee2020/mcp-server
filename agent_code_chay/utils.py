import time
from typing import Any, Dict, List, Tuple

import streamlit as st


class StreamToolAggregator:
    """Bộ gom tool-call khi LLM phản hồi dưới dạng stream.

    Khi LLM phản hồi, các tool call có thể đến thành nhiều phần.
    Class này dùng để ghép nối các phần đó lại thành kết quả hoàn chỉnh cuối cùng.

    Attributes:
        final_tool_calls (Dict[int, Any]): Lưu trữ tool call cuối cùng.
    """

    def __init__(self) -> None:
        """Khởi tạo đối tượng StreamToolAggregator với bộ nhớ rỗng."""
        self.final_tool_calls: Dict[int, Any] = {}

    def add(self, tool_call: Any) -> None:
        """Thêm một phần tool call vào bộ nhớ, tự động ghép nối nếu đã tồn tại index.

        Args:
            tool_call (Any): Đối tượng tool call, có thuộc tính `index` và `function.arguments`.
        """
        index = tool_call.index

        if index not in self.final_tool_calls:
            self.final_tool_calls[index] = tool_call
        else:
            # Ghép nối thêm argument mới vào argument trước đó
            self.final_tool_calls[index].function.arguments = (
                self.final_tool_calls[index].function.arguments or ""
            ) + tool_call.function.arguments

    def aggregate(self) -> List[Any]:
        """Trả về danh sách các tool call hoàn chỉnh sau khi đã ghép nối.

        Returns:
            List[Any]: Danh sách tool call cuối cùng.
        """
        return list(self.final_tool_calls.values())


def process_stream(
    stream: Any,
    print_output: bool = False,
    streamlit_display: bool = True,
) -> Tuple[Dict[str, Any], float, float]:
    """Xử lý dữ liệu stream từ LLM và tổng hợp thành AI message.

    Trong quá trình stream:
    - Nội dung text (`content`) được ghép nối dần.
    - Các tool call được gom lại bằng `StreamToolAggregator`.
    - Nếu `print_output=True`, text sẽ được in ra console.
    - Nếu `streamlit_display=True`, text sẽ được hiển thị dần trên Streamlit.

    Args:
        stream (Any): Stream trả về từ LLM.
        print_output (bool, optional): Có in ra console không. Mặc định: False.
        streamlit_display (bool, optional): Có hiển thị trên Streamlit không. Mặc định: True.

    Returns:
        Tuple[Dict[str, Any], float, float]:
            - `ai_message` (dict): AI message trả về từ LLM, bao gồm role, content và tool_calls.
            - `first_response_time` (float): Thời điểm bắt đầu nhận response.
            - `end_response_time` (float): Thời điểm kết thúc response.
    """
    message_content: str = ""
    first_response_time: float = None
    end_response_time: float = None

    if streamlit_display:
        response_placeholder = st.empty()

    stream_tool_aggregator = StreamToolAggregator()

    for chunk in stream:
        delta = chunk.choices[0].delta
        if first_response_time is None:
            first_response_time = time.perf_counter()

        # Xử lý text content stream
        if delta.content:
            if print_output:
                print(delta.content, end="", flush=True)
            message_content += delta.content
            if streamlit_display and message_content.strip():
                response_placeholder.markdown(message_content.strip())

        # Xử lý tool call stream
        if delta.tool_calls:
            for tool_call in delta.tool_calls:
                stream_tool_aggregator.add(tool_call)

    # Lấy danh sách tool call hoàn chỉnh
    tool_calls = stream_tool_aggregator.aggregate()

    # Đóng gói lại thành AI message
    ai_message: Dict[str, Any] = {
        "role": "assistant",
        "content": message_content.strip(),
        "tool_calls": tool_calls,
    }

    end_response_time = time.perf_counter()

    return ai_message, first_response_time, end_response_time