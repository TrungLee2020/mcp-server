# ⚡ mcp_server

`mcp_server` là một package được dùng để triển khai **Model Context Protocol (MCP) server**, cho phép định nghĩa và cung cấp các **tool** để các agent có thể kết nối và gọi.  

Server hỗ trợ nhiều loại **transport**:
- `stdio`
- `sse` (Server-Sent Events)
- `streamable-http` (phiên bản cải tiến dần thay thế SSE)

---

## 📂 Cấu trúc thư mục

```
mcp_server/
│── __main__.py          # File để chạy package
│── __init__.py          # Đánh dấu package
│── README.md            # Tài liệu mô tả package
│── log_config.py        # Cấu hình logging
│── tools.py             # Định nghĩa các tool
└── utils/
    └── mcp_server_utils.py  # Các hàm tiện ích hỗ trợ server

````

---

## 🧩 Chức năng chi tiết

### 1. `__main__.py`
- Điểm vào chính của server khi chạy bằng lệnh:
```bash
  python -m mcp_server --transport streamable-http --port 12001 --mount-path /abcd
```

### 2. `log_config.py`

* Cấu hình logging mặc định cho server.

### 3. `tools.py`

* Đây là nơi sẽ định nghĩa các tool của mcp server.
* Hàm `add_tools(mcp)` để đăng ký tool vào server.

### 4. `utils/mcp_server_utils.py`

* Chứa các hàm tiện ích phục vụ cho MCP server.

---

## 🚀 Cách chạy server

### 1. Cài đặt môi trường
Tại thư mục gốc của project:
```bash
uv sync
```

### 2. Định nghĩa các tool của mcp server
Định nghĩa các tool trong file mcp_server/tools.py, hàm add_tool

Cấu trúc của tool:
```python
    @mcp.tool() # Decorator mặc định của thư viện mcp, đánh dấu đây là một tool
    @tool_wrapper # Cung cấp xử lý ngoại lệ, tính toán thời gian chạy tool
    def bye(name: str) -> str:
        """Tool này dùng để làm gì. Các tham số đầu vào định dạng như thế nào."""
        ... # Code tool
        return res
```

Lưu ý:
- Luôn định nghĩa tool **bên trong** hàm add_tool
- Giá trị trả về của tool cần phải có kiểu string hoặc dict, không để là kiểu list (do mặc định thư viện mcp coi kiểu list có nghĩa là nhiều response). Nếu kiểu trả về là kiểu list, gói nó vào một dict, ví dụ:
```python
    return {"result": list_response}
```

### 3. Chạy server

```bash
uv run python -m mcp_server --help

usage: __main__.py [-h] [--transport {stdio,sse,streamable-http}] [--port PORT] [--mount-path MOUNT_PATH]

Run MCP server with chosen transport and port.

options:
  -h, --help            show this help message and exit
  --transport {stdio,sse,streamable-http}
                        Transport type to use: stdio, sse, streamable-http (default: stdio)
  --port PORT           Port number (only used for streamable-http, default: 8000)
  --mount-path MOUNT_PATH
```

### Chạy server với stdio
```bash
python -m mcp_server
```
* Transport: `stdio`
* Port: **không sử dụng** (vì stdio không cần cổng).
* Cách chạy này chỉ được sử dụng khi kết nối trực tiếp mcp server với agent trên cùng một máy. Lệnh chạy ```python -m mcp_server``` cũng không cần chạy trên terminal mà sẽ được cung cấp trực tiếp cho agent.

### Chạy server với SSE

```bash
python -m mcp_server --transport sse --port 8000 --mount-path /abcd
```

* Endpoint SSE:

  ```
  http://localhost:8000/abcd/sse
  ```

### Chạy server với Streamable HTTP

```bash
python -m mcp_server --transport streamable-http --port 8000 --mount-path /abcd
```

* Endpoint Streamable HTTP:

  ```
  http://localhost:8000/abcd/mcp
  ```
