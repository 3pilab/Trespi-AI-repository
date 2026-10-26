"""End-to-end tests for RDD snapshots and the CLI, on real git in throwaway repositories.

Every repository gets an isolated global config through GIT_CONFIG_GLOBAL, so no test
reads or writes the developer's own git configuration.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import candidate as cand
import rdd


class GitRepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        self.global_config = base / "gitconfig"
        self.global_config.write_text("[user]\n\tname = T\n\temail = t@t.test\n", encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(self.global_config),
                                                "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()
        self.repo = base / "demo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True,
                              text=True).stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str = "c") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def cli(self, *argv: str) -> tuple[int, dict | str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = rdd.main(["--cwd", str(self.repo), "--json", *argv])
            except SystemExit as exc:
                code = int(exc.code)
        try:
            return code, json.loads(out.getvalue())
        except ValueError:
            return code, out.getvalue() + err.getvalue()

    def feature_branch(self) -> str:
        self.write("README.md", "hello\n")
        base = self.commit("init")
        self.git("checkout", "-q", "-b", "feature")
        return base


class SnapshotTests(GitRepoCase):
    def test_snapshot_touches_neither_worktree_nor_index(self):
        self.write("README.md", "hello\n")
        self.commit()
        self.write("README.md", "hello again\n")
        self.write("notes.txt", "new\n")
        before = (self.git("status", "--porcelain"), (self.repo / ".git" / "index").read_bytes())
        snap = cand.take_snapshot(self.repo)
        after = (self.git("status", "--porcelain"), (self.repo / ".git" / "index").read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(sorted(cand.changed_paths(self.repo, snap.base_tree, snap.tree)), ["README.md", "notes.txt"])

    def test_racily_clean_same_size_edit_is_seen(self):
        # Pin every timestamp git compares so the racy case is deterministic: the edit keeps
        # size and mtime, and only the index mtime tells git to re-read the file.
        self.git("config", "core.trustctime", "false")
        self.git("config", "core.checkStat", "minimal")
        stamp = 1_000_000_000
        target = self.repo / "src" / "app.py"
        self.write("src/app.py", "value = 10\n")
        os.utime(target, (stamp, stamp))
        self.commit()
        os.utime(self.repo / ".git" / "index", (stamp, stamp))
        self.write("src/app.py", "value = 11\n")
        os.utime(target, (stamp, stamp))
        snap = cand.take_snapshot(self.repo)
        self.assertEqual(cand.changed_paths(self.repo, snap.base_tree, snap.tree), ["src/app.py"])

    def test_staged_workspace_and_committed_projections_separate_paths(self):
        self.write("base.txt", "v1\n")
        self.commit()
        self.write("second.txt", "new commit\n")
        self.commit()
        self.write("staged-only.txt", "staged\n")
        self.git("add", "staged-only.txt")
        self.write("workspace-only.txt", "dirty\n")
        staged = cand.take_snapshot(self.repo, cand.STAGED)
        workspace = cand.take_snapshot(self.repo, cand.WORKSPACE)
        committed = cand.take_snapshot(self.repo, cand.COMMITTED, "HEAD~1")
        self.assertEqual(cand.changed_paths(self.repo, staged.base_tree, staged.tree), ["staged-only.txt"])
        self.assertEqual(sorted(cand.changed_paths(self.repo, workspace.base_tree, workspace.tree)),
                         ["staged-only.txt", "workspace-only.txt"])
        self.assertEqual(cand.changed_paths(self.repo, committed.base_tree, committed.tree), ["second.txt"])

    def test_unborn_repository_can_be_snapshotted(self):
        self.write("main.py", "print('x')\n")
        snap = cand.take_snapshot(self.repo)
        self.assertIsNone(snap.base_commit)
        self.assertEqual(cand.changed_paths(self.repo, snap.base_tree, snap.tree), ["main.py"])

    def test_changes_carry_modes_and_passive_content(self):
        base = self.feature_branch()
        self.write("bin/run.py", "print(1)\n")
        self.commit()
        os.chmod(self.repo / "bin" / "run.py", 0o755)
        self.write("docs/guide.md", "# Guide\n")
        self.commit()
        snap = cand.take_snapshot(self.repo, cand.COMMITTED, base)
        found = {c.path: c for c in cand.changes(self.repo, snap.base_tree, snap.tree, (".md",))}
        self.assertEqual(found["docs/guide.md"].content, b"# Guide\n")
        self.assertIsNone(found["bin/run.py"].content)


class WorkUnitFlowTests(GitRepoCase):
    def test_passive_commit_needs_no_review(self):
        base = self.feature_branch()
        self.write("docs/guide.md", "# Guide\n\nprose\n")
        self.commit()
        code, out = self.cli("assess", "--committed-only")
        self.assertEqual((code, out["risk"], out["review_due"], out["review_due_reason"]), (0, "passive", False, "passive"))
        self.assertEqual(out["candidate"]["base_commit"], base)

    def test_medium_commit_full_cycle_advances_the_boundary(self):
        self.feature_branch()
        self.write("src/app.py", "def f():\n    return 1\n" + "".join(f"\ndef g{i}():\n    return {i}\n" for i in range(6)))
        self.commit()
        code, out = self.cli("assess", "--committed-only")
        self.assertEqual((out["risk"], out["review_due_reason"], out["changed_lines"]), ("medium", "under_budget", 20))
        self.assertEqual(self.cli("start", "--committed-only")[1]["code"], "lens_required")
        self.assertEqual(self.cli("start", "--committed-only", "--lens", "reliability")[1]["code"], "consent_required")
        code, out = self.cli("start", "--committed-only", "--lens", "reliability", "--consent", "granted")
        self.assertEqual((code, out["review"]["lenses"], out["next"]["kind"]), (0, ["reliability"], "collect"))
        ledger_file = self.repo.parent / "r3.json"
        ledger_file.write_text(json.dumps([{"id": "R3-001", "location": "src/app.py:2", "severity": "CRITICAL",
                                            "evidence": "f has no test"}]), encoding="utf-8")
        code, out = self.cli("capture", "--lens", "reliability", "--findings-file", str(ledger_file),
                             "--evidence", "one sweep of the diff")
        self.assertEqual((code, out["next"]["kind"], out["next"]["refuter"]), (0, "refute", "general"))
        verdicts = self.repo.parent / "v.json"
        verdicts.write_text(json.dumps([{"finding_id": "R3-001", "outcome": "corroborated"}]), encoding="utf-8")
        code, out = self.cli("refute", "--refuter", "general", "--results-file", str(verdicts), "--evidence", "holds")
        self.assertEqual(out["next"]["kind"], "validate")
        self.write("tests/test_app.py", "from src.app import f\n\ndef test_f():\n    assert f() == 1\n")
        fixed = self.commit("add test")
        code, out = self.cli("validate", "--verdict", "pass", "--evidence", "pytest: 1 passed")
        self.assertEqual((code, out["review"]["state"], out["review"]["correction"]), (0, "closed", {
            "budget": 10, "surviving": ["R3-001"], "spent": 4}))
        self.assertEqual(self.cli("boundary", "show")[1]["boundary"], fixed)
        self.assertEqual(self.cli("assess", "--committed-only")[1]["code"], "empty_candidate")

    def test_clean_tree_is_an_empty_candidate(self):
        self.feature_branch()
        code, out = self.cli("start", "--lens", "risk", "--consent", "granted")
        self.assertEqual((code, out["code"]), (3, "empty_candidate"))

    def test_high_risk_commit_is_due_with_a_next_transition(self):
        self.feature_branch()
        self.write("internal/auth/session.go", "package auth\nfunc CheckToken() {}\n")
        self.commit()
        code, out = self.cli("assess", "--committed-only")
        self.assertEqual((out["risk"], out["review_due"], out["review_due_reason"]), ("high", True, "high_risk"))
        self.assertIn("--committed-only --consent granted", out["next_transition"]["command"])

    def test_escalation_raises_a_medium_commit(self):
        self.feature_branch()
        self.write("src/queue.py", "lock = None\n")
        self.commit()
        code, out = self.cli("assess", "--committed-only", "--escalate-item", "4", "--escalate-reason", "new lock")
        self.assertEqual((out["risk"], out["review_due_reason"]), ("high", "high_risk"))
        code, out = self.cli("assess", "--committed-only", "--escalate-item", "4")
        self.assertEqual(out["code"], "escalation_reason_required")

    def test_closed_candidate_reports_already_reviewed(self):
        base = self.feature_branch()
        self.write("internal/auth/a.go", "package auth\n")
        self.commit()
        self.cli("start", "--committed-only", "--consent", "granted")
        for lens in ("risk", "readability", "reliability", "resilience"):
            self.cli("capture", "--lens", lens, "--no-findings", "--evidence", "one sweep")
        code, out = self.cli("assess", "--base-ref", base, "--committed-only")
        self.assertEqual((out["review_due"], out["review_due_reason"]), (False, "already_reviewed"))

    def test_workspace_write_after_start_makes_the_review_stale(self):
        self.feature_branch()
        self.write("src/app.py", "x = 1\n")
        self.cli("start", "--lens", "risk", "--consent", "granted")
        self.write("lint-report.txt", "lint output\n")
        code, out = self.cli("capture", "--lens", "risk", "--no-findings", "--evidence", "sweep")
        self.assertEqual((code, out["code"]), (3, "stale_target_identity"))
        self.assertEqual(self.cli("status", "--next")[1]["kind"], "stale")


class SwitchAndExportTests(GitRepoCase):
    def test_mode_off_refuses_start_and_names_the_way_back(self):
        self.write("src/app.py", "x = 1\n")
        self.cli("mode", "disable", "--scope", "global")
        self.cli("mode", "disable", "--scope", "clone")
        code, out = self.cli("start", "--lens", "risk", "--consent", "granted")
        self.assertEqual((code, out["code"]), (3, "mode_off"))
        self.assertLess(out["next_action"].index("--scope global"), out["next_action"].index("--scope clone"))

    def test_clone_scope_off_is_not_inherited_and_status_is_read_only(self):
        self.write("README.md", "x\n")
        self.commit()
        before = self.global_config.read_text(encoding="utf-8")
        self.assertEqual(self.cli("mode", "status")[1]["source"], "default")
        self.assertEqual(self.global_config.read_text(encoding="utf-8"), before)
        self.cli("mode", "disable", "--scope", "clone")
        other = self.repo.parent / "demo2"
        self.git("clone", "-q", str(self.repo), str(other), cwd=self.repo.parent)
        self.assertEqual(rdd.store.mode_status(other)["effective"], "on")

    def test_export_refuses_a_path_that_would_change_the_candidate(self):
        self.write("src/app.py", "x = 1\n")
        self.cli("start", "--lens", "risk", "--consent", "granted")
        self.assertEqual(self.cli("export", "--out", str(self.repo / "receipts.md"))[1]["code"],
                         "export_inside_candidate")
        self.assertEqual(self.cli("export", "--out", str(self.repo.parent / "out" / "receipts.md"))[0], 0)


if __name__ == "__main__":
    unittest.main()
