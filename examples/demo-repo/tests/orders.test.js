const test = require("node:test");
const assert = require("node:assert/strict");
const { validate, STATUSES } = require("../src/orders");

test("an order needs a sku and a whole quantity", () => {
  assert.deepEqual(validate({ sku: " A-100 ", quantity: "2" }), { sku: "A-100", quantity: 2 });
  assert.throws(() => validate({ quantity: 1 }), /sku is required/);
  assert.throws(() => validate({ sku: "A-100", quantity: 0 }), /at least 1/);
  assert.throws(() => validate({ sku: "A-100", quantity: 1.5 }), /whole number/);
});

test("orders start pending", () => {
  assert.equal(STATUSES[0], "pending");
});
