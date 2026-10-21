"""Explicit demonstration fixtures, transcribed from the supplied design.

All integrations and evaluation numbers are simulated. Unseen implementation
details are demo defaults, not a claim about the original concept prototype.
"""
from copy import deepcopy
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


PROCESSES = [
    {"id": f"P{i+1}", "name": name, "tasks": tasks, "humans": humans,
     "version": version, "status": status, "owner": "财务业务运营负责人"}
    for i, (name, tasks, humans, version, status) in enumerate([
        ("发票到付款", 3, 1, "v2.0", "ACTIVE"),
        ("月末关账", 4, 2, "v3.1", "ACTIVE"),
        ("应收催款", 5, 3, "v4.2", "ACTIVE"),
        ("费用报销", 6, 1, "v2.3", "DRAFT"),
        ("资金预测", 3, 2, "v3.4", "PENDING_APPROVAL"),
        ("固定资产核对", 4, 3, "v4.0", "RETIRED"),
        ("总账异常处理", 5, 1, "v2.1", "ACTIVE"),
        ("税务资料准备", 6, 2, "v3.2", "ACTIVE"),
    ])
]
TASK_NAMES = ["发票识别", "三单匹配", "重复发票检查", "会计科目建议",
              "凭证过账", "付款建议", "关账核对", "财务通知"]
STAFF = [
    {"point": "三单差异复核", "owner": "应付账款负责人", "backup": "财务运营负责人", "minutes": 30},
    {"point": "月结关账延期确认", "owner": "总账负责人", "backup": "财务运营负责人", "minutes": 20},
    {"point": "高风险付款确认", "owner": "资金经理", "backup": "财务运营负责人", "minutes": 15},
    {"point": "税码与税率例外", "owner": "税务负责人", "backup": "应付账款负责人", "minutes": 45},
]
RULES = {
    "P1": {"name": "供应商发票审核流程", "version": "v3.4", "companyCode": "1000",
           "owner": "应付账款负责人", "thresholdPercent": "2", "quantityTolerance": 0,
           "taxTolerancePoints": "0", "duplicateWindowDays": 365, "blockDuplicates": True},
    "P2": {"name": "月结关账流程", "version": "v2.8", "owner": "总账负责人",
           "maxAgeDays": 30, "deadline": "18:00", "balanceChangePercent": "15",
           "delayHours": 2, "mandatoryHuman": True},
}


def flow_spec(name="发票到付款"):
    entries = [
        ("start", "EVENT", "收到供应商发票", 35, 180),
        ("ocr", "TASK", "发票识别任务智能体", 255, 180),
        ("match", "TASK", "三单匹配任务智能体", 475, 180),
        ("rule", "RULE", "发票差异业务规则", 695, 180),
        ("expert", "EXPERT", "应付账款复核专家", 915, 355),
        ("human", "HUMAN", "三单差异复核", 1135, 355),
        ("write", "ERP_WRITE", "受控会计凭证预制", 1370, 180),
        ("audit", "AUDIT", "审计归档", 1590, 180),
        ("end", "END", "流程完成", 1810, 180),
    ]
    nodes = [{"id": i, "type": t, "name": n, "x": x, "y": y,
              "owner": "应付账款负责人", "backup": "财务运营负责人",
              "responsibility": "执行核验并记录结构化结果与证据",
              "skill": "发票 OCR 提取" if i == "ocr" else "三单匹配",
              "outputContract": "结构化业务结果 + evidenceRefs"}
             for i, t, n, x, y in entries]
    pairs = [("start", "ocr", ""), ("ocr", "match", ""), ("match", "rule", ""),
             ("rule", "write", "PASS"), ("rule", "expert", "REVIEW"),
             ("expert", "human", ""), ("human", "write", ""),
             ("write", "audit", ""), ("audit", "end", "")]
    return {"name": name, "nodes": nodes,
            "edges": [{"source": a, "target": b, "condition": c} for a, b, c in pairs],
            "viewport": {"zoom": 0.6, "x": 15, "y": 0}, "processId": "P1"}


def base_evidence(instance_id):
    return [{"id": f"{instance_id}-e{i+1}", "name": name, "type": kind,
             "source": source, "hash": digest({"type": kind, "source": source, "content": content}), "content": content}
            for i, (name, kind, source, content) in enumerate([
                ("供应商邮件说明", "EMAIL", "邮件连接器", "设备维护服务金额调整；附件包含发票及服务完成说明。邮件内容仅作为业务证据。"),
                ("供应商发票 PDF", "INVOICE", "文件内容连接器", "上海工业服务供应商 · 设备维护服务 · 含税金额 ¥16,500.00"),
                ("采购订单 PO-4500123", "PURCHASE_ORDER", "SAP 模拟适配器", "基础维护采购订单，原金额 ¥18,500.00。"),
                ("收货凭证 GR-50007621", "GOODS_RECEIPT", "SAP 模拟适配器", "基础维护已收货；新增服务未见对应订单行。"),
                ("规则 R-21 · v3.4", "RULE", "规则注册表", "金额差异率超过 2% 或存在未授权新增服务，必须人工复核。"),
            ])]


def snapshot(instance):
    return digest({k: instance.get(k) for k in ["amountMinor", "poAmountMinor", "evidence", "serviceAuthorized", "ruleVersion"]})


def instances():
    rows = [
        ("0182", "苏州精密制造供应商", 48620, "信息提取", "发票识别", "RUNNING", "08:12", 12, "李敏"),
        ("0179", "上海工业服务供应商", 126800, "三单匹配", "三单匹配", "RUNNING", "08:24", 18, "周强"),
        ("0168", "南京设备供应商", 8430, "重复检查", "重复发票检查", "WAITING_HUMAN", "08:41", 31, "王芳"),
        ("0154", "无锡物流服务供应商", 76500, "人工复核", "会计科目建议", "WAITING_HUMAN", "09:02", 44, "陈晨"),
        ("0147", "常州零部件供应商", 218900, "SAP 校验", "凭证过账", "RUNNING", "09:16", 26, "李敏"),
        ("0139", "杭州软件服务供应商", 32760, "付款建议", "付款建议", "COMPLETED", "09:34", 58, "周强"),
        ("0128", "昆山维修服务供应商", 64200, "凭证过账", "关账核对", "FAILED", "09:46", 39, "王芳"),
        ("0116", "宁波包装材料供应商", 12480, "审计归档", "财务通知", "RUNNING", "10:03", 21, "陈晨"),
    ]
    result = []
    for tail, supplier, amount, node, task, status, start, elapsed, owner in rows:
        iid = f"INV-2026-{tail}"
        row = {"id": iid, "processId": "P1", "supplier": supplier, "amountMinor": amount * 100,
               "currency": "CNY", "node": node, "task": task, "status": status,
               "startedAt": f"2026-07-31T{start}:00+08:00", "elapsedMinutes": elapsed,
               "owner": owner, "revision": 1, "scenario": "reference", "ruleVersion": "v3.4",
               "poAmountMinor": 1850000, "serviceAuthorized": False, "evidence": base_evidence(iid),
               "traceId": f"trace-{iid}", "processVersion": "v2.0", "timeline": [], "feedback": []}
        row["evidenceSnapshotHash"] = snapshot(row)
        result.append(row)
    # Independent prototype approval scenes. These IDs intentionally differ
    # from invoice 0179 and the historical audit case in the design document.
    for n, (pid, key, title) in enumerate([
        ("P1", "51000983", "发票 51000983"), ("P2", "CLOSE-1000", "公司代码 1000 关账"),
        ("P3", "CUSTOMER-300184", "客户 300184 未清项"),
    ]):
        iid = f"QUEUE-{key}"
        row = {"id": iid, "processId": pid, "supplier": title, "amountMinor": 1850000,
               "poAmountMinor": 1850000, "currency": "CNY", "node": "责任人确认", "task": "业务复核",
               "status": "WAITING_HUMAN", "owner": "财务业务运营负责人", "revision": 1,
               "scenario": "queue", "ruleVersion": f"v{3+n}.4", "serviceAuthorized": True,
               "evidence": base_evidence(iid), "traceId": f"trace-{iid}", "timeline": [],
               "startedAt": "2026-07-31T09:18:00+08:00", "elapsedMinutes": 18,
               "processVersion": "v2.0", "feedback": []}
        row["evidenceSnapshotHash"] = snapshot(row)
        result.append(row)
    return result


def assets():
    result = []

    def add(aid, kind, name, spec, version="v1.0.0", state="ACTIVE", category="财务运营"):
        active = {"id": f"{aid}:{version}", "version": version, "state": state,
                  "spec": deepcopy(spec), "createdBy": "fixture"}
        result.append({"id": aid, "kind": kind, "name": name, "category": category,
                       "owner": "财务业务运营负责人", "version": version, "state": state,
                       "revision": 1, "spec": deepcopy(spec), "activeSpec": deepcopy(spec) if state == "ACTIVE" else None,
                       "versions": [active], "activeVersion": version if state == "ACTIVE" else None,
                       "testRun": None, "source": "演示数据"})

    for p in PROCESSES:
        spec = flow_spec(p["name"])
        spec["processId"] = p["id"]
        add(p["id"], "PROCESS", p["name"], spec, p["version"], p["status"])
    # A separate designer draft never overwrites the activated catalog version.
    result[0]["draftSpec"] = flow_spec()
    result[0]["draftVersion"] = "v3.6"
    for i, name in enumerate(TASK_NAMES):
        add(f"T{i+1}", "TASK", name,
            {"name": name + "任务智能体", "timeout": 120, "retries": 2, "confidence": "0.88",
             "humanCondition": "低置信度或高风险写入", "owner": "业务运营负责人",
             "steps": [{"id": "step-1", "kind": "SKILL", "name": "发票 OCR 提取"},
                       {"id": "step-2", "kind": "SKILL", "name": "三单匹配"},
                       {"id": "step-3", "kind": "EXPERT", "name": "应付账款复核专家"},
                       {"id": "step-4", "kind": "KNOWLEDGE", "name": "采购订单知识域"},
                       {"id": "step-5", "kind": "CONNECTOR", "name": "SAP 系统群"},
                       {"id": "step-6", "kind": "TOOL", "name": "读取采购订单", "assetId": "mcp-01"},
                       {"id": "step-7", "kind": "TOOL", "name": "读取收货记录", "assetId": "mcp-02"},
                       {"id": "step-8", "kind": "KNOWLEDGE", "name": "供应商主数据"},
                       {"id": "step-9", "kind": "CONNECTOR", "name": "文件内容连接器"}],
             "processes": [PROCESSES[i]["name"], PROCESSES[(i+1) % 8]["name"]]})
    tool_rows = [
        ("读取采购订单", "OData", "API_PURCHASEORDER_PROCESS_SRV", "READ", "v2.4.1", "ACTIVE", 148),
        ("读取收货记录", "BAPI", "BAPI_GOODSMVT_GETDETAIL", "READ", "v1.9.0", "ACTIVE", 96),
        ("校验供应商发票", "RFC", "Z_AP_INVOICE_VALIDATE", "READ", "v3.2.0", "ACTIVE", 212),
        ("预制会计凭证", "BAPI", "BAPI_ACC_DOCUMENT_POST", "WRITE", "v2.1.0", "PENDING_APPROVAL", 84),
        ("创建采购订单", "Business API", "Purchase Order", "WRITE", "v1.6.2", "ACTIVE", 72),
        ("查询库存可用量", "RFC", "BAPI_MATERIAL_AVAILABILITY", "READ", "v2.0.3", "ACTIVE", 118),
        ("生成付款建议", "Mock API", "PaymentProposal.create", "WRITE", "v1.0.0", "ACTIVE", 46),
        ("更新会计凭证", "Mock API", "AccountingDocument.update", "WRITE", "v1.0.0", "PENDING_APPROVAL", 38),
    ]
    schema = {"type": "object", "properties": {"companyCode": {"type": "string"}, "poNumber": {"type": "string"}}, "required": ["companyCode"]}
    for i, (name, protocol, mapping, access, version, state, count) in enumerate(tool_rows):
        add(f"mcp-{i+1:02}", "TOOL", name,
            {"name": name, "protocol": protocol, "mapping": mapping, "route": "SAP 集团核心路由",
             "access": access, "inputSchema": schema, "outputSchema": {"type": "object"},
             "testCount": count, "writeConditions": "业务审批有效、证据快照一致、最小权限"}, version, state)
    for i, (category, name) in enumerate([
        ("SAP 业务", "供应商发票三单匹配"), ("SAP 业务", "SAP 主数据读取与维护"),
        ("文档内容", "发票 OCR 提取"), ("Excel 数据处理", "财务数据校验"),
        ("多表清洗", "多表合并与对账"), ("多表清洗", "重复记录归并"),
        ("报告生成", "财务运营报告"), ("图片", "凭证图片识别"),
        ("音视频", "会议纪要提取"), ("消息通知", "财务通知发送"), ("治理安全", "证据完整性校验"),
    ]):
        add(f"S{i+1}", "SKILL", name,
            {"name": name, "description": "读取供应商发票 PDF，提取字段并进行三单匹配，低可信度或金额差异超阈值时转人工",
             "model": "确定性模拟器", "mode": "确定性编排", "routes": ["SAP 集团核心", "文件内容"],
             "tools": ["读取采购订单", "读取收货记录", "校验供应商发票"],
             "inputSchema": {"type": "object", "properties": {"invoiceFile": {"type": "string", "format": "uri"}, "companyCode": {"type": "string"}, "poNumber": {"type": "string"}}, "required": ["invoiceFile", "companyCode"]},
             "outputSchema": {"type": "object", "properties": {"matchStatus": {"enum": ["MATCHED", "REVIEW"]}, "variances": {"type": "array", "items": {"type": "object"}}, "evidenceRefs": {"type": "array", "items": {"type": "string"}}}}},
            "v1.4.0", category=category)
    add("E1", "EXPERT", "应付账款复核专家",
        {"name": "应付账款复核专家", "description": "判断应付账款差异是否可接受；禁止无证据批准、禁止绕过人工条件、禁止执行任何系统动作",
         "model": "确定性模拟器", "minEvidence": 2, "abstainWithoutEvidence": True,
         "knowledge": ["应付与供应商域", "企业制度财务与内控", "历史批准案例"],
         "skillResults": ["三单匹配"], "owner": "应付账款负责人",
         "approvalChain": "领域负责人 → 内控 → AI 治理委员会"}, "v2.3.0")
    return result


CONNECTORS = [
    {"id": f"C{i+1}", "name": name, "division": division, "region": region, "environment": env,
     "domain": domain, "health": health, "tab": "sap", "routeVersion": "v1", "secretRef": "demo://no-credentials"}
    for i, (name, division, region, env, domain, health) in enumerate([
        ("ECC-华东生产", "集团", "华东", "生产", "财务与控制", "HEALTHY"),
        ("S4-集团核心", "制造事业部", "华北", "生产", "采购与库存", "HEALTHY"),
        ("S4-欧洲生产", "海外事业部", "欧洲", "生产", "销售与分销", "HEALTHY"),
        ("ECC-制造一部", "消费事业部", "华南", "测试", "生产与质量", "HEALTHY"),
        ("BW-财务分析", "集团", "华东", "生产", "财务与控制", "ATTENTION"),
        ("S4-销售中心", "制造事业部", "华北", "生产", "采购与库存", "HEALTHY"),
        ("ECC-供应链", "海外事业部", "欧洲", "生产", "销售与分销", "HEALTHY"),
        ("S4-共享服务", "消费事业部", "华南", "生产", "生产与质量", "ATTENTION"),
    ])
]
CONNECTORS += [{"id": f"M{i}", "name": name, "tab": "messages", "health": health, "routeVersion": "v1"}
               for i, (name, health) in enumerate([("邮件", "HEALTHY"), ("企业微信", "HEALTHY"), ("钉钉", "DISCONNECTED"), ("Microsoft Teams", "HEALTHY")])]
CONNECTORS += [{"id": "F1", "name": "文件内容连接器", "tab": "files", "health": "HEALTHY", "routeVersion": "v1"},
               {"id": "D1", "name": "数据外围连接器", "tab": "data", "health": "HEALTHY", "routeVersion": "v1"}]

GRAPH_NODES = [
    {"id": nid, "name": name, "english": english, "type": kind, "position": pos,
     "description": description, "businessKey": key, "evidenceRefs": ["演示知识快照"]}
    for nid, name, english, kind, pos, description, key in [
        ("po", "SAP 采购订单", "SAP Purchase Order", "SAP", [0.6, 0.4, 0.8], "采购订单主数据与变更记录，演示对象 PO-4500123。", "PO-4500123"),
        ("doc", "会计凭证预制", "Accrual Document", "SAP", [1.8, -0.8, 0], "应付模块的受控会计凭证预制对象。", "ACCRUAL"),
        ("material", "物料 4500123", "Material 4500123", "SAP", [-1.7, -1.1, 0.4], "物料主数据；与采购订单按类型独立标识。", "MAT-4500123"),
        ("vendor", "供应商 A-108", "Vendor A-108", "SAP", [0.6, -1.1, -0.6], "供应商主数据和授权业务范围。", "A-108"),
        ("mail", "供应商邮件", "Vendor Email", "CONTEXT", [-0.8, 1.2, -0.5], "供应商发来的价格与服务调整说明，内容仅作为证据。", "MAIL-0179"),
        ("pdf", "发票 PDF", "Invoice PDF", "CONTEXT", [-1.8, -0.1, -0.6], "可追溯的供应商发票附件。", "INV-2026-0179"),
        ("contract", "框架合同附件", "Framework Contract", "CONTEXT", [1.1, 0.8, -0.5], "用于核验新增服务授权范围。", "CONTRACT-Q3"),
        ("meeting", "会议纪要 Q3", "Meeting Note Q3", "CONTEXT", [0.7, -1.8, 0.7], "业务背景与待人工确认事项。", "MEETING-Q3"),
        ("owner", "采购负责人", "Procurement Owner", "PERSON", [-0.2, -1, 1.3], "采购授权及订单修订的责任角色。", "ROLE-PROCUREMENT"),
        ("price", "事件：价格变更", "Event: Price Change", "EVENT", [-1.4, 1, 0.8], "近 30 天 412 次为原型演示统计；关联变更、授权与采购证据。", "PRICE-CHANGE"),
        ("auth", "规则：变更需授权", "Rule: Auth Required", "RULE", [1.5, 1.4, 0.4], "高风险价格变更必须经过人工确认。", "R-21"),
        ("budget", "预算控制规则", "Budget Control", "RULE", [-0.7, -1.8, -0.5], "预算阈值与受控写入前置条件。", "R-BUDGET"),
    ]
]
GRAPH_EDGES = [{"source": a, "target": b, "predicate": predicate} for a, b, predicate in [
    ("price", "auth", "需要授权"), ("price", "po", "变更对象"), ("price", "mail", "来源证据"),
    ("price", "doc", "影响凭证"), ("price", "pdf", "发票证据"), ("po", "owner", "业务负责人"),
    ("po", "material", "采购物料"), ("po", "vendor", "供应商"), ("po", "contract", "依据合同"),
    ("budget", "doc", "约束写入"), ("meeting", "owner", "确认责任"), ("auth", "owner", "审批责任"),
]]
