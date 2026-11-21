# Test log

## Phase 01

| Check | Result |
| --- | --- |
| Backend pytest on Python 3.12.10 | 5 passed: route versioning, safe validation and unexpected errors, profile isolation/precedence, invalid profile rejection. |
| Backend import check | 34 modules imported; no local import cycles or forbidden core imports. |
| Live Uvicorn smoke test | HTTP 200 with `{"status":"ok"}`; verified structured startup event. |
| Next.js build on Node.js 24.11.1 | Passed production compilation, Tailwind processing and TypeScript checks. |
| Live Next.js production smoke test | HTTP 200; placeholder rendered; server-only API client successfully called live FastAPI with an overridden base URL. |
| shadcn/ui CLI | Detected Next.js App Router, React Server Components, Tailwind v4, and component aliases. |
| npm audit | No production dependency advisories reported; four moderate development advisories in the shadcn CLI dependency chain. |

No final test failures. No browser automation or tests for unimplemented domain features ran. The development-mode Next.js server was not separately smoke-tested.
