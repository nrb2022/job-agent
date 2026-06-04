# 🤖 JobAgent — AI-Powered Job Application Automator

> Upload your CV. Set your preferences. Let the agent apply while you sleep.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green.svg)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.44-orange.svg)](https://playwright.dev)

**JobAgent** is an open-source agentic platform that:
1. **Parses your CV** using Claude AI to extract skills, experience, and preferences
2. **Browses job portals** (LinkedIn, Indeed, Naukri, Glassdoor) using Playwright
3. **Matches suitable jobs** based on your profile and location preferences
4. **Auto-fills and submits** applications intelligently
5. **Tracks everything** in a clean dashboard

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 CV Parser | Extracts structured data from PDF/DOCX using Claude AI |
| 🔍 Job Discovery | Scrapes LinkedIn, Indeed, Naukri, Glassdoor |
| 🧠 AI Matching | Scores job fit using Claude (skills, experience, location) |
| 🤖 Auto Apply | Playwright agent fills forms, uploads CV, submits |
| 📊 Dashboard | Tracks applied / matched / pending jobs |
| 🌍 Multi-location | Apply in multiple cities/countries simultaneously |
| 🔒 Credential Vault | Encrypted local storage of portal credentials |
| 📬 Notifications | Email/webhook alerts on application status |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│         (CV Upload · Preferences · Dashboard)        │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                     │
│   ┌──────────┐  ┌───────────┐  ┌────────────────┐   │
│   │CV Parser │  │Job Matcher│  │ Session Manager│   │
│   │(Claude)  │  │(Claude)   │  │  (SQLite/Redis)│   │
│   └──────────┘  └───────────┘  └────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │ Async Task Queue (Celery/ARQ)
┌──────────────────────▼──────────────────────────────┐
│                  Agent Workers                       │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐  │
│  │LinkedIn  │ │ Indeed  │ │  Naukri  │ │Glassdoor│  │
│  │ Agent    │ │  Agent  │ │  Agent   │ │  Agent  │  │
│  └──────────┘ └─────────┘ └──────────┘ └────────┘  │
│           (Playwright + Claude Vision)               │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Anthropic API Key](https://console.anthropic.com)

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/job-agent.git
cd job-agent

# Backend
cd backend
pip install -r requirements.txt
playwright install chromium

# Frontend
cd ../frontend
npm install
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and portal credentials
```

### 3. Run
```bash
# Terminal 1 — Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## 📁 Project Structure

```
job-agent/
├── backend/
│   ├── main.py               # FastAPI app + WebSocket
│   ├── cv_parser.py          # Claude-powered CV extraction
│   ├── job_matcher.py        # AI job-profile scoring
│   ├── agent_runner.py       # Orchestrates apply agents
│   ├── models.py             # Pydantic schemas
│   ├── database.py           # SQLite via SQLModel
│   ├── config.py             # Settings & env vars
│   ├── portals/
│   │   ├── base_portal.py    # Abstract portal class
│   │   ├── linkedin.py       # LinkedIn automation
│   │   ├── indeed.py         # Indeed automation
│   │   ├── naukri.py         # Naukri automation
│   │   └── glassdoor.py      # Glassdoor automation
│   └── utils/
│       ├── encryption.py     # Credential encryption
│       └── notifier.py       # Email/webhook notifications
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Setup.jsx
│   │   │   └── Applications.jsx
│   │   └── components/
│   │       ├── CVUpload.jsx
│   │       ├── PortalConfig.jsx
│   │       ├── PreferenceForm.jsx
│   │       └── ApplicationCard.jsx
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚙️ Configuration (.env)

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Job Portal Credentials (stored encrypted)
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword
INDEED_EMAIL=your@email.com
INDEED_PASSWORD=yourpassword
NAUKRI_EMAIL=your@email.com
NAUKRI_PASSWORD=yourpassword

# Optional
DATABASE_URL=sqlite:///./jobagent.db
NOTIFICATION_EMAIL=your@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
ENCRYPTION_KEY=generate-with-python-secrets
```

---

## 🛡️ Ethics & Safety

- **Rate limiting**: Agents respect portal rate limits (configurable delays)
- **Human review mode**: Optionally review each application before submit
- **No credential sharing**: All credentials stay local, encrypted at rest
- **Respectful crawling**: Obeys robots.txt where possible
- **Application cap**: Set a daily/weekly limit to avoid spam

---

## 🤝 Contributing

Contributions welcome! Priority areas:
- New portal adapters (Wellfound, Workday, Greenhouse)
- Resume tailoring per job description
- Cover letter AI generation
- Interview scheduling integration

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

MIT — free to use, fork, and extend.

---

*Built with ❤️ using Claude AI + Playwright*
