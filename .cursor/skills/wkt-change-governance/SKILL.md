---
name: wkt-change-governance
description: WKT 变更治理与文档合规。在改代码、修 Bug、发功能、登记 CHANGELOG、更新 SOP、记录根因防复发时使用；用户提到 changelog、SOP、bug 反复、合规、登记时使用。
---

# WKT 变更治理

## 何时使用

- 任何代码/配置/行为改动
- Bug 修复
- 用户要求记 change list / SOP /  bug 逻辑

## 步骤

1. **Read** [`docs/change/AGENT-COMPLIANCE.md`](../../../docs/change/AGENT-COMPLIANCE.md)
2. 若修 Bug → **Read/Search** [`docs/change/BUG-FIX-LOG.md`](../../../docs/change/BUG-FIX-LOG.md)
3. 实现 + 测试
4. **CL-XXXX** → `CHANGELOG.md`（含根因/防复发/SOP 字段）
5. 若修复 → **BF-XXXX** → `BUG-FIX-LOG.md`
6. 若用户可见 → 更新 `docs/SOP/系统操作SOP.md`
7. 若 UI → `UI-CHANGELOG.md`
8. 回复用户：CL、BF、SOP、测试、重启

## CL 模板要点

- 类型=修复 → 根因 + 防复发 + 关联 BF 必填
- SOP=否 → 必须写「SOP 免同步原因」

## 修 Bug 前必问

- 是否已有 BF 记录相同根因？
- 防复发测试是否存在？若无则新增。

## 文档

- 合规：[`AGENT-COMPLIANCE.md`](../../../docs/change/AGENT-COMPLIANCE.md)
- Bug：[`BUG-FIX-LOG.md`](../../../docs/change/BUG-FIX-LOG.md)
- 变更：[`CHANGELOG.md`](../../../docs/change/CHANGELOG.md)
