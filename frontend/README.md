## Medical triage frontend (MediBot)

This is a clean, self-contained WhatsApp-style triage chat UI.

### What’s included
- WhatsApp-style chat UI (mobile-first)
- Typing indicator
- Smooth scroll to latest message
- Weekly session limiting: **4 sessions per 7 days** using `localStorage` (`triage_sessions`)
- Anthropic Messages API call logic

### Setup
```bash
cd frontend
npm install
cp .env.example .env
```

#### Recommended (no API keys in frontend)
Set:
- `VITE_CHAT_MODE=proxy`
- `VITE_CHAT_PROXY_URL=<your backend chat endpoint>`

Then:

```bash
npm run dev
```

### Notes
- If you really need to call Anthropic directly (dev only), set `VITE_CHAT_MODE=anthropic` and provide:
  - `VITE_ANTHROPIC_API_KEY`
  - `VITE_ANTHROPIC_MODEL`
  This is **not recommended for production** because it exposes the key to browsers.

