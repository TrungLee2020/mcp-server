## 🧠 Giới thiệu

Chương trình này tạo **agent** sử dụng **MCP (Model Context Protocol)** và **A2A (Agent to Agent)**.
Agent có khả năng kết nối đến nhiều nguồn (model, MCP server, remote agent) và phục vụ dưới dạng **giao diện chat**.

Code chính nằm trong file **`main.py`**, nơi khởi tạo client, cấu hình model, gắn các MCP server và khởi chạy agent.

---

## 📂 Cấu trúc dự án

```
.
├── agent_code_chay/                  # Thư mục chứa code cho Agent
│   ├── __init__.py
│   ├── agent.py
│   ├── a2a_client.py
│   ├── mcp_client.py
│   ├── tool.py
│   └── utils.py
│
├── mcp_server/                       # Thư mục tạo MCP server
│   ├── __init__.py
│   ├── __main__.py
│   ├── log_config.py
│   ├── tools.py                      # File chứa các tool mcp_server cung cấp
│   └── utils/
│
├── README.md
├── log_config.py
├── main.py                           # Điểm vào chính của chương trình
└── uv.lock                           # Lock file cho dependency
```

---

## ⚙️ Cài đặt

1. Clone repo + thiết lập môi trường:

   ```bash
   git clone <repo-url>
   cd <repo>
   uv sync
   ```
2. Tạo file .env: Copy file .env.example, đổi tên thành .env, sửa lại nội dung nếu muốn đổi sang openai/vllm server khác. Mặc định đang là vllm server nội bộ.
## 🚀 Chạy chương trình

```bash
# Kích hoạt venv trong Windows
.venv\Scripts\activate
# Kích hoạt venv trong Linux
. .venv/bin/activate

# Chạy ví dụ chat agent với mcp
python -m streamlit run examples/chat_agent_with_mcp.py

# Chạy ví dụ remote agent
python -m examples.remote_agent

# Sau khi chạy remote agent, chạy host agent (có kết nối với remote agent)
python -m streamlit run examples/host_agent.py

# Câu chat gọi tool trong template: Tạo lời chào tới Alice
```

Log trong quá trình chạy (của cả chương trình và mcp server, bao gồm các lượt gọi LLM) được lưu trong thư mục logs

## Sửa template cho agent cụ thể
* Sửa file mcp_server/tools.py: định nghĩa các tool có trên mcp server
* Sửa file main.py: cấu hình agent. Có thể copy code từ các file ví dụ trong thư mục example
* Chạy chương trình:
```bash
# Kích hoạt venv trong Windows
.venv\Scripts\activate
# Kích hoạt venv trong Linux
. .venv/bin/activate

# Nếu chương trình hiển thị giao diện streamlit (sử dụng agent.serve_as_chat_ui())
streamlit run main.py

# Nếu không dùng streamlit
python main.py
```

## Lưu ý
* Do cơ chế hoạt động của Streamlit là **chạy lại toàn bộ code mỗi khi người dùng gửi chat**, nên kết nối đến MCP server cũng bị **thiết lập lại sau mỗi lần chat**.
* Nếu kết nối được thiết lập nhanh thì không vấn đề gì. Tuy nhiên, trong trường hợp dùng **kết nối qua stdio** (server được khởi chạy trực tiếp từ code phía client), mỗi lần người dùng chat thì server lại bị **khởi động lại**, khiến **thời gian chờ trên giao diện tăng đáng kể**.
* **Khuyến nghị:** Nếu khởi tạo mcp server tốn thời gian, nên chuyển sang sử dụng kết nối qua **SSE hoặc streamable HTTP**. Khi đó client chỉ cần tạo lại kết nối, mà không phải khởi động lại MCP server. Hoặc xây dựng giao diện riêng không yêu cầu chạy lại code như streamlit.
