"""map --serve: the viewer, /graph.json, and an /events message after the doctrine changes."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import threading
import time
import unittest
from unittest import mock

from doctrine_testkit import DEMO_FILES, RepoTestCase, doctrine

VIEWER = '<html><head></head><body><script id="doctrine-graph" type="application/json"></script></body></html>'


class Serve(RepoTestCase):
    def setUp(self):
        self.root = self.make_repo(DEMO_FILES)
        (self.root / ".doctrine" / "map.html").write_text(VIEWER)
        self.example = self.root / "example.json"
        self.example.write_text(json.dumps({"schema": doctrine.TRACE_SCHEMA, "steps": []}))
        with mock.patch.object(doctrine, "EXAMPLE_TRACE", self.example):
            self.server = doctrine.make_server(self.root / ".doctrine" / "doctrine.toml", port=0, interval=0.1)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.live.close()
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response.status, response.getheader("Content-Type"), response.getheader("Content-Length"), body

    def get(self, path):
        status, kind, _, body = self.request("GET", path)
        return status, kind, body

    def test_head_matches_get_without_sending_a_body(self):
        for path in ("/", "/index.html", "/map.html", "/graph.json", "/example-trace.json", "/nothing", "/trace.json"):
            with self.subTest(path=path):
                status, kind, length, body = self.request("GET", path)
                self.assertEqual(self.request("HEAD", path), (status, kind, length, b""))
                self.assertEqual(int(length), len(body))
        self.assertEqual(json.loads(self.get("/example-trace.json")[2])["schema"], doctrine.TRACE_SCHEMA)
        status, kind, _, body = self.request("HEAD", "/events")
        self.assertEqual((status, kind, body), (200, "text/event-stream", b""))

    def test_example_endpoint_does_not_serve_arbitrary_repository_files(self):
        for path in ("/example.json", "/docs/reference/agent-runs-20261018-trace-hook.json",
                     "/../example.json", "/%2e%2e/example.json", "/example-trace.json/../example.json"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)
                self.assertEqual(self.request("HEAD", path)[0], 404)

    def test_missing_bundled_example_returns_not_found_for_head_and_get(self):
        self.stop()
        self.example.unlink()
        with mock.patch.object(doctrine, "EXAMPLE_TRACE", self.example):
            self.server = doctrine.make_server(self.root / ".doctrine" / "doctrine.toml", port=0, interval=0.1)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.assertEqual(self.get("/example-trace.json")[0], 404)
        status, _, _, body = self.request("HEAD", "/example-trace.json")
        self.assertEqual((status, body), (404, b""))
        self.assertEqual(self.get("/")[0], 200)

    def test_serves_the_graph_and_the_viewer(self):
        status, kind, body = self.get("/graph.json")
        self.assertEqual((status, kind), (200, "application/json"))
        self.assertEqual(json.loads(body)["schema"], "doctrine-map/graph@1")
        status, kind, body = self.get("/")
        self.assertEqual((status, body.decode()), (200, VIEWER))
        self.assertEqual(self.get("/nothing")[0], 404)

    def test_an_edit_to_the_doctrine_sends_an_event(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/events")
        response = conn.getresponse()
        self.assertEqual(response.getheader("Content-Type"), "text/event-stream")
        self.assertEqual(response.fp.readline(), b": connected\n")
        path = self.root / ".doctrine" / "doctrine.toml"
        path.write_text(path.read_text().replace("A small doctrine for tests.", "A changed summary."))
        deadline = time.monotonic() + 5
        event = b""
        while time.monotonic() < deadline and not event.startswith(b"data:"):
            event = response.fp.readline()
        conn.close()
        self.assertTrue(event.startswith(b"data: "), event)
        self.assertIn("rebuilt", json.loads(event[6:]))
        status, _, body = self.get("/graph.json")
        self.assertEqual(json.loads(body)["doctrine"]["summary"], "A changed summary.")

    def test_a_broken_edit_keeps_the_last_good_graph(self):
        path = self.root / ".doctrine" / "doctrine.toml"
        before = self.get("/graph.json")[2]
        reported = threading.Event()

        class Diagnostic(io.StringIO):
            def write(self, text):
                size = super().write(text)
                if text.endswith("\n") and "keeping the last good graph" in self.getvalue():
                    reported.set()
                return size

        with contextlib.redirect_stderr(Diagnostic()) as err:
            path.write_text("this is [not toml")
            self.assertTrue(reported.wait(10), "watcher did not report the rejected TOML edit")
        self.assertIn("keeping the last good graph", err.getvalue())
        self.assertEqual(self.get("/graph.json")[2], before)


if __name__ == "__main__":
    unittest.main()
