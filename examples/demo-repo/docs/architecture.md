# Architecture

The service is one Node.js process in front of one PostgreSQL database.

- `src/server.js` parses requests and maps errors to HTTP status codes.
- `src/orders.js` holds the order rules. Validation lives here so the tests can reach it
  without a database.
- `src/db.js` opens a single connection pool from `DATABASE_URL`.

Schema changes go in `db/migrations/` as numbered SQL files. They are applied in order and
never edited after they reach a shared database. The database itself is described in
`infra/main.tf`; it has deletion protection and keeps a final snapshot.
