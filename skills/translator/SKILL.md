---
name: translator
description: 用于同步和翻译 FastMCP 官方 Mintlify 文档。Use when Codex needs to sync the official FastMCP docs into origin, rebuild multilingual i18n docs.json, extract and fix document links, validate with non-blocking Mintlify CLI checks, and translate i18n/zh documentation with progress tracking and subagents.
---

# Translator

## 概览

使用本 skill 维护 FastMCP 文档的多语言仓库：同步官方 `docs/` 到 `origin/`，更新 Mintlify 多语言配置，修正语言目录中的跳转路径，用非阻塞 Mintlify CLI 命令验证文档，然后翻译 `i18n/zh`。

默认仓库根目录是当前 FastmcpDocs 项目。所有路径命令都应在仓库根目录执行，除非步骤中明确要求进入 `i18n/`。

## 严格约束
- 根目录的 origin 内容是基线，无论如何你都不能去修改它，它只接受从官方 repo 仓库同步过来数据。

## 开始前

先询问用户 FastMCP 官方 repo 的本地 clone 目录。用户必须自己提前准备这个 repo；本 skill 只负责检查该目录是否满足要求，不负责 clone、切分支、stash、commit、pull 或修复官方 repo 状态。

如果用户没有准备好官方 repo、路径为空、路径不存在、不是 git 仓库，或不是 FastMCP 官方 repo，直接告诉用户先准备好官方 repo 的本地 clone 后再继续，并停止后续同步步骤。不要替用户准备该 repo。

拿到目录后执行检查：

```bash
git -C <OFFICIAL_REPO> rev-parse --is-inside-work-tree
git -C <OFFICIAL_REPO> branch --show-current
git -C <OFFICIAL_REPO> remote -v
git -C <OFFICIAL_REPO> fetch --dry-run origin main
git -C <OFFICIAL_REPO> status --short
git -C <OFFICIAL_REPO> rev-list --count HEAD..origin/main
```

检查要求：

- `rev-parse` 必须成功，路径必须是 git 仓库。
- 当前分支必须是 `main`。
- `remote -v` 应指向 FastMCP 官方仓库，例如 `jlowin/fastmcp`。
- `status --short` 必须为空，避免复制未提交的本地改动。
- `HEAD..origin/main` 必须为 `0`，表示本地 `main` 已包含远端最新变动。

如果任一条件不满足，只告知用户具体问题和需要用户自行处理的动作，例如“请先切到 main 并执行 git pull 更新官方 repo”。不要在官方 repo 中执行修复动作。只有在官方 repo 已经位于 `main`、工作区干净且最新时，继续后续操作。

同步前也检查当前仓库：

```bash
git status --short
```

不要回滚用户已有改动。若待删除或覆盖的目录中有不相关改动，先说明影响范围，再继续执行用户明确要求的同步步骤。

## 同步官方文档

1. 清空 `origin/` 后复制官方文档：

```bash
find origin -mindepth 1 -maxdepth 1 -exec rm -rf {} +
rsync -a <OFFICIAL_REPO>/docs/ origin/
```

2. 生成官方文档差异临时文件：

```bash
git diff -- origin > temp_origin_diff.txt
```

这个文件用于判断官方新增、删除、移动、修改了哪些文档、资源、CSS 和导航结构。

3. 提取 Markdown 文档内部跳转链接：

```bash
python3 skills/translator/scripts/extra_ref_link.py --root origin --output temp_ref_link.txt
```

`temp_ref_link.txt` 只记录 `.md/.mdx` 文档中 `[]()` 语法指向其他文档页的内部跳转，不记录外部 URL、图片、静态资源或代码块内容。它是后续修正 `i18n/en` 与 `i18n/zh` 文档跳转路径的依据。

## 更新 Mintlify 配置

分析 `origin/docs.json`，并同步更新：

- `i18n/docs_template.json`：保留多语言入口 `navigation.languages: []`，同步官方全局配置，如 `colors`、`navbar`、`footer`、`redirects`、`search`、`theme`、`logo`、`favicon` 等。
- `i18n/json_config/en.json`：根据官方 `navigation` 结构生成英文语言配置，所有页面路径加 `${LANGUAGE_CODE}/` 前缀。
- `i18n/json_config/zh.json`：保持与英文相同的页面结构，导航可读文本翻译为中文，页面路径同样使用 `${LANGUAGE_CODE}/` 前缀。

如果不确定 Mintlify `docs.json` 语法，查阅官方文档索引：

```bash
curl -L https://www.mintlify.com/docs/llms.txt | rg -n "docs.json|navigation|languages|dropdowns|tabs|anchors"
```

优先保持官方 `origin/docs.json` 的结构字段，不要凭空发明 Mintlify 不支持的字段。

## 同步资源和语言目录

先结合 `temp_origin_diff.txt` 判断 `origin/assets`、`origin/css`、根路径引用的共享图片目录或根级脚本是否变化：

```bash
rg -n "^diff --git a/origin/(assets|css|apps/images|integrations/images)/|^\+\+\+ b/origin/(assets|css|apps/images|integrations/images)/|^--- a/origin/(assets|css|apps/images|integrations/images)/" temp_origin_diff.txt
```

如果有变化，清空并重新复制到 `i18n/` 根目录作为全站共享资源：

```bash
find i18n/assets -mindepth 1 -maxdepth 1 -exec rm -rf {} +
find i18n/css -mindepth 1 -maxdepth 1 -exec rm -rf {} +
rsync -a origin/assets/ i18n/assets/
rsync -a origin/css/ i18n/css/
mkdir -p i18n/apps i18n/integrations
find i18n/apps/images -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
find i18n/integrations/images -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
rsync -a origin/apps/images/ i18n/apps/images/
rsync -a origin/integrations/images/ i18n/integrations/images/
```

如果源目录不存在，先确认是否为官方删除；不要为不存在的目录强行创建空目录，除非 Mintlify 验证需要。`/assets/...`、`/css/...`、`/apps/images/...`、`/integrations/images/...` 这类静态资源不会随语言改变，应保留站点根路径并放在 `i18n/` 根目录，不要复制到 `i18n/en` 或 `i18n/zh`。

然后重建英文目录：

```bash
find i18n/en -mindepth 1 -maxdepth 1 -exec rm -rf {} +
rsync -a origin/ i18n/en/
rm -rf i18n/en/assets i18n/en/css i18n/en/apps/images i18n/en/integrations/images i18n/en/docs.json i18n/en/python-sdk-pages.json i18n/en/v2-navigation.json i18n/en/.cursor i18n/en/.ccignore i18n/en/fastmcp-analytics.js i18n/en/prefab-demo-payloads.js i18n/en/unify-intent.js i18n/en/v2-banner.js
python3 skills/translator/scripts/extra_ref_link.py --root i18n/en --language-prefix en --output temp_ref_link.txt
python3 skills/translator/scripts/fix_mdx_import_paths.py --root i18n/en --language-prefix en
```

根据报告修正 `i18n/en` 内部文档跳转路径。常见改法：

- `/servers/tools` 这类站内绝对链接改为 `/en/servers/tools`。
- `/assets/...`、`/css/...`、`/apps/images/...`、`/integrations/images/...` 这类站点根资源保持不变，并由 `i18n/` 根目录共享资源提供。
- MDX import 中的 `/snippets/...` 改为当前语言路径，例如 `/en/snippets/...`；不要在 `i18n/` 根目录创建共享 `snippets`，因为不同语言目录里的 snippets 可能需要各自翻译。

再重建中文目录：

```bash
find i18n/zh -mindepth 1 -maxdepth 1 -exec rm -rf {} +
rsync -a origin/ i18n/zh/
rm -rf i18n/zh/assets i18n/zh/css i18n/zh/apps/images i18n/zh/integrations/images i18n/zh/docs.json i18n/zh/python-sdk-pages.json i18n/zh/v2-navigation.json i18n/zh/.cursor i18n/zh/.ccignore i18n/zh/fastmcp-analytics.js i18n/zh/prefab-demo-payloads.js i18n/zh/unify-intent.js i18n/zh/v2-banner.js
python3 skills/translator/scripts/extra_ref_link.py --root i18n/zh --language-prefix zh --output temp_ref_link.txt
python3 skills/translator/scripts/fix_mdx_import_paths.py --root i18n/zh --language-prefix zh
```

根据报告修正 `i18n/zh` 内部文档跳转路径。此时 `i18n/zh` 仍是英文内容，先只修文档跳转路径，不开始翻译。

## 验证文档

先构建多语言 `docs.json`：

```bash
(cd i18n && python3 build_docs_json.py)
```

再运行 Mintlify 官方 CLI 的非阻塞检查命令：

```bash
(cd i18n && mint broken-links)
(cd i18n && mint validate)
```

不要用 `mint dev` 作为同步或 CI 检查命令；它会启动长驻预览服务器并阻塞流程。`mint validate` 会严格检查构建，遇到警告或错误会返回非零退出码。若检查失败，优先检查 `docs.json` 结构、页面路径、被删除页面、资源路径和 MDX import。必要时查阅 Mintlify 官方 CLI 文档后修复，再重新运行上述非阻塞检查。

如果 `mint` 命令不存在，告诉用户需要安装 Mintlify CLI。

## 翻译流程

验证通过后，创建或更新根目录 `temp_translate_process_list.txt`。推荐格式：

```text
# status: pending | partial | done | review
# file | status | translated_ranges | owner | notes
i18n/zh/getting-started/welcome.mdx | pending | - | - | -
```

生成初始列表：

```bash
find i18n/zh -type f \( -name '*.md' -o -name '*.mdx' \) | sort | awk '{print $0 " | pending | - | - | -"}' > temp_translate_process_list.txt
```

翻译要求：

- 翻译所有对外阅读字符串，包括正文、标题、frontmatter 的 `title`、`sidebarTitle`、`description`、表格、提示框、代码注释、文档字符串和 SDK 文档说明。
- 保留代码标识符、导入路径、包名、类名、函数名、参数名、CLI 命令、环境变量、URL、协议字段、JSON key 和文件路径。
- FastMCP、MCP、OAuth、HTTP、SSE、STDIO、JSON Schema、OpenAPI、SDK 等专有名词按技术语境保留或采用通用译法。
- 常用译法：server 译为“服务端”，client 译为“客户端”，tool 译为“工具”，resource 译为“资源”，prompt 译为“提示词”，transport 译为“传输”，middleware 译为“中间件”，context 译为“上下文”，sampling 译为“采样”，elicitation 译为“用户征询”。
- 不要翻译 Mermaid、代码块中会影响执行的代码本体；只翻译其中对人可读的注释、字符串、docstring，且不要破坏语法。
- 每完成一个文件或一个行区间，立即更新 `temp_translate_process_list.txt`，大文件可记录 `partial` 和已翻译行号范围。
- 翻译的时候注意页面锚点问题，标题翻译成中文后锚点引用也要改成中文。

如果用户没有明确指定 subagent 数量，默认使用 3 个 subagent 并行翻译。主 agent 负责分配文件、检查术语一致性、合并结果、运行验证，并持续维护 `temp_translate_process_list.txt`。如果当前环境不能启动 subagent，则按同样的列表分批顺序翻译。

翻译完成后再次运行：

```bash
(cd i18n && python3 build_docs_json.py)
(cd i18n && mint broken-links)
(cd i18n && mint validate)
```

最后检查：

```bash
git diff --stat
git diff -- i18n/zh temp_translate_process_list.txt
```
