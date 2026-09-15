# Security Policy

CyberSentinel AI is a portfolio/demo project. It is **not** a production
security tool and must not be pointed at real, live network infrastructure.

## Secret handling
- No API keys, passwords, or credentials are ever committed to this repository.
- All configuration is via environment variables, loaded through
  `backend/app/core/config.py` (`pydantic-settings`). See `.env.example`.
- `.env` is git-ignored. If a secret is ever committed by mistake, rotate it
  immediately and scrub it from git history (`git filter-repo` / BFG).

## Data handling
- All network/security event data shipped in `data/sample/` is **synthetic**,
  generated for this project. No real production logs, IPs, or credentials
  are included.
- Application logs redact request bodies and any field named `password`,
  `token`, `secret`, or `api_key` before writing.

## AI / LLM safety
- The system defaults to a local, offline mock LLM provider — no data ever
  leaves the machine unless `LLM_PROVIDER=openai_compatible` is explicitly
  configured with the operator's own key.
- Agents never execute arbitrary commands returned by an LLM. All simulated
  response actions (block IP, isolate host, etc.) are applied only to an
  in-memory/simulated environment, are allow-listed by action type, and
  require explicit human approval via the `/approve` API before being marked
  "executed."
- No destructive real-world network or system commands are ever issued.

## API security
- Input validation via Pydantic schemas on every endpoint.
- CORS is restricted to an explicit allow-list (`CORS_ALLOW_ORIGINS`).
- Basic per-IP rate limiting on write endpoints.
- Authentication: token-based auth is implemented for state-changing
  endpoints (see `docs/api.md`); this is demo-grade, not enterprise SSO.

## Reporting a vulnerability
This is a personal portfolio project. If you find an issue, please open a
GitHub issue describing it (do not include real credentials or sensitive
data in the report).
