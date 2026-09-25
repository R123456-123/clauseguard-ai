# ClauseGuard AI ⚖️🛡️

**AI-powered legal contract risk analysis tool** — Instantly identify risky clauses, assess contract exposure, and generate negotiation preparation packs using Google Gemini AI.

---

## Problem Statement

Legal contracts are dense, complex documents that often contain clauses with hidden risks — unfavorable termination terms, broad indemnification requirements, aggressive non-compete provisions, or ambiguous liability caps. Small businesses, freelancers, and individuals frequently sign contracts without fully understanding these risks, leading to costly legal disputes.

**ClauseGuard AI** solves this by providing instant, AI-powered contract risk analysis that:

- **Extracts and classifies** every significant clause in a contract
- **Assigns risk levels** (Low → Critical) with clear explanations
- **Generates actionable recommendations** for each risky clause
- **Produces negotiation prep packs** with alternative language suggestions
- **Scrubs PII** before any data reaches external AI services

> ⚠️ **Disclaimer:** ClauseGuard AI provides informational assistance only and does not constitute formal legal advice. Always consult a qualified attorney.

---

## Architecture

```
┌─────────────────────┐     HTTP/JSON     ┌──────────────────────────┐
│   Next.js Frontend  │ ◄──────────────► │   FastAPI Backend        │
│   (TypeScript +     │                   │                          │
│    Tailwind CSS)    │                   │  ┌────────────────────┐  │
│                     │                   │  │  PII Scrubber      │  │
│  • FileUpload       │                   │  │  (Regex Redaction) │  │
│  • RiskDashboard    │                   │  └────────┬───────────┘  │
│  • Loading States   │                   │           │              │
└─────────────────────┘                   │  ┌────────▼───────────┐  │
                                          │  │  Gemini Service    │  │
                                          │  │  (gemini-1.5-flash)│  │
                                          │  └────────┬───────────┘  │
                                          │           │              │
                                          │  ┌────────▼───────────┐  │
                                          │  │  Pydantic Schemas  │  │
                                          │  │  (Strict Typing)   │  │
                                          │  └────────────────────┘  │
                                          └──────────────────────────┘
                                                      │
                                                      ▼
                                          ┌──────────────────────────┐
                                          │   Google Gemini API      │
                                          │   (gemini-1.5-flash)     │
                                          └──────────────────────────┘
```

### Data Flow

1. User uploads contract text via the **Next.js** frontend
2. Frontend sends `POST` to FastAPI backend (`/api/v1/upload-contract`)
3. **PII Scrubber** redacts emails, phone numbers, and SSN-format data
4. Sanitized text is sent to **Google Gemini AI** with structured JSON prompts
5. Gemini returns clause-by-clause risk analysis
6. Backend validates response via **Pydantic** schemas, appends legal disclaimer
7. Frontend renders interactive **Risk Dashboard** with color-coded risk levels

---

## GenAI Integration Mapping

| Feature                  | GenAI Component          | Purpose                                          |
| ------------------------ | ------------------------ | ------------------------------------------------ |
| Contract Risk Analysis   | Gemini 1.5 Flash         | Extract clauses, classify risk levels, explain risks |
| Prep Pack Generation     | Gemini 1.5 Flash         | Generate negotiation points & alternative language |
| Structured Output        | `response_mime_type=json` | Enforce JSON schema compliance from AI responses |
| PII Protection           | Regex Scrubber (pre-AI)  | Remove personal data before API transmission     |
| Safety Guardrails        | Pydantic Validation      | Validate AI output structure, enforce disclaimer |

---

## Tech Stack

| Layer       | Technology                        |
| ----------- | --------------------------------- |
| Frontend    | Next.js 14, TypeScript, Tailwind CSS |
| Backend     | Python 3.11+, FastAPI, Pydantic v2 |
| AI Engine   | Google Gemini API (gemini-1.5-flash) |
| Testing     | Pytest, FastAPI TestClient         |
| Security    | PII Scrubbing, Input Validation    |

---

## Run Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Running Tests

```bash
cd backend
pytest tests/ -v --tb=short
```

### Environment Variables

Create a `backend/.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## API Endpoints

| Method | Endpoint                      | Description                          |
| ------ | ----------------------------- | ------------------------------------ |
| POST   | `/api/v1/upload-contract`     | Analyze contract for legal risks     |
| POST   | `/api/v1/generate-prep-pack`  | Generate negotiation preparation pack |
| GET    | `/health`                     | Health check endpoint                |

---

## License

MIT License — See [LICENSE](./LICENSE) for details.
