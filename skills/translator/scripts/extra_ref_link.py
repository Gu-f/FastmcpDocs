#!/usr/bin/env python3
"""Extract internal Markdown doc links that may need i18n path fixes."""

from __future__ import annotations

import argparse
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


DOC_EXTENSIONS = {".md", ".mdx"}
STATIC_EXTENSIONS = {
    ".avif",
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".yaml",
    ".yml",
    ".zip",
}
SKIP_DIRS = {".git", ".mintlify", ".next", "node_modules", "dist", "build", "__pycache__"}
LANGUAGE_SEGMENT_RE = re.compile(r"^/[a-z]{2}(?:-[a-z0-9]+)?(?=/|$)", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[([^\]\n]+?)\]\(\s*([^\s)]+)(?:\s+['\"][^)]*['\"])?\s*\)"
)


@dataclass(frozen=True)
class DocLink:
    file: Path
    line: int
    text: str
    target: str
    resolved: str
    suggestion: str
    context: str

    @property
    def status(self) -> str:
        return "needs-language-prefix" if self.suggestion else "ok"


def iter_doc_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        if path.suffix.lower() in DOC_EXTENSIONS:
            yield path


def mask_fenced_code(text: str) -> str:
    def replace_same_length(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    masked = re.sub(r"```.*?```", replace_same_length, text, flags=re.DOTALL)
    masked = re.sub(r"~~~.*?~~~", replace_same_length, masked, flags=re.DOTALL)
    return masked


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def line_context(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return " ".join(text[start:end].strip().split())


def clean_link_text(text: str) -> str:
    cleaned = text.replace("`", "").replace("*", "")
    return " ".join(cleaned.split())


def is_external(target: str) -> bool:
    lowered = target.lower()
    return bool(re.match(r"^[a-z][a-z0-9+.-]*:", lowered) or lowered.startswith("//"))


def split_suffix(target: str) -> tuple[str, str]:
    indexes = [index for index in (target.find("?"), target.find("#")) if index != -1]
    if not indexes:
        return target, ""
    split_at = min(indexes)
    return target[:split_at], target[split_at:]


def has_static_extension(path_part: str) -> bool:
    suffix = PurePosixPath(path_part).suffix.lower()
    return suffix in STATIC_EXTENSIONS and suffix not in DOC_EXTENSIONS


def is_internal_doc_target(target: str) -> bool:
    if not target or target.startswith("#") or is_external(target):
        return False

    path_part, _ = split_suffix(target)
    if not path_part:
        return False
    if path_part.startswith(("/assets/", "/css/", "/images/")):
        return False
    if has_static_extension(path_part):
        return False

    suffix = PurePosixPath(path_part).suffix.lower()
    if suffix in DOC_EXTENSIONS:
        return True
    if target.startswith(("/", "./", "../")):
        return True
    return suffix == ""


def strip_doc_extension(route: str) -> str:
    suffix = PurePosixPath(route).suffix.lower()
    if suffix in DOC_EXTENSIONS:
        return route[: -len(suffix)]
    return route


def resolve_route(source_rel: Path, target: str) -> str:
    path_part, suffix = split_suffix(target)
    source_dir = source_rel.parent.as_posix()

    if path_part.startswith("/"):
        route = posixpath.normpath(path_part)
    else:
        route = posixpath.normpath(posixpath.join("/", source_dir, path_part))

    if route == ".":
        route = "/"
    if not route.startswith("/"):
        route = f"/{route}"
    return strip_doc_extension(route) + suffix


def suggest_route(resolved: str, language_prefix: str | None) -> str:
    if not language_prefix:
        return ""

    path_part, suffix = split_suffix(resolved)
    wanted_prefix = f"/{language_prefix}"
    if path_part == wanted_prefix or path_part.startswith(f"{wanted_prefix}/"):
        return ""

    without_existing_lang = LANGUAGE_SEGMENT_RE.sub("", path_part, count=1) or "/"
    if without_existing_lang == "/":
        return wanted_prefix + suffix
    return f"{wanted_prefix}{without_existing_lang}{suffix}"


def extract_links(root: Path, language_prefix: str | None) -> list[DocLink]:
    links: list[DocLink] = []
    for path in iter_doc_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        scan_text = mask_fenced_code(text)
        source_rel = path.relative_to(root)

        for match in MARKDOWN_LINK_RE.finditer(scan_text):
            link_text = clean_link_text(match.group(1))
            target = match.group(2).strip()
            if not is_internal_doc_target(target):
                continue

            resolved = resolve_route(source_rel, target)
            links.append(
                DocLink(
                    file=path,
                    line=line_number(text, match.start(2)),
                    text=link_text,
                    target=target,
                    resolved=resolved,
                    suggestion=suggest_route(resolved, language_prefix),
                    context=line_context(text, match.start(0)),
                )
            )
    return links


def escape_cell(value: str) -> str:
    escaped = value.replace("|", "\\|").replace("\n", " ").strip()
    return escaped or "-"


def render_report(root: Path, links: list[DocLink], language_prefix: str | None) -> str:
    needs_fix = sum(1 for link in links if link.suggestion)
    lines = [
        "# Internal Markdown Doc Links",
        f"root: {root}",
        f"language_prefix: {language_prefix or '-'}",
        f"total: {len(links)}",
        f"needs_language_prefix: {needs_fix}",
        "",
        "status | file:line | text | target | resolved | suggestion | context",
        "--- | --- | --- | --- | --- | --- | ---",
    ]

    for link in links:
        rel_file = link.file.relative_to(root)
        suggestion = link.suggestion or "-"
        lines.append(
            " | ".join(
                [
                    link.status,
                    f"{rel_file}:{link.line}",
                    escape_cell(link.text),
                    f"`{escape_cell(link.target)}`",
                    f"`{escape_cell(link.resolved)}`",
                    f"`{escape_cell(suggestion)}`",
                    escape_cell(link.context),
                ]
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- 仅扫描 `.md` 和 `.mdx` 文件中的 Markdown `[]()` 链接。",
            "- 已忽略图片 `![]()`、外部 URL、锚点-only 链接、静态资源和代码块。",
            "- `resolved` 是按当前文件位置解析后的文档路由；`suggestion` 是加入或替换语言前缀后的建议路由。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract internal Markdown doc links for i18n path review.")
    parser.add_argument("--root", default=".", help="Directory containing .md/.mdx docs to scan.")
    parser.add_argument("--output", default="temp_ref_link.txt", help="Report output path.")
    parser.add_argument("--language-prefix", help="Language prefix such as en or zh for suggested routes.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found: {root}")

    links = extract_links(root, args.language_prefix)
    report = render_report(root, links, args.language_prefix)
    output = Path(args.output)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {len(links)} internal Markdown doc links to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
