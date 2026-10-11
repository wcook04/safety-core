# orders-service

A small orders API used to show doctrine-map on a realistic repository. It is not a real
service.

- `src/` holds the HTTP server and the order logic.
- `tests/` holds the tests (`npm test`).
- `db/migrations/` holds the SQL migrations, applied in order.
- `infra/` holds the Terraform for the database.
- `docs/` explains the design.

Copy `.env.example` to `.env` and fill in the values before running `npm start`.

The agent doctrine for this repository lives in `.doctrine/doctrine.toml`. From this
folder, `python3 ../../doctrine.py check` reports what holds, and
`python3 ../../doctrine.py explain db/migrations/002_add_order_status.sql` shows what an
agent receives there.
