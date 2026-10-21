"""Transactional application services backed by SQLite.

This is a single-tenant local demo. Financial writes go exclusively to the
deterministic mock adapter below; no SAP credentials or remote calls exist.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re
import sqlite3
import uuid

from . import fixtures as f


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def require(condition, status, code, message, details=None):
    if not condition:
        raise ApiError(status, code, message, details)


def decimal_value(value, name):
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError()
        return result
    except (ValueError, InvalidOperation):
        raise ApiError(422, "VALIDATION_ERROR", f"{name}必须是有效数字")


def evaluate_rule(amount_minor, po_minor, threshold="2", *, has_receipt=True,
                  authorized=True, duplicate=False):
    require(isinstance(amount_minor, int) and amount_minor > 0, 422, "INVALID_AMOUNT", "金额必须为正整数分")
    require(isinstance(po_minor, int) and po_minor > 0, 422, "INVALID_AMOUNT", "采购订单金额必须为正整数分")
    limit = decimal_value(threshold, "金额差异阈值")
    require(Decimal(0) <= limit <= Decimal(100), 422, "VALIDATION_ERROR", "金额差异阈值范围为 0–100%")
    difference = abs(amount_minor - po_minor)
    percentage = Decimal(difference) * 100 / Decimal(po_minor)
    reasons = []
    if percentage > limit:
        reasons.append("AMOUNT_VARIANCE")
    if not has_receipt:
        reasons.append("MISSING_RECEIPT")
    if not authorized:
        reasons.append("UNAUTHORIZED_SERVICE")
    if duplicate:
        reasons.append("DUPLICATE_INVOICE")
    return {"passed": not reasons, "differenceMinor": difference,
            "variancePercent": str(percentage.quantize(Decimal("0.1"))),
            "mandatoryHuman": bool(reasons), "reasonCodes": reasons, "thresholdPercent": str(limit)}


def expert_advice(evidence, rule, output=None, min_evidence=2):
    available = {e["id"] for e in evidence}
    if output is not None:
        allowed = {"recommendation", "confidence", "rationaleSummary", "evidenceRefs", "conflicts", "requiresHuman", "reasonCodes"}
        require(isinstance(output, dict) and not (set(output) - allowed), 422, "EXPERT_BOUNDARY", "Expert 输出包含未授权字段；禁止执行命令及工具调用")
        require(output.get("recommendation") in {"ALLOW_REVIEW", "BLOCK", "ABSTAIN"}, 422, "EXPERT_SCHEMA", "Expert 建议枚举无效")
        require(isinstance(output.get("evidenceRefs"), list), 422, "EXPERT_SCHEMA", "证据引用必须为数组")
        require(all(ref in available for ref in output.get("evidenceRefs", [])), 422, "INVALID_EVIDENCE", "Expert 引用了不存在的证据")
        required = {"recommendation", "confidence", "rationaleSummary", "evidenceRefs", "conflicts", "requiresHuman", "reasonCodes"}
        require(required <= set(output), 422, "EXPERT_SCHEMA", "Expert 输出缺少必要字段")
        require(isinstance(output["requiresHuman"], bool) and isinstance(output["rationaleSummary"], str), 422, "EXPERT_SCHEMA", "Expert 输出字段类型错误")
        require(0 <= decimal_value(output["confidence"], "置信度") <= 1, 422, "EXPERT_SCHEMA", "置信度范围为 0–1")
        require(output["recommendation"] == "ABSTAIN" or len(set(output["evidenceRefs"])) >= min_evidence, 422, "INVALID_EVIDENCE", "独立判断缺少足够证据引用")
        require(not rule["mandatoryHuman"] or output["requiresHuman"], 422, "EXPERT_BOUNDARY", "Expert 不得覆盖规则强制人工条件")
    missing = "MISSING_RECEIPT" in rule["reasonCodes"] or len(evidence) < min_evidence
    return {"recommendation": "ABSTAIN" if missing else "ALLOW_REVIEW" if rule["passed"] else "BLOCK",
            "confidence": "0.00" if missing else "0.91", "requiresHuman": missing or rule["mandatoryHuman"],
            "rationaleSummary": "缺少收货证据，无法作出可追溯判断，请补充材料。" if missing else
                                "差异或授权条件触发规则 R-21，暂停写入，补充授权并修订订单后重新校验。" if rule["mandatoryHuman"] else
                                "证据完整且金额差异在阈值内；建议进入写入前校验。",
            "evidenceRefs": [e["id"] for e in evidence[:4]], "conflicts": [],
            "reasonCodes": rule["reasonCodes"], "simulated": True}


def validate_flow(spec):
    nodes, edges = spec.get("nodes", []), spec.get("edges", [])
    require(isinstance(nodes, list) and isinstance(edges, list) and len(nodes) <= 200,
            422, "FLOW_INVALID", "nodes / edges 必须为数组，演示最多支持 200 个节点")
    require(all(isinstance(n, dict) and isinstance(n.get("id"), str) for n in nodes) and
            all(isinstance(e, dict) and isinstance(e.get("source"), str) and isinstance(e.get("target"), str) for e in edges),
            422, "FLOW_INVALID", "节点和连线字段格式无效")
    for node in nodes:
        require(isinstance(node.get("name"), str) and node["name"].strip(), 422, "FLOW_INVALID", "节点名称不可为空")
        require(all(isinstance(node.get(k, 0), (int, float)) and abs(node.get(k, 0)) < 100000 for k in ["x", "y"]), 422, "FLOW_INVALID", "节点坐标无效")
    errors = []
    ids = [n.get("id") for n in nodes]
    by_id = {n.get("id"): n for n in nodes}
    if len(ids) != len(set(ids)) or not all(ids):
        errors.append({"field": "nodes", "message": "节点 ID 不可重复或为空"})
    starts = [n for n in nodes if n.get("type") == "EVENT"]
    ends = [n for n in nodes if n.get("type") == "END"]
    if len(starts) != 1 or not ends:
        errors.append({"field": "nodes", "message": "需要唯一入口和至少一个终点"})
    adjacency = {nid: [] for nid in ids}
    incoming = {nid: [] for nid in ids}
    for edge in edges:
        a, b = edge.get("source"), edge.get("target")
        if a not in by_id or b not in by_id:
            errors.append({"field": "edges", "message": "连线引用不存在的节点"})
        else:
            adjacency[a].append(b)
            incoming[b].append(a)
    visiting, visited = set(), set()

    def visit(nid):
        if nid in visiting:
            return False
        if nid in visited:
            return True
        visiting.add(nid)
        for target in adjacency[nid]:
            if not visit(target):
                return False
        visiting.remove(nid)
        visited.add(nid)
        return True

    if any(not visit(nid) for nid in ids):
        errors.append({"field": "edges", "message": "流程包含未受限循环"})
    if starts:
        reachable, stack = set(), [starts[0]["id"]]
        while stack:
            node_id = stack.pop()
            if node_id not in reachable:
                reachable.add(node_id)
                stack.extend(adjacency.get(node_id, []))
        for node in nodes:
            if node["id"] not in reachable:
                errors.append({"nodeId": node["id"], "message": "节点无法从入口到达"})
    can_end, stack = set(), [n["id"] for n in ends]
    while stack:
        nid = stack.pop()
        if nid not in can_end:
            can_end.add(nid)
            stack.extend(incoming.get(nid, []))
    for node in nodes:
        nid, kind = node["id"], node.get("type")
        if kind not in {"EVENT", "TASK", "RULE", "EXPERT", "HUMAN", "ERP_WRITE", "AUDIT", "END"}:
            errors.append({"nodeId": nid, "message": "不支持的业务骨架节点类型"})
        if nid not in can_end:
            errors.append({"nodeId": nid, "message": "节点无法到达终点"})
        if kind == "HUMAN" and (not node.get("owner") or not node.get("backup")):
            errors.append({"nodeId": nid, "message": "人工点必须设置主负责人及备选人"})
        if kind == "EXPERT" and any(node.get(k) for k in ["tools", "connectors", "executableCommand"]):
            errors.append({"nodeId": nid, "message": "Expert 不得持有工具、连接器或执行命令"})
        if kind == "RULE":
            out = [e for e in edges if e.get("source") == nid]
            if len(out) != 2 or {e.get("condition") for e in out} != {"PASS", "REVIEW"}:
                errors.append({"nodeId": nid, "message": "规则节点需包含互斥完备的 PASS / REVIEW 分支"})
        if kind == "ERP_WRITE":
            # Every entry-to-write path must have a rule or human control.
            pending = [(p, False) for p in incoming.get(nid, [])]
            seen = set()
            while pending:
                parent, controlled = pending.pop()
                if (parent, controlled) in seen:
                    continue
                seen.add((parent, controlled))
                controlled = controlled or by_id[parent].get("type") in {"RULE", "HUMAN"}
                if by_id[parent].get("type") == "EVENT" and not controlled:
                    errors.append({"nodeId": nid, "message": "写入路径缺少规则或人工控制点"})
                pending.extend((p, controlled) for p in incoming.get(parent, []))
            # Every write-to-end path must archive audit evidence.
            pending = [(p, False) for p in adjacency.get(nid, [])]
            seen = set()
            while pending:
                child, audited = pending.pop()
                if (child, audited) in seen:
                    continue
                seen.add((child, audited))
                audited = audited or by_id[child].get("type") == "AUDIT"
                if by_id[child].get("type") == "END" and not audited:
                    errors.append({"nodeId": nid, "message": "写入完成后必须经过审计归档"})
                pending.extend((p, audited) for p in adjacency.get(child, []))
    require(not errors, 422, "FLOW_INVALID", "流程校验失败", errors)
    return {"valid": True, "nodeCount": len(nodes), "edgeCount": len(edges)}


class Service:
    def __init__(self, database):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS entities(kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(sequence INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS idempotency(key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, response TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
            """)
            if not self.all(db, "setting"):
                self.seed(db)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def all(self, db, kind):
        return [json.loads(r["body"]) for r in db.execute("SELECT body FROM entities WHERE kind=? ORDER BY rowid", (kind,))]

    def get(self, db, kind, eid):
        row = db.execute("SELECT body FROM entities WHERE kind=? AND id=?", (kind, eid)).fetchone()
        require(row is not None, 404, "NOT_FOUND", "记录不存在或无权访问")
        return json.loads(row["body"])

    def put(self, db, kind, value):
        db.execute("INSERT INTO entities(kind,id,body) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                   (kind, value["id"], json.dumps(value, ensure_ascii=False)))
        return value

    def event(self, db, action, *, instance=None, actor="system", actor_type="系统服务", detail="", refs=None, outcome="SUCCESS"):
        event = {"id": uid("evt"), "traceId": instance["traceId"] if instance else uid("trace"),
                 "instanceId": instance["id"] if instance else None, "actorId": actor, "actorType": actor_type,
                 "action": action, "detail": detail, "outcome": outcome, "occurredAt": now(),
                 "ruleVersion": instance.get("ruleVersion") if instance else None,
                 "evidenceSnapshotHash": instance.get("evidenceSnapshotHash") if instance else None,
                 "evidenceRefs": [e["id"] for e in instance.get("evidence", [])] if instance else [],
                 "refs": refs or []}
        cursor = db.execute("INSERT INTO audit(body) VALUES(?)", (json.dumps(event, ensure_ascii=False),))
        event["sequence"] = cursor.lastrowid
        db.execute("INSERT INTO outbox(body) VALUES(?)", (json.dumps({"type": action, "aggregateId": instance["id"] if instance else "assets", "revision": instance.get("revision", 1) if instance else 1, "occurredAt": event["occurredAt"], "payload": event}, ensure_ascii=False),))
        if instance is not None:
            instance.setdefault("timeline", []).append(event)
        return event

    def make_decision(self, db, instance, source="EXCEPTION_REVIEW", rule="R-21"):
        decision = {"id": uid("decision"), "instanceId": instance["id"], "processId": instance["processId"],
                    "title": instance["supplier"], "rule": rule, "sourceKind": source, "state": "PENDING",
                    "revision": 1, "assignee": "operator", "backup": "reviewer", "createdAt": now(),
                    "evidenceSnapshotHash": instance["evidenceSnapshotHash"], "ruleVersion": instance["ruleVersion"]}
        self.put(db, "decision", decision)
        return decision

    def seed(self, db):
        self.put(db, "setting", {"id": "demo", "demoMode": True, "erpWriteEnabled": False, "seededAt": now()})
        for row in f.instances():
            self.put(db, "instance", row)
            if row["scenario"] == "queue":
                self.make_decision(db, row, "NORMAL_APPROVAL" if row["processId"] == "P2" else "EXCEPTION_REVIEW",
                                   {"P1": "R-21", "P2": "R-22", "P3": "R-23"}[row["processId"]])
        for row in f.assets():
            if row["state"] == "PENDING_APPROVAL":
                approval = {"id": uid("approval"), "assetId": row["id"], "name": row["name"], "kind": row["kind"],
                            "version": row["version"], "spec": deepcopy(row["spec"]), "specHash": f.digest(row["spec"]),
                            "submittedBy": "fixture", "state": "PENDING", "revision": 1, "createdAt": now(), "comment": "原型待审批演示版本"}
                row["approvalId"] = approval["id"]
                self.put(db, "approval", approval)
            self.put(db, "asset", row)
        for row in f.CONNECTORS:
            self.put(db, "connector", row)
        self.put(db, "config", {"id": "staffing", "spec": deepcopy(f.STAFF), "version": "v1.0", "revision": 1})
        for pid, rule in f.RULES.items():
            self.put(db, "config", {"id": f"rules-{pid}", "spec": rule, "version": rule["version"], "revision": 1})
        historic = {"id": "AP-2026-0731-014", "traceId": "trace-AP-2026-0731-014", "ruleVersion": "v3.4", "evidenceSnapshotHash": f.digest("historical-demo"), "evidence": []}
        for actor_type, action, detail in [
            ("Connector", "读取供应商邮件证据", "模拟连接 · 只读凭据 · 路由与证据指纹"),
            ("MCP Tool", "读取采购订单", "演示工具 v2.4.1 · Schema 与权限校验"),
            ("Skill", "发票 OCR 提取结构化字段", "模拟 OCR · 输入输出版本锁定"),
            ("Task Agent", "三单匹配完成核验", "演示置信度 0.91 · 发现差异"),
            ("Expert", "应付账款专家给出复核建议", "模拟判断 · 未调用工具或执行写入"),
            ("Process Agent", "进入条件分支", "写入暂停，等待人工"),
            ("人工决定", "责任人批准差异处理建议", "独立历史演示案例；不是发票 0179"),
            ("受控执行", "归档模拟会计凭证", "模拟对象 DEMO-190000014 · 无真实 SAP 写入"),
        ]:
            self.event(db, action, instance=historic, actor_type=actor_type, detail=detail)

    def request(self, method, path, data=None, query=None, *, actor="operator", department="finance", key=None):
        require(department == "finance", 404, "SCOPE_NOT_FOUND", "部门不存在或无权访问")
        require(actor in {"operator", "reviewer", "designer", "auditor"}, 403, "UNKNOWN_ACTOR", "未知演示身份")
        data, query = data or {}, query or {}
        require(isinstance(data, dict), 422, "INVALID_BODY", "请求正文必须为 JSON 对象")
        mutation = method != "GET"
        if mutation:
            require(actor != "auditor", 403, "READ_ONLY", "审计员只有读取权限")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE" if mutation else "BEGIN")
            request_hash = f.digest([method, path, data, actor, department])
            if mutation and key:
                saved = db.execute("SELECT * FROM idempotency WHERE key=?", (key,)).fetchone()
                if saved:
                    require(saved["request_hash"] == request_hash, 409, "IDEMPOTENCY_CONFLICT", "同一幂等键不能用于不同请求")
                    return json.loads(saved["response"])
            result = self.dispatch(db, method, path.rstrip("/") or "/", data, query, actor)
            if mutation and key:
                db.execute("INSERT INTO idempotency VALUES(?,?,?)", (key, request_hash, json.dumps(result, ensure_ascii=False)))
            return result

    def check_revision(self, record, data):
        require(data.get("expectedRevision") == record["revision"], 409, "REVISION_CONFLICT", "记录已更新，请刷新后重试", {"currentRevision": record["revision"]})

    def process_list(self, db):
        result = []
        for asset in self.all(db, "asset"):
            if asset["kind"] != "PROCESS":
                continue
            origin = next((deepcopy(p) for p in f.PROCESSES if p["id"] == asset["id"]), {})
            active = asset.get("activeSpec") or asset.get("spec", {})
            origin.update({"id": asset["id"], "name": asset["name"], "status": "ACTIVE" if asset.get("activeVersion") else asset["state"],
                           "version": asset.get("activeVersion") or asset["version"], "draftState": asset["state"],
                           "tasks": origin.get("tasks", sum(n["type"] == "TASK" for n in active.get("nodes", []))),
                           "humans": origin.get("humans", sum(n["type"] == "HUMAN" for n in active.get("nodes", []))), "owner": asset["owner"]})
            result.append(origin)
        return result

    def counts(self, rows):
        return {"running": sum(r["status"] in {"CREATED", "RUNNING", "RETRY_WAIT"} for r in rows),
                "waiting": sum(r["status"] == "WAITING_HUMAN" for r in rows),
                "error": sum(r["status"] in {"FAILED", "RECONCILING"} for r in rows),
                "completed": sum(r["status"] == "COMPLETED" for r in rows),
                "other": sum(r["status"] in {"WAITING_INPUT", "REJECTED", "CANCELLED"} for r in rows)}

    def operational_instances(self, db):
        # Reference-list snapshots are separate from the operational queue.
        # An explicit replay event promotes that reference object into live work.
        return [r for r in self.all(db, "instance") if r["scenario"] != "reference" or r.get("emailAdjusted")]

    def dispatch(self, db, method, path, data, query, actor):
        parts = path.strip("/").split("/")
        if method == "GET":
            if path == "/health":
                return {"status": "ok", "demo": True, "database": "SQLite", "erpWriteEnabled": False}
            if path == "/bootstrap":
                return {"processes": self.process_list(db), "assets": self.all(db, "asset"),
                        "connectors": self.all(db, "connector"), "configs": self.all(db, "config"),
                        "approvals": self.all(db, "approval"), "actor": actor, "departmentId": "finance",
                        "mode": "demo", "erpWriteEnabled": False}
            if path == "/runtime/summary":
                rows, instances = [], self.all(db, "instance")
                replay = query.get("mode", "replay") == "replay"
                if not replay:
                    instances = self.operational_instances(db)
                for i, process in enumerate(self.process_list(db)):
                    counts = self.counts([r for r in instances if r["processId"] == process["id"]])
                    if replay and i < 8:
                        counts.update({"running": 3+i, "completed": 22+17*i, "error": i % 3,
                                       "waiting": [0, 1, 0, 1, 0, 1, 0, 0][i]})
                    rows.append({**process, **counts, "sla": "临界" if i == 4 else "正常"})
                counts = self.counts(instances)
                pending = len([d for d in self.all(db, "decision") if d["state"] == "PENDING"])
                return {"cards": {"running": 24 if replay else counts["running"],
                                  "completed": 186 if replay else counts["completed"],
                                  "waiting": 3 if replay else counts["waiting"], "error": 2 if replay else counts["error"]},
                        "rows": rows, "pendingDecisions": pending, "snapshotAt": now(),
                        "source": "原型演示快照，统计与明细口径独立" if replay else "SQLite 联动实例实时聚合（含独立待办场景，不含原型列表快照）"}
            if path == "/processes":
                return {"items": self.process_list(db), "total": len(self.process_list(db))}
            if len(parts) == 3 and parts[0] == "processes" and parts[2] == "instances":
                self.get(db, "asset", parts[1])
                source = self.operational_instances(db) if query.get("mode") == "linked" else self.all(db, "instance")
                all_rows = [r for r in source if r["processId"] == parts[1] and (query.get("mode") == "linked" or r["scenario"] != "queue" or parts[1] != "P1")]
                rows = [r for r in all_rows if not query.get("status") or r["status"] == query["status"]]
                return {"items": rows, "total": len(rows), "counts": self.counts(all_rows)}
            if len(parts) == 2 and parts[0] == "instances":
                row = self.get(db, "instance", parts[1])
                row["decisions"] = [d for d in self.all(db, "decision") if d["instanceId"] == row["id"]]
                row["invocations"] = [v for v in self.all(db, "invocation") if v["instanceId"] == row["id"]]
                return row
            if path == "/decisions":
                rows = [d for d in self.all(db, "decision") if d["state"] == query.get("state", "PENDING")]
                return {"items": rows, "total": len(rows)}
            if path == "/assets":
                rows = self.all(db, "asset")
                for k in ["kind", "category", "state"]:
                    if query.get(k):
                        rows = [r for r in rows if r[k] == query[k]]
                if query.get("access"):
                    rows = [r for r in rows if r["spec"].get("access") == query["access"]]
                if query.get("search"):
                    needle = query["search"].casefold()
                    rows = [r for r in rows if needle in " ".join([r["name"], r["spec"].get("mapping", ""), r["spec"].get("route", "")]).casefold()]
                return {"items": rows, "total": len(rows)}
            if len(parts) == 2 and parts[0] == "assets":
                return self.get(db, "asset", parts[1])
            if path == "/approvals":
                rows = self.all(db, "approval")
                return {"items": rows, "total": len(rows)}
            if path == "/connectors":
                rows = [c for c in self.all(db, "connector") if c["tab"] == query.get("tab", "sap")]
                return {"items": rows, "total": len(rows)}
            if path == "/department/dashboard":
                return {"configs": self.all(db, "config"), "kpis": ["96.2%", "91.8%", "2.4%", "94.1%", "18"],
                        "volume": [98, 124, 112, 148, 165, 138, 186], "backlog": [26, 22, 25, 21, 24, 20, 18],
                        "source": "原型静态演示指标；非真实经营或模型评测"}
            if path == "/knowledge/graph":
                nodes = deepcopy(f.GRAPH_NODES)
                if query.get("type") and query["type"] != "ALL":
                    nodes = [n for n in nodes if n["type"] == query["type"]]
                if query.get("search"):
                    text = query["search"].casefold()
                    nodes = [n for n in nodes if text in (n["name"] + n["english"] + n["businessKey"]).casefold()]
                ids = {n["id"] for n in nodes}
                return {"nodes": nodes, "edges": [e for e in f.GRAPH_EDGES if e["source"] in ids and e["target"] in ids]}
            if len(parts) == 3 and parts[:2] == ["knowledge", "entities"]:
                node = next((deepcopy(n) for n in f.GRAPH_NODES if n["id"] == parts[2]), None)
                require(node, 404, "NOT_FOUND", "知识实体不存在")
                edges = [e for e in f.GRAPH_EDGES if parts[2] in [e["source"], e["target"]]]
                neighbor_ids = {e["source"] for e in edges} | {e["target"] for e in edges}
                node["neighbors"] = [n for n in f.GRAPH_NODES if n["id"] in neighbor_ids and n["id"] != node["id"]]
                node["relations"] = edges
                return node
            if path == "/audit/events":
                events = []
                for row in db.execute("SELECT sequence,body FROM audit ORDER BY sequence DESC"):
                    event = {**json.loads(row["body"]), "sequence": row["sequence"]}
                    if query.get("instanceId") and query["instanceId"] != event.get("instanceId"):
                        continue
                    if query.get("search") and query["search"].casefold() not in json.dumps(event, ensure_ascii=False).casefold():
                        continue
                    events.append(event)
                return {"items": events[:500], "total": len(events)}
            if path == "/events":
                try:
                    after = int(query.get("after", "0"))
                except ValueError:
                    raise ApiError(422, "INVALID_CURSOR", "事件游标必须为整数")
                rows = db.execute("SELECT sequence,body FROM outbox WHERE sequence>? ORDER BY sequence LIMIT 100", (after,)).fetchall()
                events = [{"id": row["sequence"], **json.loads(row["body"])} for row in rows]
                return {"items": events, "cursor": events[-1]["id"] if events else after}
            if len(parts) == 2 and parts[0] == "test-runs":
                return self.get(db, "test_run", parts[1])
        if method == "POST" and path == "/demo/reset":
            require(data.get("confirm") == "RESET_DEMO", 422, "CONFIRM_REQUIRED", "重置必须明确确认")
            db.execute("DROP TRIGGER audit_no_delete")
            for table in ["entities", "audit", "outbox", "idempotency"]:
                db.execute(f"DELETE FROM {table}")
            db.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit is append only'); END")
            self.seed(db)
            return {"reset": True}
        if method == "POST" and path == "/scenarios/linked":
            return self.start_scenario(db, data, actor)
        if method == "POST" and path == "/decisions/delegate":
            return self.delegate(db, data, actor)
        if len(parts) == 3 and parts[0] == "decisions" and parts[2] == "resolve" and method == "POST":
            return self.resolve_decision(db, parts[1], data, actor)
        if len(parts) == 3 and parts[0] == "instances" and method == "POST":
            return self.instance_action(db, parts[1], parts[2], data, actor)
        if method == "POST" and path == "/assets":
            return self.create_asset(db, data, actor)
        if len(parts) == 3 and parts[0] == "assets":
            aid, action = parts[1], parts[2]
            if method == "PUT" and action == "draft":
                return self.save_draft(db, aid, data, actor)
            if method == "POST" and action == "submit":
                return self.submit_asset(db, aid, data, actor)
            if method == "POST" and action == "activate":
                return self.activate_asset(db, aid, data, actor)
            if method == "POST" and action == "test-runs":
                return self.test_asset(db, aid, data, actor)
        if len(parts) == 3 and parts[0] == "approvals" and parts[2] == "resolve" and method == "POST":
            return self.resolve_approval(db, parts[1], data, actor)
        if method == "POST" and path == "/config-drafts":
            return self.config_draft(db, data, actor)
        if method == "POST" and len(parts) == 3 and parts[0] == "connectors" and parts[2] == "test":
            connector = self.get(db, "connector", parts[1])
            connector["lastTest"] = {"at": now(), "simulated": True,
                                     "success": connector["health"] == "HEALTHY",
                                     "message": "模拟连接健康检查通过" if connector["health"] == "HEALTHY" else "模拟连接不可用，请检查配置"}
            self.event(db, "连接健康测试", actor=actor, actor_type="Connector", detail=connector["name"], outcome="SUCCESS" if connector["lastTest"]["success"] else "FAILED")
            return self.put(db, "connector", connector)
        raise ApiError(404, "NOT_FOUND", "接口不存在")

    def start_scenario(self, db, data, actor):
        fault = data.get("fault", "none")
        require(fault in {"none", "missing_receipt", "write_timeout", "write_failure"}, 422, "INVALID_FAULT", "未知故障场景")
        iid = uid("DEMO-INV")
        rule_config = self.get(db, "config", "rules-P1")
        expert_config = self.get(db, "asset", "E1")
        expert_spec = expert_config.get("activeSpec") or expert_config["spec"]
        row = {"id": iid, "processId": "P1", "supplier": "上海工业服务供应商 · 联动场景",
               "amountMinor": 1650000, "poAmountMinor": 1850000, "currency": "CNY", "node": "异常判断",
               "task": "三单匹配", "status": "WAITING_HUMAN", "revision": 1, "owner": "应付账款负责人",
               "startedAt": now(), "elapsedMinutes": 0, "scenario": "linked", "ruleVersion": rule_config["version"],
               "processVersion": self.get(db, "asset", "P1")["activeVersion"], "thresholdPercent": rule_config["spec"]["thresholdPercent"],
               "expertVersion": expert_config["activeVersion"], "expertMinEvidence": expert_spec.get("minEvidence", 2),
               "serviceAuthorized": False, "evidence": f.base_evidence(iid), "traceId": uid("trace"),
               "timeline": [], "feedback": [], "fault": fault}
        if fault == "missing_receipt":
            row["evidence"] = [e for e in row["evidence"] if e["type"] != "GOODS_RECEIPT"]
        row["evidenceSnapshotHash"] = f.snapshot(row)
        row["ruleResult"] = evaluate_rule(row["amountMinor"], row["poAmountMinor"], row["thresholdPercent"],
                                          has_receipt=fault != "missing_receipt", authorized=False)
        row["expertResult"] = expert_advice(row["evidence"], row["ruleResult"], min_evidence=row["expertMinEvidence"])
        for actor_type, action in [("Connector", "供应商邮件与发票已接收"), ("Skill", "模拟 OCR 提取完成"),
                                   ("Task Agent", "三单匹配完成"), ("Process Agent", "规则 R-21 命中"),
                                   ("Expert", "生成独立复核建议"), ("Process Agent", "等待人工复核")]:
            self.event(db, action, instance=row, actor_type=actor_type, detail="联动演示 · ERP 写入保持暂停")
        self.make_decision(db, row)
        return self.put(db, "instance", row)

    def resolve_decision(self, db, did, data, actor):
        decision = self.get(db, "decision", did)
        require(actor in {decision["assignee"], decision["backup"]}, 403, "NOT_ASSIGNED", "当前身份不是该待办的负责人或备选人")
        require(decision["state"] == "PENDING", 409, "ALREADY_RESOLVED", "该待办已处理")
        self.check_revision(decision, data)
        instance = self.get(db, "instance", decision["instanceId"])
        require(instance["status"] == "WAITING_HUMAN", 409, "INSTANCE_STATE", "实例当前不处于人工复核阶段")
        require(data.get("evidenceSnapshotHash") == decision["evidenceSnapshotHash"] == f.snapshot(instance),
                412, "EVIDENCE_CHANGED", "证据或金额已变化，请重新查看证据并审批")
        action = str(data.get("action", "")).upper()
        require(action in {"APPROVE", "REJECT", "REQUEST_CHANGES", "RETURN_FOR_REWORK"}, 400, "INVALID_ACTION", "未知人工决定")
        reason = str(data.get("reason", "")).strip()
        require(action == "APPROVE" or reason, 422, "REASON_REQUIRED", "拒绝、补证或重做需要填写原因")
        if action == "APPROVE" and instance["scenario"] == "linked":
            require(instance.get("serviceAuthorized") and any(e["type"] == "GOODS_RECEIPT" for e in instance["evidence"]),
                    412, "PRECONDITION_FAILED", "请先补充新增服务授权、修订采购订单及收货证据，再批准")
            require(evaluate_rule(instance["amountMinor"], instance["poAmountMinor"], instance.get("thresholdPercent", "2"))["passed"],
                    412, "PRECONDITION_FAILED", "订单差异尚未消除，请先补充修订采购订单")
        decision.update({"state": action, "revision": decision["revision"] + 1, "resolvedBy": actor,
                         "reason": reason or "已核验证据与规则，批准继续", "resolvedAt": now()})
        instance["revision"] += 1
        instance.pop("approvedHash", None)
        if action == "APPROVE":
            instance.update({"status": "RUNNING", "node": "写入前复核", "approvedHash": instance["evidenceSnapshotHash"]})
        elif action == "REJECT":
            instance.update({"status": "REJECTED", "node": "拒绝归档"})
        elif action == "REQUEST_CHANGES":
            instance.update({"status": "WAITING_INPUT", "node": "等待补充证据"})
        else:
            require(instance.get("reworkCount", 0) < 3, 422, "REWORK_LIMIT", "最多重做 3 次")
            require(data.get("returnNodeId", "match") in {"ocr", "match"}, 422, "INVALID_RETURN_NODE", "只能退回识别或匹配节点")
            instance.update({"status": "WAITING_INPUT", "node": "退回三单匹配重做", "reworkCount": instance.get("reworkCount", 0) + 1})
        self.put(db, "decision", decision)
        self.event(db, {"APPROVE": "人工批准，恢复写入前校验", "REJECT": "人工拒绝并归档", "REQUEST_CHANGES": "人工要求补充证据", "RETURN_FOR_REWORK": "人工驳回重做"}[action],
                   instance=instance, actor=actor, actor_type="人工决定", detail=decision["reason"], refs=[did])
        self.put(db, "instance", instance)
        return {"decision": decision, "instance": instance}

    def delegate(self, db, data, actor):
        require(actor in {"operator", "reviewer"}, 403, "FORBIDDEN", "当前身份不能委派待办")
        ids = data.get("taskIds", [])
        require(isinstance(ids, list) and ids, 422, "TASKS_REQUIRED", "请选择待办")
        assignee, backup = data.get("assigneeId"), data.get("backupId", "operator")
        require(assignee in {"operator", "reviewer"} and backup in {"operator", "reviewer"} and assignee != backup, 422, "INVALID_ASSIGNEE", "主负责人和备选人必须为不同的有效身份")
        require(str(data.get("reason", "")).strip(), 422, "REASON_REQUIRED", "请输入委派原因")
        result = []
        for did in dict.fromkeys(ids):
            decision = self.get(db, "decision", did)
            require(decision["state"] == "PENDING" and data.get("revisions", {}).get(did) == decision["revision"], 409, "REVISION_CONFLICT", "待办已更新，请刷新")
            old = decision["assignee"]
            decision.update({"assignee": assignee, "backup": backup, "revision": decision["revision"] + 1})
            self.put(db, "decision", decision)
            instance = self.get(db, "instance", decision["instanceId"])
            self.event(db, "待办委派", instance=instance, actor=actor, actor_type="人工决定", detail=f"{old} → {assignee}；{data['reason']}")
            self.put(db, "instance", instance)
            result.append(decision)
        return {"items": result, "total": len(result)}

    def instance_action(self, db, iid, action, data, actor):
        row = self.get(db, "instance", iid)
        if action == "feedback":
            require(row["status"] in {"COMPLETED", "REJECTED"}, 409, "INSTANCE_STATE", "归档后才能提交反馈")
            require(str(data.get("reason", "")).strip(), 422, "REASON_REQUIRED", "请填写反馈内容")
            feedback = {"id": uid("feedback"), "actor": actor, "reason": str(data["reason"])[:2000], "createdAt": now(), "state": "PENDING_REVIEW", "traceId": row["traceId"]}
            row.setdefault("feedback", []).append(feedback)
            self.event(db, "反馈进入待审核案例池", instance=row, actor=actor, detail=feedback["reason"])
            return self.put(db, "instance", row)
        self.check_revision(row, data)
        if action == "events":
            require(iid == "INV-2026-0179" and data.get("type") == "email_adjustment_0179", 400, "INVALID_DEMO_EVENT", "未知演示事件")
            if row.get("emailAdjusted"):
                return row
            row.update({"amountMinor": 1650000, "node": "异常判断", "status": "WAITING_HUMAN", "emailAdjusted": True})
            row["evidenceSnapshotHash"] = f.snapshot(row)
            row["ruleResult"] = evaluate_rule(1650000, 1850000, authorized=False)
            row["expertResult"] = expert_advice(row["evidence"], row["ruleResult"], min_evidence=row.get("expertMinEvidence", 2))
            self.make_decision(db, row)
            self.event(db, "显式演示事件：邮件金额调整", instance=row, actor=actor, detail="金额由 ¥126,800 调整为 ¥16,500；GET 详情没有副作用")
        elif action == "evidence":
            require(row["status"] in {"WAITING_INPUT", "WAITING_HUMAN", "RUNNING"}, 409, "INSTANCE_STATE", "当前实例不可补证")
            require(str(data.get("note", "")).strip(), 422, "EVIDENCE_REQUIRED", "请输入证据说明")
            require(actor in {"operator", "reviewer"}, 403, "FORBIDDEN", "当前身份不能补充业务证据")
            old_hash = row["evidenceSnapshotHash"]
            row["evidence"].append({"id": uid("evidence"), "type": "AUTHORIZATION", "name": "新增服务授权及修订订单（模拟）",
                                    "source": actor, "content": str(data["note"])[:4000], "hash": f.digest(data["note"])})
            po = data.get("poAmountMinor", row["amountMinor"])
            require(isinstance(po, int) and po > 0, 422, "INVALID_AMOUNT", "修订采购订单金额必须为正整数分")
            row["poAmountMinor"], row["serviceAuthorized"] = po, True
            if data.get("includeReceipt", True) and not any(e["type"] == "GOODS_RECEIPT" for e in row["evidence"]):
                row["evidence"].append({"id": uid("evidence"), "type": "GOODS_RECEIPT", "name": "补充服务收货记录（模拟）", "source": actor, "content": "服务已验收", "hash": f.digest("received")})
            row.pop("approvedHash", None)
            for decision in self.all(db, "decision"):
                if decision["instanceId"] == iid and decision["state"] == "PENDING":
                    decision.update({"state": "SUPERSEDED", "revision": decision["revision"] + 1})
                    self.put(db, "decision", decision)
            row["evidenceSnapshotHash"] = f.snapshot(row)
            row["ruleResult"] = evaluate_rule(row["amountMinor"], row["poAmountMinor"], row.get("thresholdPercent", "2"), has_receipt=any(e["type"] == "GOODS_RECEIPT" for e in row["evidence"]))
            row["expertResult"] = expert_advice(row["evidence"], row["ruleResult"], min_evidence=row.get("expertMinEvidence", 2))
            row.update({"status": "WAITING_HUMAN", "node": "补证后重新复核"})
            self.make_decision(db, row, "RESUBMISSION")
            self.event(db, "补充证据并重新提交", instance=row, actor=actor, actor_type="人工决定", detail=f"原快照 {old_hash[:12]} 失效；新版证据必须重新审批")
        elif action == "advance":
            require(row["status"] == "RUNNING" and row.get("approvedHash"), 409, "NOT_APPROVED", "需要有效人工批准后才能执行模拟写入")
            require(row["approvedHash"] == f.snapshot(row), 412, "EVIDENCE_CHANGED", "批准后证据发生变化，禁止写入")
            invocation_id = f.digest(["finance", iid, "ERP_WRITE", 1, row["approvedHash"]])
            existing = db.execute("SELECT body FROM entities WHERE kind='invocation' AND id=?", (invocation_id,)).fetchone()
            if existing:
                invocation = json.loads(existing["body"])
                require(invocation["state"] == "SUCCESS", 409, "RECONCILE_REQUIRED", "已有未知或失败的写入，请核对结果")
            else:
                self.event(db, "写入前校验通过", instance=row, actor_type="Process Agent", detail="批准快照、规则版本、公司代码 1000 与模拟路由已核对")
                invocation = {"id": invocation_id, "instanceId": iid, "state": "SUCCESS", "idempotencyKey": invocation_id,
                              "routeVersion": "v1", "toolVersion": "demo-write-v1", "payloadHash": row["approvedHash"],
                              "externalObject": "DEMO-1900" + uuid.uuid4().hex[:6].upper(), "simulated": True, "createdAt": now(), "calls": 1}
                if row.get("fault") == "write_timeout":
                    invocation["state"] = "UNKNOWN"
                    invocation["remoteSucceeded"] = True
                elif row.get("fault") == "write_failure":
                    invocation["state"] = "FAILED"
                    invocation["externalObject"] = None
                self.put(db, "invocation", invocation)
            if invocation["state"] == "UNKNOWN":
                row.update({"status": "RECONCILING", "node": "核对模拟远端结果"})
                self.event(db, "模拟写入超时，结果未知", instance=row, actor_type="受控执行", outcome="UNKNOWN", detail="模拟远端已成功；请核对，不自动重发")
            elif invocation["state"] == "FAILED":
                row.update({"status": "FAILED", "node": "模拟写入失败"})
                self.event(db, "模拟写入明确失败", instance=row, actor_type="受控执行", outcome="FAILED", detail="MOCK_ERP_REJECTED；未生成外部对象")
            else:
                row.update({"status": "COMPLETED", "node": "审计归档", "externalObject": invocation["externalObject"]})
                self.event(db, "模拟受控写入成功", instance=row, actor_type="受控执行", detail=invocation["externalObject"])
                self.event(db, "实例完成并审计归档", instance=row, actor_type="Process Agent", detail="候选经验待审核，不自动变更规则")
        elif action == "reconcile":
            require(row["status"] == "RECONCILING", 409, "INSTANCE_STATE", "当前实例没有未知写入结果")
            invocation = next((v for v in self.all(db, "invocation") if v["instanceId"] == iid and v["state"] == "UNKNOWN"), None)
            require(invocation is not None, 409, "NO_INVOCATION", "未找到待核对的调用")
            invocation["state"] = "SUCCESS"
            self.put(db, "invocation", invocation)
            row.update({"status": "COMPLETED", "node": "审计归档", "externalObject": invocation["externalObject"]})
            self.event(db, "核对发现模拟远端已成功", instance=row, actor_type="受控执行", detail=f"{invocation['externalObject']}；调用次数仍为 1，未重复写入")
            self.event(db, "实例完成并审计归档", instance=row, actor_type="Process Agent")
        else:
            raise ApiError(404, "NOT_FOUND", "实例操作不存在")
        row["revision"] += 1
        return self.put(db, "instance", row)

    def validate_spec(self, kind, spec):
        require(isinstance(spec, dict), 422, "INVALID_SPEC", "配置必须为 JSON 对象")
        if kind == "PROCESS":
            return validate_flow(spec)
        if kind == "EXPERT":
            require(not any(spec.get(k) for k in ["tools", "connectors", "executableCommand", "toolBindings", "connectorBindings"]), 422, "EXPERT_BOUNDARY", "Expert 不可绑定工具、连接器或执行命令")
            require(isinstance(spec.get("minEvidence", 2), int) and spec.get("minEvidence", 2) >= 2, 422, "EVIDENCE_REQUIRED", "Expert 至少需要 2 个证据引用")
        if kind in {"SKILL", "TOOL"}:
            for key in ["inputSchema", "outputSchema"]:
                schema = spec.get(key)
                require(isinstance(schema, dict) and schema.get("type") == "object", 422, "INVALID_SCHEMA", f"{key} 必须为 type=object 的 JSON Schema")
        if kind == "TOOL":
            require(spec.get("access") in {"READ", "WRITE"} and spec.get("route") and spec.get("mapping"), 422, "INVALID_TOOL", "工具需要权限、路由与底层映射")
        if kind == "TASK":
            require(isinstance(spec.get("timeout"), int) and 1 <= spec["timeout"] <= 3600, 422, "INVALID_TIMEOUT", "超时必须为 1–3600 秒")
            require(isinstance(spec.get("retries"), int) and 0 <= spec["retries"] <= 5, 422, "INVALID_RETRIES", "重试次数范围为 0–5")
            require(0 <= decimal_value(spec.get("confidence"), "可信度") <= 1, 422, "INVALID_CONFIDENCE", "可信度范围为 0–1")
            ids = [s.get("id") for s in spec.get("steps", [])]
            require(len(ids) == len(set(ids)), 422, "DUPLICATE_STEP", "执行步骤 ID 不能重复")
        return {"valid": True}

    def create_asset(self, db, data, actor):
        kind, name, spec = data.get("kind"), str(data.get("name", "")).strip(), data.get("spec", {})
        require(kind in {"PROCESS", "TASK", "TOOL", "SKILL", "EXPERT"}, 422, "INVALID_KIND", "资产类型无效")
        require(1 <= len(name) <= 100, 422, "NAME_REQUIRED", "名称长度为 1–100 字")
        self.validate_spec(kind, spec)
        aid = uid(kind.lower())
        if kind == "PROCESS":
            spec["processId"] = aid
        asset = {"id": aid, "name": name, "kind": kind, "category": data.get("category", "财务运营"),
                 "owner": str(data.get("owner", "财务业务运营负责人")), "version": "v0.1.0", "state": "DRAFT",
                 "revision": 1, "spec": spec, "draftSpec": deepcopy(spec), "draftVersion": "v0.1.0",
                 "activeSpec": None, "activeVersion": None, "versions": [], "testRun": None, "createdBy": actor, "source": "本地创建"}
        self.event(db, "创建资产草稿", actor=actor, detail=name, refs=[aid])
        return self.put(db, "asset", asset)

    def save_draft(self, db, aid, data, actor):
        asset = self.get(db, "asset", aid)
        self.check_revision(asset, data)
        require(asset["state"] not in {"PENDING_APPROVAL", "APPROVED"}, 409, "VERSION_LOCKED", "审批中的版本已锁定，请完成审批或拒绝后再编辑")
        spec = data.get("spec")
        require(isinstance(spec, dict), 422, "INVALID_SPEC", "配置必须为 JSON 对象")
        # Draft graphs may temporarily be incomplete; submission compiles them.
        if asset["kind"] != "PROCESS":
            self.validate_spec(asset["kind"], spec)
        asset.update({"draftSpec": spec, "draftVersion": asset.get("draftVersion") or f"v-demo-{len(asset['versions'])+1}",
                      "state": "DRAFT", "revision": asset["revision"] + 1, "testRun": None, "draftBy": actor})
        self.event(db, "保存资产草稿", actor=actor, detail=asset["name"], refs=[aid])
        return self.put(db, "asset", asset)

    def submit_asset(self, db, aid, data, actor):
        asset = self.get(db, "asset", aid)
        self.check_revision(asset, data)
        require(asset["state"] in {"DRAFT", "REJECTED"}, 409, "VERSION_STATE", "只有草稿或驳回版本可以提交")
        spec = asset.get("draftSpec") or asset["spec"]
        self.validate_spec(asset["kind"], spec)
        test = asset.get("testRun")
        require(test and test["state"] == "SUCCEEDED" and test["specHash"] == f.digest(spec), 412, "TEST_REQUIRED", "请先对当前草稿运行固定测试")
        approval = {"id": uid("approval"), "assetId": aid, "name": asset["name"], "kind": asset["kind"],
                    "version": asset.get("draftVersion") or "v-demo-1", "spec": deepcopy(spec), "specHash": f.digest(spec),
                    "submittedBy": actor, "state": "PENDING", "revision": 1, "createdAt": now(), "comment": str(data.get("comment", ""))[:2000]}
        asset.update({"state": "PENDING_APPROVAL", "revision": asset["revision"] + 1, "approvalId": approval["id"]})
        self.put(db, "asset", asset)
        self.put(db, "approval", approval)
        self.event(db, "资产提交发布审批", actor=actor, detail=asset["name"] + "；活动版本保持不变", refs=[aid, approval["id"]])
        return {"asset": asset, "approval": approval}

    def resolve_approval(self, db, apid, data, actor):
        approval = self.get(db, "approval", apid)
        require(actor == "reviewer", 403, "REVIEWER_REQUIRED", "请切换为独立审批人身份")
        require(actor != approval["submittedBy"], 403, "SEPARATION_OF_DUTIES", "提交人不能批准自己的版本")
        self.check_revision(approval, data)
        require(approval["state"] == "PENDING", 409, "ALREADY_RESOLVED", "审批已处理")
        action = data.get("action", "APPROVE")
        require(action in {"APPROVE", "REJECT"}, 422, "INVALID_ACTION", "审批动作无效")
        if action == "REJECT":
            require(str(data.get("reason", "")).strip(), 422, "REASON_REQUIRED", "请填写拒绝原因")
        asset = self.get(db, "asset", approval["assetId"])
        require(asset.get("approvalId") == apid, 409, "REVISION_CONFLICT", "该审批已被更新版本替代")
        approval.update({"state": "APPROVED" if action == "APPROVE" else "REJECTED", "revision": approval["revision"] + 1, "resolvedBy": actor, "resolvedAt": now(), "reason": data.get("reason", "")})
        asset.update({"state": approval["state"], "revision": asset["revision"] + 1})
        self.put(db, "approval", approval)
        self.put(db, "asset", asset)
        self.event(db, "资产审批通过" if action == "APPROVE" else "资产审批驳回", actor=actor, detail=asset["name"], refs=[asset["id"], apid])
        return {"approval": approval, "asset": asset}

    def activate_asset(self, db, aid, data, actor):
        asset = self.get(db, "asset", aid)
        self.check_revision(asset, data)
        require(asset["state"] == "APPROVED", 409, "NOT_APPROVED", "仅已批准版本可以激活")
        approval = self.get(db, "approval", asset["approvalId"])
        spec = deepcopy(approval["spec"])
        require(approval["state"] == "APPROVED" and approval["specHash"] == f.digest(spec), 412, "APPROVAL_CHANGED", "审批快照不一致")
        for version in asset["versions"]:
            if version["state"] == "ACTIVE":
                version["state"] = "RETIRED"
        activated = {"id": f"{aid}:{approval['version']}", "version": approval["version"], "state": "ACTIVE", "spec": spec, "createdBy": approval["submittedBy"]}
        existing_index = next((i for i, version in enumerate(asset["versions"]) if version["version"] == approval["version"]), None)
        if existing_index is None:
            asset["versions"].append(activated)
        else:
            asset["versions"][existing_index] = activated
        asset.update({"activeSpec": spec, "spec": deepcopy(spec), "activeVersion": approval["version"], "version": approval["version"],
                      "state": "ACTIVE", "revision": asset["revision"] + 1, "draftVersion": None, "draftSpec": None})
        if asset["kind"] in {"RULES", "STAFF"}:
            config_id = spec["configId"]
            config = self.get(db, "config", config_id)
            require(config["revision"] == spec["baseRevision"], 412, "CONFIG_CHANGED", "活动配置已更新，该草稿需要基于新版重新提交")
            config.update({"spec": spec["value"], "version": approval["version"], "revision": config["revision"] + 1})
            self.put(db, "config", config)
        self.event(db, "激活已批准资产版本", actor=actor, detail=asset["name"] + "；存量实例保持绑定版本", refs=[aid])
        return self.put(db, "asset", asset)

    def test_asset(self, db, aid, data, actor):
        asset = self.get(db, "asset", aid)
        self.check_revision(asset, data)
        spec = asset.get("draftSpec") or asset["spec"]
        self.validate_spec(asset["kind"], spec)
        cases = []
        for name, amount, po, has_receipt, authorized, expected_pass, expected_recommendation in [
            ("差异 1.2%，证据完整", 1827800, 1850000, True, True, True, "ALLOW_REVIEW"),
            ("缺少收货记录", 1650000, 1850000, False, True, False, "ABSTAIN"),
            ("新增服务未经授权", 1650000, 1850000, True, False, False, "BLOCK"),
            ("阈值边界恰好 2%", 1813000, 1850000, True, True, True, "ALLOW_REVIEW"),
        ]:
            rule = evaluate_rule(amount, po, has_receipt=has_receipt, authorized=authorized)
            advice = expert_advice(f.base_evidence("test") if has_receipt else [], rule)
            cases.append({"name": name, "passed": rule["passed"] == expected_pass and advice["recommendation"] == expected_recommendation,
                          "ruleResult": rule, "expertResult": advice})
        passed = sum(case["passed"] for case in cases)
        run = {"id": uid("test"), "assetId": aid, "state": "SUCCEEDED" if passed == len(cases) else "FAILED", "specHash": f.digest(spec),
               "createdAt": now(), "completedAt": now(), "simulated": True, "sampleCount": len(cases),
               "passed": passed, "cases": cases, "message": "固定用例实际执行 RuleEvaluator 与证据判断；非真实模型准确率或延迟评测"}
        asset.update({"testRun": run, "revision": asset["revision"] + 1})
        self.put(db, "asset", asset)
        self.put(db, "test_run", run)
        self.event(db, "运行固定沙箱测试", actor=actor, detail=f"{asset['name']} · {len(cases)} 个演示用例", refs=[aid, run["id"]])
        return {"asset": asset, "run": run}

    def config_draft(self, db, data, actor):
        cid, spec = data.get("configId"), data.get("spec")
        config = self.get(db, "config", cid)
        self.check_revision(config, data)
        if cid == "staffing":
            require(isinstance(spec, list) and spec, 422, "STAFF_REQUIRED", "至少配置一个人工介入点")
            for item in spec:
                require(isinstance(item, dict) and item.get("point") and item.get("owner") and item.get("backup") and
                        isinstance(item.get("minutes"), int) and 0 < item["minutes"] <= 1440, 422, "INVALID_STAFF", "介入点必须有主备负责人及正整数响应时限（最多 1440 分钟）")
            kind, name = "STAFF", "财务人员分配"
        else:
            require(cid in {"rules-P1", "rules-P2"} and isinstance(spec, dict), 422, "INVALID_RULES", "规则配置无效")
            if cid == "rules-P1":
                evaluate_rule(100, 100, spec.get("thresholdPercent"))
                require(isinstance(spec.get("duplicateWindowDays"), int) and spec["duplicateWindowDays"] > 0, 422, "INVALID_RULES", "重复发票窗口必须为正整数天")
                require(isinstance(spec.get("quantityTolerance"), int) and spec["quantityTolerance"] >= 0 and decimal_value(spec.get("taxTolerancePoints"), "税率容忍度") >= 0, 422, "INVALID_RULES", "数量及税率容忍度不可为负")
            else:
                require(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(spec.get("deadline", ""))), 422, "INVALID_RULES", "截止时间格式为 HH:MM")
                require(isinstance(spec.get("maxAgeDays"), int) and spec["maxAgeDays"] > 0 and decimal_value(spec.get("balanceChangePercent"), "余额幅度") >= 0 and decimal_value(spec.get("delayHours"), "延期时长") >= 0, 422, "INVALID_RULES", "关账阈值无效")
            kind, name = "RULES", spec.get("name", "财务业务规则")
        aid = uid("config")
        value = {"configId": cid, "value": spec, "baseRevision": config["revision"]}
        asset = {"id": aid, "kind": kind, "name": name, "category": "部门治理", "owner": "财务业务运营负责人",
                 "version": f"v-demo-{config['revision']+1}-{aid[-4:]}", "draftVersion": f"v-demo-{config['revision']+1}-{aid[-4:]}",
                 "state": "DRAFT", "revision": 1, "spec": value, "draftSpec": value,
                 "activeSpec": None, "activeVersion": None, "versions": [], "testRun": None, "createdBy": actor}
        self.put(db, "asset", asset)
        tested = self.test_asset(db, aid, {"expectedRevision": 1}, actor)
        return self.submit_asset(db, aid, {"expectedRevision": tested["asset"]["revision"], "comment": "部门配置待审批版本"}, actor)
