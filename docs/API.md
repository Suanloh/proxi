# HTTP API

`GET /api/v1/health` returns HTTP 200 with `{"status":"ok"}`. This is liveness only: no database or external service is checked. Interactive OpenAPI documentation is at `/docs` on the backend.

Error responses use `{"error":{"code":"…","message":"…"}}`: `http_error` for HTTP errors, `validation_error` for invalid requests (422), and `internal_error` for unexpected failures (500). Raw exception details are not returned.
