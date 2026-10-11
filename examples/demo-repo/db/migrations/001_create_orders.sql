-- 001: the orders table.
CREATE TABLE orders (
    id          BIGSERIAL PRIMARY KEY,
    sku         TEXT        NOT NULL,
    quantity    INTEGER     NOT NULL CHECK (quantity > 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
