# WKT 设计资源

## 当前 UI 主题

**Linear 风格（深色）** · 来源：[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 中的 `linear.app` 设计分析。

| 文件 | 说明 |
|------|------|
| `DESIGN.md` | 项目当前生效的设计规范（供 AI / 开发参考） |
| `ui-style-guide-v1.md` | WKT 布局与组件约定 |
| `awesome-design-md/` | 完整设计库（73 套大厂 DESIGN.md） |
| **方案库预览** | 浏览器打开 **`/design-gallery`** |

### 如何切换其他大厂风格

1. 在 `awesome-design-md/design-md/` 下选择目标品牌（如 `stripe`、`ibm`、`notion`）。
2. 将其 `DESIGN.md` 中的色彩 / 字体 / 圆角 token 映射到 `test_impl/web/static/style.css` 的 `:root` 变量。
3. 更新本目录 `DESIGN.md` 中的「当前主题」说明。

### awesome-design-md 是什么？

[awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 收集了 Stripe、Linear、IBM、Notion 等品牌的 **DESIGN.md** 设计系统文档，供 AI 编码助手读取后生成风格一致的 UI。本项目已将其克隆到 `docs/design/awesome-design-md/`（约 2MB，MIT 许可）。
