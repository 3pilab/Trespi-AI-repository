"""Tests for ODD feature documents: structure checks, creation, mirror, and budget.

Structure cases drive `check` on documents written to a temporary directory. The
creation, mirror, and budget cases run real git in throwaway repositories with an
isolated global config.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import odd_tasks

VALID = """# Negative limit validation
Objective: reject negative limits · Branch: `fix/negative-limit` · Delivery: ask-on-risk · Runner: `npm test`

## Specs
S1. "GET /orders?limit=-1 returns 400 with `limit must be positive`". Acceptance: status 400, body message exact. Checks: unit test.
S2. Existing `limit=10` behavior is unchanged. Checks: regression test.

## Tasks
- [x] T1 (S1) inline · validator rejects negative limit · RED→GREEN · 1a2b3c4d
- [ ] T2 (S2) inline · pin existing limit behavior

## Log
L1 2026-10-23 user (verbatim): > GET /orders returns 500 when limit is negative; it should return 400
L2 2026-10-23 T1 evidence: RED `expected 400, got 500`; GREEN `npm test` 41 passed.
"""


def messages(text: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "feature.md"
        path.write_text(text, encoding="utf-8")
        return [f.message for f in odd_tasks.check(path)]


class CheckTests(unittest.TestCase):
    def test_valid_document_has_no_findings(self):
        self.assertEqual(messages(VALID), [])

    def test_sections_must_be_in_order_with_log_last(self):
        broken = VALID.replace("## Tasks", "## Tmp").replace("## Specs", "## Tasks").replace("## Tmp", "## Specs")
        self.assertTrue(any("Specs, Tasks, Log" in m for m in messages(broken)))
        trailing = VALID + "\n## Notes\nextra\n"
        found = messages(trailing)
        self.assertTrue(any("unexpected section" in m for m in found))
        self.assertTrue(any("must be the last section" in m for m in found))

    def test_header_needs_branch_delivery_and_runner(self):
        found = messages(VALID.replace(" · Runner: `npm test`", ""))
        self.assertIn("the header must name `Runner:`", found)
        found = messages(VALID.replace("Delivery: ask-on-risk", "Delivery: whatever"))
        self.assertTrue(any("Delivery must be one of" in m for m in found))

    def test_specs_must_be_numbered_without_gaps(self):
        found = messages(VALID.replace("S2. Existing", "S3. Existing").replace("(S2)", "(S3)"))
        self.assertTrue(any("missing S2" in m for m in found))

    def test_task_must_link_an_existing_spec_and_every_spec_needs_a_task(self):
        found = messages(VALID.replace("T2 (S2)", "T2 (S9)"))
        self.assertTrue(any("links S9" in m for m in found))
        self.assertIn("S2 has no task", found)

    def test_spec_ranges_and_lists_expand(self):
        self.assertEqual(odd_tasks.spec_ids("S2-S4"), [2, 3, 4])
        self.assertEqual(odd_tasks.spec_ids("S1, S3"), [1, 3])
        self.assertEqual(messages(VALID.replace("T1 (S1)", "T1 (S1-S2)").replace("- [ ] T2 (S2)", "- [ ] T2 (S1, S2)")), [])

    def test_checked_task_needs_evidence(self):
        found = messages(VALID.replace(" · RED→GREEN · 1a2b3c4d", ""))
        self.assertTrue(any("checked without a commit" in m for m in found))

    def test_task_ids_unique_and_routes_known(self):
        self.assertTrue(any("not unique" in m for m in messages(VALID.replace("T2 (S2)", "T1 (S2)"))))
        self.assertTrue(any("route must be" in m for m in messages(VALID.replace("T2 (S2) inline", "T2 (S2) solo"))))

    def test_log_starts_with_verbatim_l1_and_has_no_gaps(self):
        self.assertTrue(any("start with `L1`" in m for m in messages(VALID.replace("L1 2026", "L3 2026"))))
        self.assertTrue(any("verbatim" in m for m in messages(VALID.replace("(verbatim)", ""))))
        self.assertTrue(any("without gaps" in m for m in messages(VALID.replace("L2 2026", "L4 2026"))))

    def test_template_placeholders_are_findings_but_user_angle_brackets_are_not(self):
        self.assertIn("unfilled template placeholder", messages(odd_tasks.TEMPLATE.format(
            title="T", objective="o", branch="b", delivery="ask-on-risk", runner="r", today="2026-10-23", request="x")))
        self.assertEqual(messages(VALID.replace("returns 400", "returns <400 Bad Request>")), [])


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        config = base / "gitconfig"
        config.write_text("[user]\n\tname = T\n\temail = t@t.test\n", encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()
        self.repo = base / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.repo / "AGENTS.md").write_text("`AGENTIC_DOCS_ROOT=documentation`\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.cwd = mock.patch("pathlib.Path.cwd", return_value=self.repo)
        self.cwd.start()

    def tearDown(self):
        self.cwd.stop()
        self.env.stop()
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = odd_tasks.main(list(argv))
        return code, out.getvalue()


class CreationTests(RepoCase):
    def test_new_writes_under_the_docs_root_and_refuses_to_overwrite(self):
        code, _ = self.run_cli("new", "negative-limit", "--request", "fix it\nplease", "--objective", "o",
                               "--runner", "npm test")
        target = self.repo / "documentation" / "odd" / "tasks" / "negative-limit.md"
        self.assertEqual(code, 0)
        text = target.read_text(encoding="utf-8")
        self.assertIn("(verbatim): > fix it\n> please", text)
        self.assertIn("Branch: `main`", text)
        code, out = self.run_cli("new", "negative-limit", "--request", "x", "--objective", "o", "--runner", "r")
        self.assertEqual(code, 3)
        self.assertIn("never overwrite", out)

    def test_new_rejects_unsafe_feature_names(self):
        code, _ = self.run_cli("new", "../escape", "--request", "x", "--objective", "o", "--runner", "r")
        self.assertEqual(code, 2)


class MirrorTests(RepoCase):
    def test_mirror_lives_outside_the_worktree_and_detects_drift(self):
        doc = self.repo / "documentation" / "odd" / "tasks" / "f.md"
        doc.parent.mkdir(parents=True)
        doc.write_text(VALID, encoding="utf-8")
        code, out = self.run_cli("mirror", "check", str(doc))
        self.assertEqual(code, 1)
        self.assertIn("pending", out)
        self.assertEqual(self.run_cli("mirror", "write", str(doc))[0], 0)
        self.assertTrue((self.repo / ".git" / "odd" / "f" / "tasks.md").is_file())
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all", ".git"), "")
        self.assertEqual(self.run_cli("mirror", "check", str(doc))[0], 0)
        doc.write_text(VALID.replace("- [ ] T2", "- [x] T2").replace("existing limit behavior", "x · 9f8e7d6c"),
                       encoding="utf-8")
        code, out = self.run_cli("mirror", "check", str(doc))
        self.assertEqual(code, 1)
        self.assertIn("DIFFERS", out)


class BudgetTests(RepoCase):
    def test_budget_counts_authored_lines_and_skips_goldens(self):
        self.git("checkout", "-q", "-b", "feature")
        (self.repo / "a.py").write_text("x = 1\n" * 300, encoding="utf-8")
        (self.repo / "testdata" / "golden").mkdir(parents=True)
        (self.repo / "testdata" / "golden" / "out.txt").write_text("g\n" * 900, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "unit 1")
        code, out = self.run_cli("budget", "--base-ref", "main")
        self.assertEqual(code, 0)
        self.assertIn(": 300 / 400", out)
        (self.repo / "b.py").write_text("y = 2\n" * 150, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "unit 2")
        doc = self.repo / "f.md"
        doc.write_text(VALID, encoding="utf-8")
        code, out = self.run_cli("budget", "--base-ref", "main", "--file", str(doc))
        self.assertIn(": 450 / 400", out)
        self.assertIn("ask once for the chain strategy", out)


if __name__ == "__main__":
    unittest.main()
