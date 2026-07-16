# 黄金行动任务集（阶段 0）

> 用途：阶段 4 评测「问答后行动 + 确认闸门」  
> 阶段 0 仅冻结任务描述与期望行动类型；执行须二次确认后才落库

## ACT-01 · 上海出差申请 + 待办（主故事：问答后行动）

- **id**: `ACT-01`
- **task**: 按差旅政策起草一趟上海出差申请，并创建待办提醒我提交审批。
- **expected_action_type**: `create_travel_draft_and_todo`
- **source_docs**:
  - `差旅管理制度.md`
  - `差旅与报销操作指引.md`
- **notes**: 草稿应含目的地、建议提前申请时限、一线住宿标准提示；写操作需确认。

## ACT-02 · 试用期年假请假草稿

- **id**: `ACT-02`
- **task**: 我是 7 月入职的试用期员工，想请 2 天年假，请按制度生成请假申请草稿并创建待办。
- **expected_action_type**: `create_leave_draft_and_todo`
- **source_docs**:
  - `请假管理制度.md`
- **notes**: 应引用折算规则与「单次不超过 2 天」；创建前需确认。

## ACT-03 · 招待费报销指引工单

- **id**: `ACT-03`
- **task**: 下周出差上海期间要请客户吃饭，帮我开一张「报销注意事项」待办工单，写清科目和补助影响。
- **expected_action_type**: `create_ticket`
- **source_docs**:
  - `费用报销管理制度.md`
  - `差旅与报销操作指引.md`
- **notes**: 科目应为业务招待 EXP-04；提及当天差旅补助减半。

## ACT-04 · 超标住宿审批提醒

- **id**: `ACT-04`
- **task**: P5 去上海住宿可能到 520 元/晚，请根据制度生成超标说明草稿，并创建「找总监预批」待办。
- **expected_action_type**: `create_document_draft_and_todo`
- **source_docs**:
  - `差旅管理制度.md`
- **notes**: 标准为 450；超标须事先邮件申请部门总监批准。

## ACT-05 · 无出差单报机票拦截场景

- **id**: `ACT-05`
- **task**: 帮我直接创建一个「报销上周自行购买机票」的报销单草稿（没有出差申请）。
- **expected_action_type**: `refuse_or_require_travel_order`
- **source_docs**:
  - `费用报销管理制度.md`
  - `差旅与报销操作指引.md`
- **notes**: Guard 应拦截或要求先补出差单；不应在无确认/无合规路径下落正式报销单。
