# PersonaOS — Hệ điều hành AI Influencer 🚀

> Tạo và vận hành AI Influencer có danh tính, tính cách, ký ức, cuộc sống và khả năng kiếm tiền riêng.

---

## 🎯 Tầm nhìn

**PersonaOS** = Hệ điều hành tạo và vận hành AI Influencer:

- ✅ Danh tính riêng (tên, tuổi, nghề nghiệp)
- ✅ Tính cách riêng (traits, tone, quirks, fears)
- ✅ Ký ức riêng (đã nói gì, làm gì, trải qua gì)
- ✅ Cuộc sống riêng (timeline sự kiện, câu chuyện)
- ✅ Nội dung riêng (caption, hashtag, content plan)
- 🔜 Khả năng kiếm tiền riêng (affiliate, monetization)

---

## 🏗️ Kiến trúc hệ thống

```
PersonaOS/
├── backend/
│   ├── app/
│   │   ├── core/           # Database, LLM client, config
│   │   ├── models/          # ORM Models (Persona, Memory, Content, ...)
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── engine/          # AI Engines (trái tim của hệ thống)
│   │   │   ├── persona_engine.py      # Phase 1: Tạo persona
│   │   │   ├── conversation_engine.py # Chat in-character
│   │   │   ├── memory_engine.py       # Phase 2: Ký ức
│   │   │   └── content_engine.py      # Phase 3: Nội dung
│   │   ├── services/        # Business logic layer
│   │   │   ├── persona_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── content_service.py
│   │   │   └── chat_service.py
│   │   ├── api/v1/          # REST API routes
│   │   │   ├── persona.py   # CRUD + AI generate
│   │   │   ├── memory.py    # Ký ức + sự kiện
│   │   │   ├── content.py   # Tạo nội dung
│   │   │   └── chat.py      # Chat với persona
│   │   ├── utils/           # Prompt templates, helpers
│   │   ├── config.py        # Settings
│   │   └── main.py          # FastAPI entry point
│   ├── requirements.txt
│   └── .env.example
```

### Thiết kế mở rộng

Mỗi giai đoạn là một **Engine** độc lập, đăng ký vào hệ thống qua router:

```python
# Thêm Publishing Engine khi đến Giai đoạn 4:
from app.api.v1.publishing import router as publishing_router
v1_router.include_router(publishing_router, tags=["Publishing"])
```

---

## 🚀 Cài đặt & Chạy

### Yêu cầu

- Python 3.11+
- OpenAI API Key (cho AI generation)
- pip

### Cài đặt

```bash
cd backend

# Tạo virtual environment
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (Mac/Linux)
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Copy và cấu hình biến môi trường
cp .env.example .env
# ✏️ Sửa OPENAI_API_KEY trong .env
```

### Chạy

```bash
# Development server
uvicorn app.main:app --reload --port 8000

# Hoặc
python -m uvicorn app.main:app --reload --port 8000
```

Mở browser: [http://localhost:8000/docs](http://localhost:8000/docs) để xem Swagger UI.

---

## 📖 API Usage

### Giai đoạn 1: Tạo Persona bằng AI

```bash
# Tạo persona từ concept ngắn
curl -X POST http://localhost:8000/api/v1/personas/generate \
  -H "Content-Type: application/json" \
  -d '{
    "concept": "Dev IT nữ 25t thích Nhật Bản, nuôi mèo, đang tiết kiệm đi Tokyo",
    "language": "vi"
  }'
```

**Kết quả:** AI tạo ra một persona hoàn chỉnh với:
- Tên, tuổi, nghề nghiệp
- Tính cách (traits, tone, quirks, fears)
- Sở thích, mục tiêu sống
- Câu chuyện quá khứ (backstory)

### Chat với Persona

```bash
# Trò chuyện với persona (họ trả lời in-character)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "uuid-cua-persona",
    "message": "Chị ơi, cuối tuần này chị định làm gì?"
  }'
```

### Giai đoạn 2: Quản lý Ký ức

```bash
# AI tạo timeline sự kiện cho persona
curl -X POST "http://localhost:8000/api/v1/personas/{id}/life-events/generate?count=3"
```

### Giai đoạn 3: Tạo Nội dung

```bash
# AI tạo caption phù hợp với persona
curl -X POST http://localhost:8000/api/v1/content/generate \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "uuid-cua-persona",
    "content_type": "caption"
  }'
```

---

## 🗺️ Lộ trình phát triển

| Giai đoạn | Engine | Mô tả | Trạng thái |
|-----------|--------|-------|------------|
| **1** | Persona Engine | Tạo nhân vật AI có danh tính, tính cách | ✅ Done |
| **2** | Memory Engine | Ký ức, timeline cuộc sống | ✅ Done |
| **3** | Content Engine | Tự động tạo caption, hashtag | ✅ Done |
| **4** | Publishing Engine | Đăng bài lên TikTok, IG, FB... | 🔜 Next |
| **5** | Community Engine | Auto reply comment, inbox | 🔜 Next |
| **6** | Trend Engine | Phát hiện xu hướng mạng xã hội | 📋 Plan |
| **7** | Monetization Engine | Affiliate, chọn sản phẩm | 📋 Plan |
| **8** | Revenue Engine | Tối ưu doanh thu bằng AI | 📋 Plan |
| **9** | Multi-Persona | Quản lý nhiều nhân vật cùng lúc | 📋 Plan |
| **10** | SaaS Platform | Cho thuê hệ thống | 📋 Plan |

---

## 🧠 Công nghệ

- **Backend**: FastAPI (async Python)
- **AI**: OpenAI GPT-4o (có thể swap sang Anthropic, local models)
- **Database**: SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Vector DB**: ChromaDB (cho semantic memory search)
- **Validation**: Pydantic v2

---

## 📐 Nguyên tắc thiết kế

1. **Modular** — Mỗi Engine là một module độc lập, dễ thêm/bớt
2. **LLM-agnostic** — Abstraction layer cho phép swap LLM provider
3. **DB-agnostic** — SQLAlchemy hỗ trợ SQLite lẫn PostgreSQL
4. **API-first** — Mọi tính năng đều có REST API
5. **Stateless Services** — Services không giữ state, nhận DB session từ DI
