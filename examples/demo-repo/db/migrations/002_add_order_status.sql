-- 002: order status. Existing rows become 'pending'.
ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled'));
CREATE INDEX orders_status_idx ON orders (status);
