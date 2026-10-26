"""Tests for RDD risk tiers and the receipt ledger, driven through the pure functions."""

from __future__ import annotations

import json
import unittest

import ledger
import risk
from risk import Change

POLICY = risk.load_policy(risk.DEFAULT_RISK)
LIVE = "committed:base..tree"
NOW = "2026-10-23T00:00:00+00:00"


def doc(path: str, text: bytes = b"# Title\n\nprose\n", additions: int = 3) -> Change:
    return Change(path=path, additions=additions, content=text)


class TierTests(unittest.TestCase):
    def test_prose_is_passive_whatever_its_size(self):
        found = risk.classify(POLICY, [doc(f"docs/p{i}.md", additions=5000) for i in range(12)])
        self.assertEqual((found.tier, found.lenses), ("passive", ()))

    def test_passive_is_proven_by_content_not_extension(self):
        self.assertEqual(risk.classify(POLICY, [doc("docs/run.md", b"#!/bin/sh\necho hi\n")]).tier, "medium")
        self.assertEqual(risk.classify(POLICY, [doc("img/logo.png", b"not a png")]).tier, "medium")
        self.assertEqual(risk.classify(POLICY, [doc("img/logo.png", b"\x89PNG\r\n\x1a\nrest")]).tier, "passive")
        self.assertEqual(risk.classify(POLICY, [doc("docs/page.mdx", b"import X from 'y'\n")]).tier, "medium")

    def test_agent_facing_markdown_is_never_passive(self):
        for path in ("AGENTS.md", ".agents/skills/x/SKILL.md", "docs/prompts/review.md", ".github/README.md"):
            with self.subTest(path=path):
                self.assertNotEqual(risk.classify(POLICY, [doc(path)]).tier, "passive")

    def test_configuration_is_medium(self):
        found = risk.classify(POLICY, [Change("config/app.yaml", additions=2)])
        self.assertEqual((found.tier, found.reasons[0]["code"]), ("medium", "configuration_change"))

    def test_hot_path_service_token_shell_and_mode_are_high(self):
        cases = [
            Change("internal/auth/session.go", additions=1),
            Change("src/webhook/handler.ts", additions=1),
            Change("src/service_token.py", additions=1),
            Change("scripts/deploy.sh", additions=1),
            Change("bin/tool.py", old_mode="100644", new_mode="100755"),
        ]
        for change in cases:
            with self.subTest(path=change.path):
                found = risk.classify(POLICY, [change])
                self.assertEqual((found.tier, len(found.lenses)), ("high", 4))

    def test_hot_path_tokens_in_tests_are_not_evidence(self):
        self.assertEqual(risk.classify(POLICY, [Change("internal/auth/session_test.go", additions=4)]).tier, "medium")

    def test_dangerous_sink_in_added_lines_is_high(self):
        change = Change("src/fetch.py", additions=1, added="requests.get(url, verify=False)")
        found = risk.classify(POLICY, [change])
        self.assertEqual(found.tier, "high")
        self.assertIn("TLS", found.reasons[0]["detail"])

    def test_escalation_raises_and_must_cite_an_item(self):
        found = risk.classify(POLICY, [Change("src/a.py", additions=1)], {"item": "4", "reason": "new lock"})
        self.assertEqual((found.tier, found.reasons[-1]["code"]), ("high", "agent_escalation"))
        with self.assertRaises(ValueError):
            risk.classify(POLICY, [Change("src/a.py", additions=1)], {"item": "9", "reason": "x"})

    def test_changed_lines_skip_goldens_and_binaries(self):
        changes = [Change("a.py", additions=10, deletions=5), Change("testdata/golden/out.txt", additions=900),
                   Change("img.bin", additions=0, binary=True)]
        self.assertEqual(risk.changed_lines(POLICY, changes), 15)

    def test_correction_budget(self):
        self.assertEqual([risk.correction_budget(n) for n in (0, 1, 3, 101, 1000)], [0, 2, 2, 51, 200])


class DueTests(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(ledger.assess_due(True, "high", 999), (False, "already_reviewed"))
        self.assertEqual(ledger.assess_due(False, "high", 1), (True, "high_risk"))
        self.assertEqual(ledger.assess_due(False, "medium", 399), (False, "under_budget"))
        self.assertEqual(ledger.assess_due(False, "medium", 400), (True, "slice_budget_reached"))
        self.assertEqual(ledger.assess_due(False, "passive", 5000), (False, "passive"))


def review(tier: str = "medium", lenses=("risk",), budget: int = 50) -> ledger.Record:
    return ledger.new_review("r1", {"projection": "committed"}, LIVE,
                             {"tier": tier, "reasons": [], "changed_lines": 100}, list(lenses), budget, "granted", NOW)


def row(rid: str, severity: str = "CRITICAL") -> dict:
    return {"id": rid, "location": "src/a.py:10", "severity": severity, "evidence": "unchecked input"}


class LedgerTests(unittest.TestCase):
    def test_lens_selection(self):
        self.assertEqual(ledger.select_lenses("passive", []), [])
        self.assertEqual(ledger.select_lenses("high", []), ["risk", "readability", "reliability", "resilience"])
        self.assertEqual(ledger.select_lenses("medium", ["reliability"]), ["reliability"])
        for bad in ([], ["vibes"], ["risk", "risk"]):
            with self.subTest(bad=bad), self.assertRaises(ledger.Refusal):
                ledger.select_lenses("medium", bad)

    def test_passive_start_closes_and_spends_authority(self):
        record = review(tier="passive", lenses=())
        self.assertEqual(record["state"], ledger.CLOSED)
        with self.assertRaises(ledger.Refusal) as caught:
            ledger.capture_lens(record, LIVE, "risk", [], "x", NOW)
        self.assertEqual(caught.exception.code, "wrong_state")

    def test_only_severe_findings_go_to_refutation(self):
        record = ledger.capture_lens(review(), LIVE, "risk", [row("R1-001", "WARNING")], "one sweep", NOW)
        self.assertEqual(record["state"], ledger.CLOSED)
        self.assertEqual(record["ledger"][0]["status"], "info")

    def test_ledger_rows_are_validated(self):
        for bad in ({"id": "R2-001"}, row("R1-1"), row("R1-001", "MAJOR"), {**row("R1-001"), "evidence": ""}):
            with self.subTest(bad=bad), self.assertRaises(ledger.Refusal) as caught:
                ledger.capture_lens(review(), LIVE, "risk", [bad], "sweep", NOW)
            self.assertEqual(caught.exception.code, "malformed_ledger")

    def test_stale_identity_refuses(self):
        with self.assertRaises(ledger.Refusal) as caught:
            ledger.capture_lens(review(), "committed:base..moved", "risk", [], "sweep", NOW)
        self.assertEqual(caught.exception.code, "stale_target_identity")

    def test_standard_review_uses_one_general_refuter(self):
        record = ledger.capture_lens(review(), LIVE, "risk", [row("R1-001"), row("R1-002")], "sweep", NOW)
        self.assertEqual((record["state"], record["refuters"]), (ledger.REFUTING, ["general"]))
        record = ledger.capture_refutation(record, LIVE, "general", {"R1-001": "refuted"}, "read code", NOW)
        self.assertEqual(record["state"], ledger.CORRECTING)
        self.assertEqual(record["correction"]["surviving"], ["R1-002"])

    def test_full_review_votes_two_of_three(self):
        record = review(tier="high", lenses=("risk", "readability", "reliability", "resilience"))
        ledger.capture_lens(record, LIVE, "risk", [row("R1-001"), row("R1-002")], "sweep", NOW)
        for lens in ("readability", "reliability", "resilience"):
            ledger.capture_lens(record, LIVE, lens, [], "sweep", NOW)
        self.assertEqual(record["refuters"], ["correctness", "exploitability", "reproducibility"])
        ledger.capture_refutation(record, LIVE, "correctness", {"R1-001": "refuted", "R1-002": "refuted"}, "e", NOW)
        ledger.capture_refutation(record, LIVE, "exploitability", {"R1-001": "refuted"}, "e", NOW)
        ledger.capture_refutation(record, LIVE, "reproducibility", {"R1-002": "garbage"}, "e", NOW)
        statuses = {r["id"]: r["status"] for r in record["ledger"]}
        self.assertEqual(statuses, {"R1-001": "refuted", "R1-002": "open"})

    def test_all_refuted_closes(self):
        record = ledger.capture_lens(review(), LIVE, "risk", [row("R1-001")], "sweep", NOW)
        record = ledger.capture_refutation(record, LIVE, "general", {"R1-001": "refuted"}, "counter-evidence", NOW)
        self.assertEqual(record["state"], ledger.CLOSED)

    def correcting(self) -> ledger.Record:
        record = ledger.capture_lens(review(), LIVE, "risk", [row("R1-001")], "sweep", NOW)
        return ledger.capture_refutation(record, LIVE, "general", {"R1-001": "corroborated"}, "holds", NOW)

    def test_one_scoped_correction_inside_budget_closes(self):
        record = ledger.capture_validation(self.correcting(), "committed:base..fixed", 12, "pass", "tests green", NOW)
        self.assertEqual((record["state"], record["ledger"][0]["status"]), (ledger.CLOSED, "verified"))

    def test_failed_validation_and_over_budget_escalate(self):
        record = ledger.capture_validation(self.correcting(), "x", 12, "findings", "still broken", NOW)
        self.assertEqual(record["state"], ledger.ESCALATED)
        record = ledger.capture_validation(self.correcting(), "x", 80, "pass", "ok", NOW)
        self.assertEqual(record["state"], ledger.ESCALATED)
        for label in ("spent 80", "remaining 0", "total budget 50"):
            self.assertIn(label, record["closed_reason"])

    def test_next_transition_is_read_only(self):
        record = review()
        before = json.dumps(record, sort_keys=True)
        ledger.next_transition(record, "committed:base..moved")
        self.assertEqual(json.dumps(record, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
