"""Meaningful domain / transaction tests; no external packages or services."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from erp_demo.fixtures import flow_spec
from erp_demo.service import ApiError, Service, evaluate_rule, expert_advice, validate_flow


class DomainTests(unittest.TestCase):
    def test_decimal_threshold_and_denominator(self):
        self.assertTrue(evaluate_rule(9800, 10000)["passed"])
        self.assertFalse(evaluate_rule(9799, 10000)["passed"])
        self.assertEqual(evaluate_rule(1650000, 1850000)["variancePercent"], "10.8")
        self.assertEqual(evaluate_rule(1650000, 1850000)["differenceMinor"], 200000)

    def test_authorization_and_receipt_override_small_variance(self):
        self.assertTrue(evaluate_rule(10000, 10000, authorized=False)["mandatoryHuman"])
        self.assertTrue(evaluate_rule(10000, 10000, has_receipt=False)["mandatoryHuman"])
        self.assertTrue(evaluate_rule(10000, 10000, duplicate=True)["mandatoryHuman"])

    def test_expert_has_no_execution_fields_or_fake_evidence(self):
        with self.assertRaises(ApiError) as context:
            expert_advice([], evaluate_rule(100, 100), {"executableCommand": "write"})
        self.assertEqual(context.exception.code, "EXPERT_BOUNDARY")
        with self.assertRaises(ApiError):
            expert_advice([], evaluate_rule(100, 100), {"recommendation": "ALLOW_REVIEW", "evidenceRefs": ["invented"]})
        result = expert_advice([], evaluate_rule(100, 100, has_receipt=False))
        self.assertEqual(result["recommendation"], "ABSTAIN")
        self.assertTrue(result["requiresHuman"])

    def test_flow_validation_and_human_ownership(self):
        spec = flow_spec()
        self.assertTrue(validate_flow(spec)["valid"])
        human = next(n for n in spec["nodes"] if n["type"] == "HUMAN")
        human["backup"] = ""
        with self.assertRaises(ApiError) as context:
            validate_flow(spec)
        self.assertEqual(context.exception.code, "FLOW_INVALID")

    def test_flow_control_and_audit_paths(self):
        spec = flow_spec()
        spec["edges"].append({"source": "start", "target": "write", "condition": ""})
        with self.assertRaises(ApiError):
            validate_flow(spec)
        spec = flow_spec()
        spec["edges"].append({"source": "write", "target": "end", "condition": ""})
        with self.assertRaises(ApiError):
            validate_flow(spec)

    def test_flow_rejects_cycles_and_expert_tools(self):
        spec = flow_spec()
        spec["edges"].append({"source": "human", "target": "rule", "condition": ""})
        with self.assertRaises(ApiError):
            validate_flow(spec)

    def test_malformed_flow_is_validation_error(self):
        for spec in [{"nodes": "invalid", "edges": []}, {"nodes": [{"id": []}], "edges": []}]:
            with self.assertRaises(ApiError) as context:
                validate_flow(spec)
            self.assertEqual(context.exception.status, 422)
        spec = flow_spec()
        next(n for n in spec["nodes"] if n["type"] == "EXPERT")["tools"] = ["write"]
        with self.assertRaises(ApiError):
            validate_flow(spec)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.service = Service(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def get(self, path, query=None, **kwargs):
        return self.service.request("GET", path, query=query, **kwargs)

    def post(self, path, data=None, **kwargs):
        return self.service.request("POST", path, data, **kwargs)

    def decision_payload(self, d, action="APPROVE", reason="已核验证据"):
        return {"expectedRevision": d["revision"], "evidenceSnapshotHash": d["evidenceSnapshotHash"],
                "action": action, "reason": reason}

    def start(self, fault="none"):
        return self.post("/scenarios/linked", {"fault": fault})

    def supplement(self, row):
        return self.post(f"/instances/{row['id']}/evidence", {"expectedRevision": row["revision"],
                         "note": "采购负责人授权新增服务，修订订单并补充收货证明。", "poAmountMinor": row["amountMinor"]})

    def approve_linked(self, row):
        row = self.supplement(row)
        detail = self.get("/instances/" + row["id"])
        d = next(d for d in detail["decisions"] if d["state"] == "PENDING")
        return self.post("/decisions/" + d["id"] + "/resolve", self.decision_payload(d))["instance"]

    def test_initial_catalog_and_reference_counts(self):
        boot = self.get("/bootstrap")
        self.assertEqual(len(boot["processes"]), 8)
        self.assertEqual(self.get("/decisions")["total"], 3)
        rows = self.get("/processes/P1/instances")
        self.assertEqual(rows["total"], 8)
        self.assertEqual(rows["counts"], {"running": 4, "waiting": 2, "error": 1, "completed": 1, "other": 0})
        self.assertEqual(self.get("/runtime/summary")["cards"], {"running": 24, "completed": 186, "waiting": 3, "error": 2})

    def test_get_detail_is_side_effect_free(self):
        before = self.get("/instances/INV-2026-0179")
        count = self.get("/audit/events")["total"]
        for _ in range(10):
            self.assertEqual(self.get("/instances/INV-2026-0179"), before)
        self.assertEqual(self.get("/audit/events")["total"], count)
        self.assertEqual(before["amountMinor"], 12680000)

    def test_explicit_email_event_only_once(self):
        path = "/instances/INV-2026-0179/events"
        result = self.post(path, {"type": "email_adjustment_0179", "expectedRevision": 1})
        self.assertEqual(result["amountMinor"], 1650000)
        self.assertEqual(result["ruleResult"]["variancePercent"], "10.8")
        repeated = self.post(path, {"type": "email_adjustment_0179", "expectedRevision": result["revision"]})
        self.assertEqual(repeated["revision"], result["revision"])
        self.assertEqual(self.get("/decisions")["total"], 4)
        counts = self.get("/processes/P1/instances")["counts"]
        self.assertEqual((counts["running"], counts["waiting"]), (3, 3))

    def test_queue_clears_and_does_not_write_on_approve(self):
        decisions = self.get("/decisions")["items"]
        self.assertIn("NORMAL_APPROVAL", {d["sourceKind"] for d in decisions})
        for i, d in enumerate(decisions):
            result = self.post("/decisions/" + d["id"] + "/resolve", self.decision_payload(d))
            self.assertEqual(result["instance"]["status"], "RUNNING")
            self.assertFalse(self.get("/instances/" + d["instanceId"])["invocations"])
            self.assertEqual(self.get("/decisions")["total"], 2-i)
        self.assertEqual(self.get("/runtime/summary", {"mode": "linked"})["cards"]["waiting"], 0)

    def test_concurrent_approval_only_one_succeeds(self):
        d = self.get("/decisions")["items"][0]

        def attempt(_):
            try:
                self.post("/decisions/" + d["id"] + "/resolve", self.decision_payload(d))
                return 200
            except ApiError as error:
                return error.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, range(2))), [200, 409])
        events = self.get("/audit/events", {"instanceId": d["instanceId"]})["items"]
        self.assertEqual(len([e for e in events if e["actorType"] == "人工决定"]), 1)

    def test_linked_mandatory_human_and_missing_evidence(self):
        row = self.start("missing_receipt")
        self.assertEqual(row["status"], "WAITING_HUMAN")
        self.assertEqual(row["expertResult"]["recommendation"], "ABSTAIN")
        d = next(d for d in self.get("/decisions")["items"] if d["instanceId"] == row["id"])
        with self.assertRaises(ApiError) as context:
            self.post("/decisions/" + d["id"] + "/resolve", self.decision_payload(d))
        self.assertEqual(context.exception.status, 412)
        self.assertFalse(self.get("/instances/" + row["id"])["invocations"])

    def test_full_linked_closure_and_idempotent_write(self):
        row = self.approve_linked(self.start())
        key, path = "write-once", f"/instances/{row['id']}/advance"
        body = {"expectedRevision": row["revision"]}
        done = self.post(path, body, key=key)
        self.assertEqual(done["status"], "COMPLETED")
        self.assertTrue(done["externalObject"].startswith("DEMO-"))
        self.assertEqual(self.post(path, body, key=key), done)
        invocations = self.get("/instances/" + row["id"])["invocations"]
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0]["calls"], 1)
        events = self.get("/audit/events", {"instanceId": row["id"]})["items"]
        self.assertEqual(len({e["traceId"] for e in events}), 1)
        self.assertTrue(any(e["actorType"] == "人工决定" and e["evidenceSnapshotHash"] for e in events))

    def test_unknown_write_is_reconciled_without_reinvocation(self):
        row = self.approve_linked(self.start("write_timeout"))
        unknown = self.post(f"/instances/{row['id']}/advance", {"expectedRevision": row["revision"]})
        self.assertEqual(unknown["status"], "RECONCILING")
        done = self.post(f"/instances/{row['id']}/reconcile", {"expectedRevision": unknown["revision"]})
        self.assertEqual(done["status"], "COMPLETED")
        calls = self.get("/instances/" + row["id"])["invocations"]
        self.assertEqual((len(calls), calls[0]["calls"]), (1, 1))

    def test_known_write_failure_is_not_completed(self):
        row = self.approve_linked(self.start("write_failure"))
        failed = self.post(f"/instances/{row['id']}/advance", {"expectedRevision": row["revision"]})
        self.assertEqual(failed["status"], "FAILED")
        self.assertFalse(failed.get("externalObject"))

    def test_changed_evidence_invalidates_approval(self):
        row = self.approve_linked(self.start())
        revised = self.supplement(row)
        self.assertNotIn("approvedHash", revised)
        with self.assertRaises(ApiError) as context:
            self.post(f"/instances/{row['id']}/advance", {"expectedRevision": revised["revision"]})
        self.assertEqual(context.exception.code, "NOT_APPROVED")
        self.assertFalse(self.get("/instances/" + row["id"])["invocations"])

    def test_request_changes_and_resubmission(self):
        row = self.start()
        d = next(d for d in self.get("/decisions")["items"] if d["instanceId"] == row["id"])
        waiting = self.post("/decisions/" + d["id"] + "/resolve", self.decision_payload(d, "REQUEST_CHANGES", "请补充采购授权"))["instance"]
        self.assertEqual(waiting["status"], "WAITING_INPUT")
        revised = self.supplement(waiting)
        fresh = next(d for d in self.get("/decisions")["items"] if d["instanceId"] == row["id"])
        self.assertEqual(fresh["sourceKind"], "RESUBMISSION")
        self.assertNotEqual(fresh["evidenceSnapshotHash"], d["evidenceSnapshotHash"])
        self.assertEqual(revised["status"], "WAITING_HUMAN")

    def test_scope_and_auditor_permissions(self):
        with self.assertRaises(ApiError) as context:
            self.get("/instances/INV-2026-0179", department="sales")
        self.assertEqual(context.exception.status, 404)
        with self.assertRaises(ApiError) as context:
            self.post("/scenarios/linked", actor="auditor")
        self.assertEqual(context.exception.status, 403)

    def test_idempotency_rejects_different_payload(self):
        row = self.post("/scenarios/linked", {"fault": "none"}, key="scenario-1")
        self.assertEqual(self.post("/scenarios/linked", {"fault": "none"}, key="scenario-1")["id"], row["id"])
        with self.assertRaises(ApiError) as context:
            self.post("/scenarios/linked", {"fault": "write_timeout"}, key="scenario-1")
        self.assertEqual(context.exception.status, 409)

    def test_configuration_approval_and_activation(self):
        before = next(c for c in self.get("/bootstrap")["configs"] if c["id"] == "rules-P1")
        spec = deepcopy(before["spec"])
        spec["thresholdPercent"] = "5"
        result = self.post("/config-drafts", {"configId": "rules-P1", "spec": spec, "expectedRevision": before["revision"]})
        ap = result["approval"]
        active = next(c for c in self.get("/bootstrap")["configs"] if c["id"] == "rules-P1")
        self.assertEqual(active["spec"]["thresholdPercent"], "2")
        with self.assertRaises(ApiError):
            self.post("/approvals/" + ap["id"] + "/resolve", {"action": "APPROVE", "expectedRevision": 1})
        approved = self.post("/approvals/" + ap["id"] + "/resolve", {"action": "APPROVE", "expectedRevision": 1}, actor="reviewer")
        asset = approved["asset"]
        self.assertEqual(asset["state"], "APPROVED")
        self.post("/assets/" + asset["id"] + "/activate", {"expectedRevision": asset["revision"]}, actor="reviewer")
        current = next(c for c in self.get("/bootstrap")["configs"] if c["id"] == "rules-P1")
        self.assertEqual(current["spec"]["thresholdPercent"], "5")

    def test_designer_cannot_self_approve(self):
        asset = self.get("/assets/S1")
        draft = self.service.request("PUT", "/assets/S1/draft", {"spec": asset["spec"], "expectedRevision": asset["revision"]}, actor="reviewer")
        tested = self.post("/assets/S1/test-runs", {"expectedRevision": draft["revision"]}, actor="reviewer")
        submitted = self.post("/assets/S1/submit", {"expectedRevision": tested["asset"]["revision"]}, actor="reviewer")
        with self.assertRaises(ApiError) as context:
            self.post("/approvals/" + submitted["approval"]["id"] + "/resolve", {"action": "APPROVE", "expectedRevision": 1}, actor="reviewer")
        self.assertEqual(context.exception.code, "SEPARATION_OF_DUTIES")

    def test_seed_pending_version_activates_without_duplicate(self):
        ap = next(a for a in self.get("/approvals")["items"] if a["assetId"] == "mcp-04")
        approved = self.post("/approvals/" + ap["id"] + "/resolve", {"action": "APPROVE", "expectedRevision": 1}, actor="reviewer")
        a = approved["asset"]
        activated = self.post("/assets/" + a["id"] + "/activate", {"expectedRevision": a["revision"]}, actor="reviewer")
        versions = [v["version"] for v in activated["versions"]]
        self.assertEqual(len(versions), len(set(versions)))
        self.assertEqual(activated["state"], "ACTIVE")

    def test_stale_configuration_cannot_overwrite_new_active_version(self):
        config = next(c for c in self.get("/bootstrap")["configs"] if c["id"] == "rules-P1")
        drafts = [self.post("/config-drafts", {"configId": config["id"], "spec": config["spec"], "expectedRevision": config["revision"]}) for _ in range(2)]
        approved = []
        for draft in drafts:
            ap = draft["approval"]
            approved.append(self.post("/approvals/" + ap["id"] + "/resolve", {"action": "APPROVE", "expectedRevision": 1}, actor="reviewer")["asset"])
        self.post("/assets/" + approved[0]["id"] + "/activate", {"expectedRevision": approved[0]["revision"]})
        with self.assertRaises(ApiError) as context:
            self.post("/assets/" + approved[1]["id"] + "/activate", {"expectedRevision": approved[1]["revision"]})
        self.assertEqual(context.exception.code, "CONFIG_CHANGED")

    def test_draft_and_test_revision_preserve_active_spec(self):
        asset = self.get("/assets/P1")
        spec = deepcopy(asset["draftSpec"])
        spec["nodes"][1]["name"] = "测试的新识别节点"
        saved = self.service.request("PUT", "/assets/P1/draft", {"spec": spec, "expectedRevision": asset["revision"]})
        self.assertNotEqual(saved["draftSpec"], saved["activeSpec"])
        with self.assertRaises(ApiError) as context:
            self.post("/assets/P1/submit", {"expectedRevision": saved["revision"]})
        self.assertEqual(context.exception.code, "TEST_REQUIRED")
        tested = self.post("/assets/P1/test-runs", {"expectedRevision": saved["revision"]})
        self.assertEqual(tested["run"]["sampleCount"], 4)
        self.assertEqual(self.get("/assets/P1")["activeVersion"], "v2.0")

    def test_search_and_permissions_are_combined(self):
        result = self.get("/assets", {"kind": "TOOL", "search": "采购", "access": "READ"})
        self.assertEqual([r["id"] for r in result["items"]], ["mcp-01"])
        self.assertEqual(self.get("/assets", {"kind": "TOOL"})["total"], 8)

    def test_graph_has_no_edges_to_hidden_nodes(self):
        graph = self.get("/knowledge/graph", {"type": "PERSON"})
        ids = {n["id"] for n in graph["nodes"]}
        self.assertTrue(all(e["source"] in ids and e["target"] in ids for e in graph["edges"]))
        self.assertFalse(self.get("/knowledge/graph", {"search": "does-not-exist"})["nodes"])

    def test_feedback_does_not_change_active_rules(self):
        row = self.approve_linked(self.start())
        done = self.post(f"/instances/{row['id']}/advance", {"expectedRevision": row["revision"]})
        before = self.get("/bootstrap")["configs"]
        feedback = self.post(f"/instances/{row['id']}/feedback", {"reason": "请加强新增服务授权检查"})
        self.assertEqual(feedback["feedback"][0]["state"], "PENDING_REVIEW")
        self.assertEqual(before, self.get("/bootstrap")["configs"])
        self.assertEqual(feedback["status"], done["status"])

    def test_audit_is_append_only_and_outbox_commits(self):
        row = self.start()
        events = self.get("/events")["items"]
        self.assertTrue(any(e["aggregateId"] == row["id"] for e in events))
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE audit SET body='{}' WHERE sequence=1")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM audit WHERE sequence=1")

    def test_restart_persists_state_and_reset_restores_seed(self):
        self.start()
        again = Service(self.path)
        self.assertEqual(again.request("GET", "/decisions")["total"], 4)
        self.post("/demo/reset", {"confirm": "RESET_DEMO"})
        self.assertEqual(self.get("/decisions")["total"], 3)
        self.assertEqual(self.get("/audit/events")["total"], 8)


if __name__ == "__main__":
    unittest.main()
