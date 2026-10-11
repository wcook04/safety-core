// Order rules: validation and the two queries the API needs.
const { query } = require("./db");

const STATUSES = ["pending", "paid", "shipped", "cancelled"];

function validate(input) {
  const quantity = Number(input.quantity);
  if (!input.sku || typeof input.sku !== "string") {
    throw Object.assign(new Error("sku is required"), { status: 400 });
  }
  if (!Number.isInteger(quantity) || quantity < 1) {
    throw Object.assign(new Error("quantity must be a whole number of at least 1"), { status: 400 });
  }
  return { sku: input.sku.trim(), quantity };
}

async function createOrder(input) {
  const order = validate(input);
  const rows = await query(
    "INSERT INTO orders (sku, quantity, status) VALUES ($1, $2, 'pending') RETURNING *",
    [order.sku, order.quantity],
  );
  return rows[0];
}

async function listOrders() {
  return query("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100");
}

module.exports = { STATUSES, validate, createOrder, listOrders };
