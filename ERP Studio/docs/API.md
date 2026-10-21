# 本地 Demo API

统一前缀 `/api/v1`，JSON 同源接口。默认部门 `finance`、演示身份 `operator`。

请求头：

```text
X-Department-ID: finance
X-Demo-Actor: operator | reviewer | designer | auditor
Idempotency-Key: 每次新操作唯一的 UUID，同一次重试保持不变
```

这是本机演示身份，不能替代真实认证。错误格式 `{code,message,details,traceId}`；版本冲突 409、证据或前提变化 412、配置校验失败 422、权限不足 403、未知部门 404。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 服务与模拟状态 |
| GET | `/bootstrap` | 目录、配置、连接、版本审批与身份 |
| GET | `/runtime/summary?mode=replay或linked` | 原型快照或联动实例实时汇总 |
| GET | `/processes/{id}/instances?mode=linked&status=...` | 实例及互斥状态计数 |
| GET | `/instances/{id}` | 纯读取详情、证据、待办、模拟调用与时间线 |
| POST | `/scenarios/linked` | 创建固定发票闭环，fault: none / missing_receipt / write_timeout / write_failure |
| POST | `/instances/{id}/events` | 0179 的显式 email_adjustment_0179 事件 |
| POST | `/instances/{id}/evidence` | 补证，旧批准失效并创建新待办 |
| POST | `/instances/{id}/advance` | 写入前检查并调用模拟适配器 |
| POST | `/instances/{id}/reconcile` | 核对模拟调用的未知结果 |
| POST | `/instances/{id}/feedback` | 归档实例反馈进入待审核池 |
| GET | `/decisions` | 待决队列 |
| POST | `/decisions/{id}/resolve` | APPROVE / REJECT / REQUEST_CHANGES / RETURN_FOR_REWORK |
| POST | `/decisions/delegate` | 批量委派，验证每条待办 revision |
| GET | `/assets?kind=TOOL&search=采购&access=READ&state=ACTIVE` | 资产目录，条件 AND 组合 |
| GET | `/assets/{id}` | 配置、草稿、活动版与测试 |
| POST | `/assets` | 新建 PROCESS / TASK / TOOL / SKILL / EXPERT 草稿 |
| PUT | `/assets/{id}/draft` | 保存草稿，审批中或待激活版本不可编辑 |
| POST | `/assets/{id}/test-runs` | 执行并保存四个确定性沙箱用例 |
| GET | `/test-runs/{id}` | 固定测试记录 |
| POST | `/assets/{id}/submit` | 当前草稿测试通过后提交审批 |
| GET | `/approvals` | 资产与部门配置发布审批 |
| POST | `/approvals/{id}/resolve` | 独立 reviewer 批准或拒绝 |
| POST | `/assets/{id}/activate` | 激活确切已批准的配置快照 |
| GET | `/department/dashboard` | 原型演示指标与生效配置 |
| POST | `/config-drafts` | 人员 / 规则保存为待审批版本 |
| GET | `/connectors?tab=sap或messages或files或data` | 四类连接目录 |
| POST | `/connectors/{id}/test` | 模拟连接健康检查 |
| GET | `/knowledge/graph?type=SAP&search=采购` | 过滤节点与可见端点之间的边 |
| GET | `/knowledge/entities/{id}` | 关联实体详情 |
| GET | `/audit/events?instanceId=...&search=...` | 追加式审计，最多返回最近 500 条 |
| GET | `/events?after=0` | outbox 增量事件与 cursor |
| POST | `/demo/reset` | 正文 confirm=RESET_DEMO 清空并重建当前 Demo 数据 |

审批示例：

```json
{
  "action": "APPROVE",
  "reason": "已核验授权及修订订单",
  "expectedRevision": 1,
  "evidenceSnapshotHash": "从最新待办中读取的完整指纹"
}
```

补证示例：

```json
{
  "expectedRevision": 1,
  "note": "已核实新增服务授权并修订订单",
  "poAmountMinor": 1650000,
  "includeReceipt": true
}
```

mutation API 均同步完成本地确定性操作；没有真实后台作业或 SSE 长连接。outbox 和业务 / 审计同事务提交，客户端可增量轮询。
