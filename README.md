# 🤖 AI News Agent

> Hệ thống tự động thu thập tin tức AI (GitHub Trending + HuggingFace Papers) và gửi bản tin hàng ngày lên Telegram/Discord/Email.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-95%20passed-green.svg)](https://github.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Daily%20Schedule-green.svg)](https://github.com/features/actions)

## ✨ Điểm nổi bật

### 🔄 Tự động hóa hoàn toàn
- **GitHub Trending** - Thu thập repo AI trending hàng ngày
- **HuggingFace Papers** - Lấy paper AI mới nhất từ arXiv
- **Đa nền tảng** - Gửi Telegram / Discord / Email
- **Cron Scheduling** - Chạy tự động theo lịch hoặc GitHub Actions

### 🧠 Thông minh  
- **AI Summarization** - Dùng LLM (OpenAI/Gemini) tóm tắt nội dung
- **Smart Retry** - Tự động retry khi gặp lỗi mạng
- **Usage Tracking** - Theo dõi chi phí API theo ngày/tháng

### 🛡️ Đáng tin cậy
- **Persistent Memory** - Không gửi trùng nội dung đã gửi
- **Alert System** - Cảnh báo khi gần hết credit API
- **Error Classification** - Phân loại lỗi để xử lý tốt hơn

## 🚀 Quick Start

### 1. Cài đặt

```bash
# Clone repository
git clone https://github.com/yourusername/ai_news_agent.git
cd ai_news_agent

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# Cài dependencies
pip install -r requirements.txt
```

### 2. Cấu hình

Tạo file `.env`:

```env
# API Keys (bắt buộc)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# GitHub Token (để lấy trending repos)
GITHUB_TOKEN=github_pat_...

# Telegram (bắt buộc)
TELEGRAM_TOKEN=bot_token
CHAT_ID=chat_id

# Tùy chọn: Bật thêm platform
ENABLE_TELEGRAM=true
ENABLE_DISCORD=false
ENABLE_EMAIL=false
```

### 3. Chạy thủ công

```bash
# Chạy và in ra console
python main.py --repo-limit 3 --paper-limit 5

# Gửi lên Telegram
python main.py --send --repo-limit 3 --paper-limit 5

# Gửi qua Telegraph (1 tin nhắn + link Instant View)
python main.py --send --repo-limit 3 --paper-limit 5 --telegraph
```

### 4. Chạy tự động

#### Cách 1: GitHub Actions (Khuyến nghị)
- Push code lên GitHub
- Vào **Actions** tab → Chạy "AI News Daily"
- Job chạy tự động lúc **9:00 AM UTC** mỗi ngày

#### Cách 2: Cron cục bộ
```bash
python -m src.cron.daemon
```

#### Cách 3: Windows Task Scheduler
```bash
python -m src.cron.daemon --once
```
Đặt task chạy daily lúc 9:00 AM.

## 📁 Cấu trúc dự án

```
ai_news_agent/
├── main.py                 # Entry point
├── src/
│   ├── crew/             # CrewAI crew (AI summarization)
│   ├── tools/            # GitHub & HuggingFace tools
│   ├── cron/             # Scheduler & runner
│   ├── gateway/          # Multi-platform delivery
│   ├── memory/          # Persistent memory
│   ├── monitoring/      # Usage & cost tracking
│   ├── services/        # Telegram, retry logic
│   ├── config/          # Settings
│   └── setup/           # Setup wizard
├── tests/                # 95 unit tests
├── .github/
│   └── workflows/       # GitHub Actions
└── README.md
```

## 🧪 Testing

```bash
# Chạy tất cả tests
pytest tests/ -v

# Kết quả: 95 tests passed
```

## 📊 Usage Report

Xem chi phí API:
```bash
python -c "from src.monitoring import get_report; print(get_report())"
```

Output mẫu:
```
📊 AI News Agent - Usage Report (7 ngày gần nhất)
──────────────────────────────────────────────────
  Total Requests:      7
  Input Tokens:        156,000
  Output Tokens:       189,200
  Total Cost:          $0.0284
──────────────────────────────────────────────────
  Avg Daily Cost:      $0.0041
  Est. Monthly Cost:    $0.12
```

## 🔧 Cấu hình nâng cao

### Telegram Bot
```env
TELEGRAM_TOKEN=your_bot_token
CHAT_ID=your_chat_id
ENABLE_TELEGRAM=true
```

### Discord Webhook
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ENABLE_DISCORD=true
```

### Email (SMTP)
```env
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
ENABLE_EMAIL=true
```

### Cấu hình bản tin
```env
AI_NEWS_REPO_LIMIT=5       # Số repo mặc định
AI_NEWS_PAPER_LIMIT=8      # Số paper mặc định
AI_NEWS_OPENAI_MODEL=gpt-4o-mini
AI_NEWS_GEMINI_MODEL=gemini-2.0-flash
```

## 🤝 Đóng góp

Pull requests are welcome! 🎉

## 📝 License

MIT License - xem file `LICENSE`.

---

**Tự động hóa bản tin AI với <3 phút setup!** 🚀