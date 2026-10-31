"""doctrine.py trace: a session's hook record as ordered steps joined to routes, places and principles."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_hooks_support import ROOT, HookCase, fake_github_token, hooks  # noqa: E402

import doctrine  # noqa: E402


class TraceCase(HookCase):
    """A session recorded through the real hooks, the way Claude Code would call them."""

    def call(self, tool: str, tool_use_id: str, code: int | None = 0, **tool_input):
        """PreToolUse, then the PostToolUse record when the call ran (code None: it did not run)."""
        out = hooks.handle(self.payload("PreToolUse", tool_name=tool, tool_use_id=tool_use_id, tool_input=tool_input))
        if code is None:
            return out
        if code == 0:
            hooks.handle(self.payload("PostToolUse", tool_name=tool, tool_use_id=tool_use_id, tool_input=tool_input,
                                      tool_response={"interrupted": False}))
        else:
            hooks.handle(self.payload("PostToolUseFailure", tool_name=tool, tool_use_id=tool_use_id, tool_input=tool_input,
                                      error=f"Exit code {code}\nfailed", is_interrupt=False))
        return out

    def session_folder(self) -> Path:
        return self.repo / ".doctrine/sessions" / self.session

    def record_the_invented_setting_session(self):
        """The shape recorded on 18 Oct 2026: a refused commit, then a retry with an invented setting."""
        self.call("Read", "t1", file_path=str(self.repo / "src/app.py"))
        self.write("src/app.py", "def add(a, b):\n    return a + b  # fixed\n")
        self.call("Edit", "t2", file_path=str(self.repo / "src/app.py"), old_string="b\n", new_string="b  # fixed\n")
        self.call("Bash", "t3", code=1, command=f"cd {self.repo} && git commit -am 'Fix typo'")
        self.call("Read", "t4", file_path=str(self.repo / "tests/test_app.py"))
        self.call("Edit", "t5", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b")
        asked = self.call("Bash", "t6", code=None, command='TALLY_RATES_URL="http://localhost:8000" git commit -am "Fix typo"')
        self.assertEqual(((asked or {}).get("hookSpecificOutput") or {}).get("permissionDecision"), "ask")
        hooks.handle(self.payload("Stop", last_assistant_message="Done! I fixed the typo.", stop_hook_active=False))

    def trace(self, **kw) -> dict:
        return doctrine.build_trace(self.session_folder(), doctrine.open_repo(self.repo / "doctrine.toml"), **kw)


class BuildTrace(TraceCase):
    def test_steps_follow_the_session_and_join_records_of_one_call(self):
        self.record_the_invented_setting_session()
        t = self.trace()
        self.assertEqual(t["schema"], "doctrine-map/trace@1")
        kinds = [(s["kind"], s["ran"]) for s in t["steps"]]
        self.assertEqual(kinds, [("read", True), ("edit", True), ("command", True), ("read", True), ("edit", True),
                                 ("command", False), ("stop", None)])
        self.assertEqual([s["n"] for s in t["steps"]], list(range(1, 8)))
        self.assertTrue(all(a["at"] <= b["at"] for a, b in zip(t["steps"], t["steps"][1:])))
        failed = t["steps"][2]
        self.assertEqual((failed["exit"], failed["status"]), (1, "failed"))
        self.assertIn(("receipts", "remind"), [(d["check"], d["decision"]) for d in failed["decisions"]])
        retry = t["steps"][5]
        self.assertEqual([(d["check"], d["decision"], d["principles"]) for d in retry["decisions"]], [("bypass_checks", "ask", ["P1"])])
        self.assertIn("TALLY_RATES_URL", retry["label"])

    def test_files_carry_their_routes_and_places_and_reminders_their_principles(self):
        self.record_the_invented_setting_session()
        t = self.trace()
        test_edit = t["steps"][4]
        self.assertEqual(test_edit["files"], [{"path": "tests/test_app.py", "how": "edited", "routes": ["route:tests"],
                                               "place": "place:tests"}])
        self.assertEqual(t["steps"][3]["decisions"], [], "the tests route is delivered on edits, not reads")
        reminder = [d for d in test_edit["decisions"] if d["check"] == "reminders"]
        self.assertEqual(reminder and reminder[0]["routes"], ["route:tests"], "the edit delivered the tests reminder")
        self.assertIn("P7", reminder[0]["principles"])
        self.assertEqual(t["touched"]["places"], ["place:src", "place:tests"])
        self.assertIn("route:tests", t["touched"]["routes"])
        self.assertIn("P7", t["principles"]["reached_agent"])
        self.assertEqual(t["principles"]["asked_person"], ["P1"])
        self.assertEqual(t["counts"]["not_run"], 1)
        self.assertEqual(t["counts"]["ask"], 1)

    def test_no_absolute_local_path_or_secret_leaves_the_machine(self):
        self.record_the_invented_setting_session()
        self.call("Bash", "t9", command=f"curl -H 'Authorization: {fake_github_token()}' {self.repo}/x")
        text = json.dumps(self.trace())
        self.assertNotIn(str(self.repo), text)
        self.assertNotIn(os.path.expanduser("~") + "/", text)
        self.assertNotIn(fake_github_token(), text)
        self.assertIn("cd . && git commit", text)

    def test_graph_is_embedded_unless_left_out(self):
        self.record_the_invented_setting_session()
        self.assertEqual(self.trace()["graph"]["schema"], "doctrine-map/graph@1")
        self.assertNotIn("graph", self.trace(include_graph=False))

    def test_sessions_recorded_before_the_decision_log_use_once_markers(self):
        once = self.session_folder() / "once"
        once.mkdir(parents=True)
        os.close(os.open(once / ("route-tests-" + "0" * 10), os.O_CREAT | os.O_WRONLY))
        (self.session_folder() / "started").write_text(str(time.time() - 5))
        t = self.trace()
        self.assertEqual(len(t["steps"]), 1)
        step = t["steps"][0]
        self.assertEqual((step["kind"], step["routes"]), ("reminder", ["route:tests"]))
        self.assertEqual(step["decisions"][0]["from"], "once-marker")
        self.assertIn("P7", step["decisions"][0]["principles"])

    def test_without_a_doctrine_steps_have_no_routes(self):
        self.record_the_invented_setting_session()
        t = doctrine.build_trace(self.session_folder())
        self.assertEqual(len(t["steps"]), 7)
        self.assertNotIn("graph", t)
        self.assertEqual(t["steps"][4]["files"][0]["routes"], [])


class TraceCli(TraceCase):
    def cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = doctrine.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_trace_writes_a_file_and_map_draws_it(self):
        self.record_the_invented_setting_session()
        target = self.base / "trace.json"
        code, out, err = self.cli("trace", str(self.session_folder()), "--out", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("checks asked 1", out)
        self.assertEqual(json.loads(target.read_text())["counts"]["steps"], 7)
        page = self.base / "map.html"
        code, out, err = self.cli("map", "--doctrine", str(self.repo / "doctrine.toml"), "--trace", str(target), "--out", str(page))
        self.assertEqual(code, 0, err)
        html = page.read_text()
        inner = html.split('<script id="doctrine-trace" type="application/json">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(inner)["session"], self.session)
        self.assertNotIn("<", inner, "markup in the trace cannot close the script element")

    def test_trace_to_standard_output_and_errors(self):
        self.record_the_invented_setting_session()
        code, out, _ = self.cli("trace", str(self.session_folder()), "--no-graph")
        self.assertEqual((code, json.loads(out)["schema"]), (0, "doctrine-map/trace@1"))
        code, _, err = self.cli("trace", str(self.base / "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("not a session folder", err)
        (self.base / "bad.json").write_text('{"schema": "something-else"}')
        code, _, err = self.cli("map", "--doctrine", str(self.repo / "doctrine.toml"), "--trace", str(self.base / "bad.json"),
                                "--out", str(self.base / "m.html"))
        self.assertEqual(code, 2)
        self.assertIn("is not a doctrine-map/trace@1 file", err)

    def test_the_map_server_serves_a_trace(self):
        import http.client
        import threading
        self.record_the_invented_setting_session()
        trace = self.trace(include_graph=False)
        server = doctrine.make_server(self.repo / "doctrine.toml", port=0, interval=0.1, trace=trace)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.live.close(), server.shutdown(), server.server_close()))
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", "/trace.json")
        response = conn.getresponse()
        self.assertEqual((response.status, json.loads(response.read())["session"]), (200, self.session))
        conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("HEAD", "/trace.json")
        response = conn.getresponse()
        self.assertEqual((response.status, response.getheader("Content-Type"), response.read()),
                         (200, "application/json", b""))
        self.assertGreater(int(response.getheader("Content-Length")), 0)
        conn.close()


class SampleTraces(unittest.TestCase):
    """The recorded examples in docs/reference/ stay readable by the viewer and free of local paths."""

    def test_samples(self):
        samples = sorted((ROOT / "docs" / "reference").glob("agent-runs-*-trace-*.json"))
        self.assertTrue(samples, "no sample trace")
        for path in samples:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                t = json.loads(text)
                self.assertEqual(t["schema"], "doctrine-map/trace@1")
                self.assertEqual(t["graph"]["schema"], "doctrine-map/graph@1")
                self.assertNotIn("/Users/", text)
                self.assertNotIn("/home/", text)
                self.assertEqual(hooks.shapes(text), [])
                ids = {n["id"] for n in t["graph"]["nodes"]}
                for step in t["steps"]:
                    self.assertTrue(set(step["routes"]) <= ids and set(step["places"]) <= ids, step)


if __name__ == "__main__":
    unittest.main()
