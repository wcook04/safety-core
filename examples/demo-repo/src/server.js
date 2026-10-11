// HTTP entry point: GET /orders lists orders, POST /orders creates one.
const http = require("node:http");
const { createOrder, listOrders } = require("./orders");

const port = Number(process.env.PORT || 3000);

function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/orders") {
      return send(res, 200, await listOrders());
    }
    if (req.method === "POST" && req.url === "/orders") {
      let raw = "";
      for await (const chunk of req) raw += chunk;
      return send(res, 201, await createOrder(JSON.parse(raw || "{}")));
    }
    send(res, 404, { error: "not found" });
  } catch (err) {
    send(res, err.status || 500, { error: err.message });
  }
});

if (require.main === module) {
  server.listen(port, () => console.log(`orders-service listening on ${port}`));
}

module.exports = { server };
