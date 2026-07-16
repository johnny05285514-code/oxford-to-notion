# Changelog / 更新日志

## v1.4.3 — 2026-07-16

### 简体中文

- 为“最近导入”第二行增加明确的 8 像素底部安全留白，避免按钮边框被裁切。
- 将窗口默认高度和最小高度调整为 560 像素，以适应 Windows 实际字体与显示缩放。
- 新增界面回归测试，要求最小窗口下仍保留底部安全距离。

### English

- Added an explicit 8-pixel bottom safety margin below the second recent-import row so button borders are not clipped.
- Increased the default and minimum window height to 560 pixels for real Windows font and display scaling.
- Added a GUI regression test that requires bottom clearance at the minimum window size.

## v1.4.2 — 2026-07-16

### 简体中文

- 修复“最近导入”出现第二行时，最小窗口高度下按钮被底部裁切的问题。
- 隐藏“打开 Notion”和更新提醒时，其对应空白区域现在会一起隐藏，为历史记录保留完整空间。
- 窗口最小高度增加少量安全余量，以适应 Windows 字体和显示缩放差异。

### English

- Fixed the second row of recent imports being clipped at the minimum window height.
- Hidden Open Notion and update controls no longer leave unused spacing behind, preserving room for import history.
- Added a small minimum-height safety margin for Windows font and display-scaling differences.

## v1.4.1 — 2026-07-14

### 简体中文

- 修复重复导入时可能删除用户私人 Notion 笔记的问题。
- Oxford 正文现在位于 `Oxford content — managed by Oxford to Notion` 管理区域中；程序以后只更新这个区域。
- 旧版本页面第一次重新导入时保留全部旧正文，并新增安全管理区域。Oxford 内容可能暂时重复，但用户笔记不会被程序猜测或删除。
- 更新管理区域时先完整写入新内容，成功后才删除旧管理区域，降低网络中断造成内容丢失的风险。
- 修复配置测试期间修改 Token 或数据库后，旧测试结果仍可能显示成功的问题。
- 改进 Notion 断网、DNS、代理和非标准 HTTP 错误提示。
- 固定经过验证的 `notion-client 2.7.0` 依赖版本。

### English

- Fixed repeat imports potentially deleting personal notes in the Notion page body.
- Oxford content now lives inside an `Oxford content — managed by Oxford to Notion` section; future imports replace only that section.
- The first repeat import of a legacy page preserves every old body block and adds the safe managed section. Oxford content may temporarily appear twice, but the app never guesses which legacy blocks are personal notes.
- Managed content is fully written before an older managed section is removed, reducing data-loss risk during network failures.
- Fixed stale connection-test results being accepted after the Token or database value changed.
- Improved friendly handling for Notion connection, DNS, proxy, and non-standard HTTP failures.
- Pinned the verified `notion-client 2.7.0` dependency.
