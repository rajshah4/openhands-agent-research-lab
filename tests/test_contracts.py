import json
import unittest

from research_lab.contracts import ContractError, parse_worker_contract


class WorkerContractTests(unittest.TestCase):
    def valid_contract(self) -> dict:
        return {
            "status": "done",
            "candidate": {"assignments": {"0": 0}},
            "lesson": {
                "statement": "Start with constrained nodes.",
                "tags": ["graph-coloring"],
                "evidence": "The candidate was produced by this ordering.",
            },
            "summary": ["Produced one candidate."],
            "next_gate": "validate",
        }

    def test_parses_strict_contract(self) -> None:
        contract = parse_worker_contract(json.dumps(self.valid_contract()))
        self.assertEqual(contract.status, "done")
        self.assertEqual(contract.next_gate, "validate")
        self.assertEqual(contract.lesson.tags, ("graph-coloring",))
        self.assertEqual(contract.transport, "exact-json")

    def test_rejects_unknown_fields(self) -> None:
        value = self.valid_contract()
        value["confidence"] = 0.9
        with self.assertRaisesRegex(ContractError, "unknown contract fields"):
            parse_worker_contract(json.dumps(value))

    def test_rejects_done_without_candidate(self) -> None:
        value = self.valid_contract()
        value["candidate"] = None
        with self.assertRaisesRegex(ContractError, "requires a candidate"):
            parse_worker_contract(json.dumps(value))

    def test_accepts_one_valid_trailing_contract_and_marks_fallback(self) -> None:
        contract = parse_worker_contract(
            "Reasoning that should not have been returned.\n"
            + json.dumps(self.valid_contract())
        )
        self.assertEqual(contract.transport, "trailing-json-fallback")

    def test_rejects_non_contract_trailing_json(self) -> None:
        with self.assertRaisesRegex(ContractError, "no unique trailing JSON contract"):
            parse_worker_contract('Result:\n{"status": "failed"}')


if __name__ == "__main__":
    unittest.main()
