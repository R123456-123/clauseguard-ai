# ClauseGuard AI ⚖️🛡️

ClauseGuard AI is an AI-powered legal document assistant designed to help users understand, review, and navigate contracts more easily. The platform simplifies complex clauses, highlights legal risks, answers user questions using the uploaded contract as context, and supports negotiation preparation — while clearly reinforcing that it is informational support rather than formal legal advice.

## Challenge vertical

Chosen vertical: Legal Assistance & Access

This project addresses the challenge by making legal information more approachable for everyday users. It helps individuals and small businesses:

- simplify legal language
- identify risky clauses
- answer contract-related questions in plain English
- understand obligations, risks, and negotiation priorities
- prepare better questions for a lawyer

## Problem being solved

Legal documents are often dense, difficult to interpret, and full of hidden risks. Small businesses, freelancers, and individuals may not have the time or expertise to review contracts thoroughly before signing. ClauseGuard AI bridges that gap by turning a contract into a structured, understandable, and actionable review summary.

## Approach and logic

The solution combines:

- AI-powered contract analysis
- structured output validation
- PII redaction for safer handling of sensitive information
- contract-grounded Q&A
- negotiation guidance and next-step recommendations

The system works in a user-friendly flow:

1. The user uploads or pastes a contract.
2. The backend scrubbed personal data before sending to the model.
3. The AI extracts key clauses and ranks risk levels.
4. The user can ask direct questions such as:
   - What are the key risks in this contract?
   - Does this clause give the company too much control?
   - What should I negotiate before signing?
5. The app returns plain-English answers grounded in the contract text.
6. A legal disclaimer is appended to every response to reinforce safe usage.

## Key features

- Contract risk analysis with clause-by-clause breakdown
- Overall risk classification: low, medium, high, critical
- Plain-English explanations for each risky clause
- Negotiation prep pack with recommended actions
- Legal Q&A assistant using the uploaded document as context
- PII redaction for email, phone, and SSN-like patterns
- Responsive Next.js interface for upload and paste workflows

## How the solution works

### Frontend

Built with Next.js and TypeScript, the frontend provides:

- file upload or direct text paste
- loading and analysis states
- risk dashboard visualization
- legal assistant question interface

### Backend

Built with FastAPI, the backend exposes API routes for:

- contract risk analysis
- negotiation prep generation
- legal question answering
- health checks

### AI integration

Google Gemini is used to generate structured outputs from contract text. The system prompts the model to return JSON and then validates the results using Pydantic models. This keeps the answers consistent and reduces malformed outputs.

### Safety and responsible design

The application is intentionally designed to provide informational assistance instead of legal advice. It includes:

- PII scrubbing before AI calls
- strong schema validation
- mandatory legal disclaimer in responses
- emphasis on user understanding and preparation for professional legal review

## Assumptions

- The uploaded document is a legal or commercial agreement in text form.
- Users are seeking general clarification, negotiation insight, and risk awareness, not final legal counsel.
- The assistant may not detect every jurisdiction-specific legal nuance.
- Legal interpretation should still be reviewed by a qualified attorney when needed.

## Tech stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, Pydantic
- AI: Google Gemini API
- Testing: Pytest, FastAPI TestClient
- Security: PII redaction before external AI calls

## Project structure

```bash
backend/
  app/
    api/
    schemas/
    services/
    main.py
  tests/
frontend/
  src/
```

## Run locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment variable

Create a `.env` file inside the backend directory with:

```env
GEMINI_API_KEY=your_api_key_here
CORS_ORIGINS=http://localhost:3000,https://your-production-frontend.vercel.app
```

For deployment, set `CORS_ORIGINS` in the backend hosting platform to a
comma-separated list of trusted frontend origins. Do not use `*` in production.

Optional backend controls:

```env
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
CONTEXT_CACHE_TTL_SECONDS=900
CONTEXT_CACHE_MAX_ENTRIES=100
```

The backend returns a short-lived document ID after analysis. The frontend uses
that ID for follow-up legal questions so the scrubbed contract is not uploaded
again. The cache is intentionally bounded and in-memory for the hackathon
deployment; use Redis or another shared store when running multiple backend
instances.

### Quality checks

```bash
# Backend tests
cd backend
python -m pytest -q

# Frontend lint, build, and browser smoke tests
cd ../frontend
npm run lint
npm run build
npm run test:e2e

# Simple backend load check
cd ../backend
python tools/load_test.py --url http://localhost:8000/health --requests 50 --concurrency 10
```

## Important note

This project provides informational assistance and risk awareness support. It does not replace professional legal advice. Users should consult a qualified legal professional for final legal interpretation and advice.

## License

MIT License.
