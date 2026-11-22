# D-004: Use Supabase PostgreSQL for persistence

**Status:** Accepted in Prompt 03; supersedes D-001 (SQLite).

Use Supabase PostgreSQL for application persistence, retaining SQLAlchemy and Alembic. Keep repository contracts and domain records independent of the database. Use disposable local PostgreSQL for integration tests to exercise the same dialect without touching hosted data.

Compared with SQLite, this requires PostgreSQL credentials, a managed connection for hosted deployments and a separate test instance. Alembic owns the private `proxi` schema; the frontend and the Supabase Data API do not access it directly. See the [database guide](../DATABASE.md) for setup and verification.
