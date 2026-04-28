# 🤖 AI News Agent

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![CrewAI](https://img.shields.io/badge/CrewAI-Agentic_Framework-FF4B4B.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_Dashboard-009688.svg)
![License](https://img.shields.io/badge/license-MIT-green)

**AI News Agent** là một hệ thống tự động hóa tiên tiến (Agentic AI) được xây dựng dựa trên framework **CrewAI**. Hệ thống đóng vai trò như một Tổng biên tập công nghệ mẫn cán, tự động thu thập, chắt lọc, tóm tắt và phân phối các bản tin về Trí tuệ Nhân tạo (AI), Machine Learning và Công nghệ phần mềm mỗi ngày.

Dự án giúp bạn không bao giờ bị tụt hậu trong kỷ nguyên AI bằng cách mang những kiến thức giá trị nhất, mới nhất trực tiếp đến điện thoại và email của bạn vào đúng 7:00 sáng mỗi ngày.

---

## 🌟 Tính năng Nổi bật

- **🧠 Trí tuệ Mạng lưới (Agentic Workflow)**: Sử dụng các đặc vụ AI (Researcher & Analyst) từ CrewAI kết hợp cùng sức mạnh của mô hình ngôn ngữ lớn (Gemini Flash / GPT-4) để đọc hiểu, tóm tắt và chọn lọc thông tin.
- **📡 Cào dữ liệu Đa Nguồn (Multi-source Scraper)**: Tích hợp 6 nguồn dữ liệu chất lượng cao bao gồm nền tảng học thuật, diễn đàn công nghệ và video YouTube.
- **🚀 Phân phối Đa Kênh (Multi-channel Delivery)**: Tự động gửi bản tin đã định dạng qua Telegram (Instant View qua Telegraph), Discord (Rich Embeds), Email HTML Premium.
- **🌐 Web Archive Dashboard**: Tích hợp sẵn một web server cục bộ (FastAPI) lưu trữ lịch sử các bản tin theo định dạng HTML cao cấp, dễ dàng tra cứu.
- **🛡️ Chống Trùng Lặp (Deduplication)**: Hệ thống ghi nhớ (State Management) thông minh lưu lại các URL đã đọc để đảm bảo không bao giờ gửi lại tin tức cũ.
- **⚙️ Tự động hóa hoàn toàn**: Tích hợp sẵn GitHub Actions để tự động chạy pipeline mỗi sáng.

---

## 📡 Các Nguồn Dữ Liệu (Sources)

AI News Agent thu thập thông tin từ các "mỏ vàng" tri thức sau:
1. **GitHub Trending & RSS**: Các công cụ, thư viện mã nguồn mở AI đang thịnh hành nhất.
2. **Hacker News**: Các chủ đề và bài viết thảo luận về AI được upvote nhiều nhất.
3. **ArXiv Papers**: Bắt kịp các công trình nghiên cứu khoa học mới nhất (cs.AI, cs.LG).
4. **YouTube AI Channels**: Lấy tin từ các kênh hàng đầu như *Fireship, AI Explained, Matt Wolfe, Two Minute Papers*.
5. **Anthropic Official**: Các bản cập nhật mô hình, kỹ thuật Prompt Engineering từ cha đẻ của Claude.
6. **Security Alerts**: Cảnh báo lỗ hổng bảo mật khẩn cấp từ *The Hacker News / CISA*.

---

## 🏗️ Kiến trúc Hệ thống

Hệ thống hoạt động theo một pipeline tuyến tính khép kín:
`Gathering (Cào tin thô) ➡️ Summarize (LLM Tóm tắt & Lọc lõi) ➡️ Format (Định dạng UI) ➡️ Delivery (Phân phối)`

![Kiến trúc Agent](https://img.shields.io/badge/Architecture-CrewAI_Sequential_Process-blue?style=for-the-badge)

---

## 🚀 Hướng Dẫn Cài Đặt (Local Development)

### 1. Yêu cầu hệ thống
- Python 3.11+
- Pip / Venv

### 2. Thiết lập môi trường
```bash
# Clone dự án
git clone https://github.com/your-username/ai-news-agent.git
cd ai-news-agent

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Cấu hình API Keys (.env)
Tạo file `.env` ở thư mục gốc của dự án dựa trên mẫu:
```env
# AI Models
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
MODEL_PROVIDER=gemini  # 'openai' hoặc 'gemini'

# Telegram (Tùy chọn)
ENABLE_TELEGRAM=true
TELEGRAM_TOKEN=your_bot_token
CHAT_ID=your_chat_id

# Discord (Tùy chọn)
ENABLE_DISCORD=false
DISCORD_WEBHOOK_URL=your_discord_webhook

# GitHub (Tùy chọn - Giúp tăng rate limit)
GITHUB_TOKEN=your_github_token
```

### 4. Các Lệnh Khởi Chạy
Hệ thống hỗ trợ CLI Command linh hoạt:

```bash
# Chạy thử (Chỉ in ra màn hình, không gửi tin)
python main.py --dry-run

# Chạy thực tế và gửi đi các kênh (Discord, Email, Telegram text)
python main.py --send

# Chạy và gửi bản tin dạng bài viết Telegraph (Khuyên dùng cho Telegram)
python main.py --send --telegraph

# Test dữ liệu đầu vào của 1 nguồn cụ thể (Không tốn token AI)
python main.py --test-source youtube
# Các nguồn hỗ trợ: github | anthropic | security | hacker_news | arxiv | youtube
```

---

## 🌐 Web Dashboard Archive

Mỗi khi pipeline `--send` chạy thành công, một bản lưu HTML Premium sẽ được tạo trong thư mục `data/archive/`.
Để xem lại lịch sử các bản tin trên giao diện Web:

```bash
# Khởi chạy Web Server
python app.py
# (Hoặc: uvicorn app:app --reload)
```
Sau đó truy cập trình duyệt tại: **http://localhost:8000**

---

## 🤖 Tự Động Hóa (GitHub Actions)

Bạn không cần treo máy 24/7! Dự án đã cấu hình sẵn `.github/workflows/daily.yml` để chạy tự động lúc **7:00 Sáng (Giờ VN)** mỗi ngày.

**Cách thiết lập:**
1. Đẩy mã nguồn này lên một Private Repository trên GitHub của bạn.
2. Truy cập **Settings > Secrets and variables > Actions**.
3. Thêm các biến môi trường (`OPENAI_API_KEY`, `TELEGRAM_TOKEN`, v.v.) vào mục **Repository secrets**.
4. GitHub sẽ tự lo phần còn lại!

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)
- **AI Framework**: [CrewAI](https://crewai.com), LangChain
- **LLM Models**: Google Gemini (1.5 Flash/Pro), OpenAI (GPT-4o)
- **Web App & Scraping**: FastAPI, Uvicorn, BeautifulSoup4, Requests
- **Data Parsing**: Pydantic, Algolia Search API, Arxiv API, Youtube ytInitialData Regex.

---
*Developed with ❤️ as an advanced Agentic Web Scraper and Newsletter AI.*
