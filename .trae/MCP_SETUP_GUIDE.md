# Trae MCP 工具配置指南

你已成功安装了 Claude 风格的 Prompt 角色 Skills。对于更强大的 **MCP (Model Context Protocol)** 工具（如连接数据库、Linear、GitHub），你需要手动将配置添加到 Trae 设置中。

## 步骤 1: 获取配置
项目目录中已生成参考配置文件：
`config/mcp_config_reference.json`

## 步骤 2: 配置 Trae
1. 打开 Trae 左下角的 **Settings (设置)** -> **MCP Servers**。
2. 点击 **Edit in settings.json** (或类似按钮，通常是编辑 JSON 配置文件)。
3. 将 `config/mcp_config_reference.json` 中的内容复制到你的 `settings.json` 的 `mcpServers` 字段中。

## 步骤 3: 填写密钥
**重要**：复制后，请务必将 JSON 中的占位符替换为你真实的 API Key：
- **Postgres**: 已自动填充为本地默认开发库 `postgresql://postgres:postgres@localhost:5432/si_factory`。
- **Linear**: 填入你的 `LINEAR_API_KEY`。
- **GitHub**: 填入你的 `GITHUB_PERSONAL_ACCESS_TOKEN`。
- **Brave Search**: 填入你的 `BRAVE_API_KEY`。

## 已安装的 Skills (角色)
你可以直接在对话中使用以下 Skill：
- `@technical-writer`: 编写专业文档
- `@code-reviewer`: 代码审计
- `@system-architect`: 系统架构设计
- `@qa-engineer`: 测试与 QA
- `@python-optimizer`: 代码性能优化

无需额外配置，直接调用即可！
