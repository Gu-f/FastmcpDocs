#!/usr/bin/env python3
"""Fix Chinese docs anchor links after heading translation.

The translated zh pages keep links such as ``#route-mapping`` while the target
headings now generate Chinese anchors. This script compares each zh page with
its en counterpart, builds an English-heading-slug to Chinese-heading-slug map,
and rewrites internal anchor links in ``i18n/zh``.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


DOC_EXTENSIONS = (".md", ".mdx")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]*(?:\][^\[]*)*\]\(([^)\s]+(?:\s+['\"][^'\"]*['\"])?[^)]*)\)")
HREF_RE = re.compile(r"href=(['\"])([^'\"]*#[^'\"]+)\1")


# A small set of historical English anchors that no longer line up with the
# current English page structure but do have clear translated targets.
KNOWN_ANCHOR_FALLBACKS = {
    "caching-middleware": "缓存中间件",
    "conflict-resolution": "冲突解决",
    "custom-serialization": "使用-toolresult-完全控制",
    "disabling-prompts": "禁用提示",
    "disabling-resources": "禁用资源",
    "disabling-tools": "禁用工具",
    "excluding-arguments": "排除参数",
    "importing-static-composition": "导入静态组合",
    "importing-without-prefixes": "无前缀导入",
    "input-validation-modes": "验证模式",
    "key-and-storage-management": "密钥和存储管理",
    "oauth-token-security": "oauth-令牌安全性",
    "proxy-servers": "远程服务器",
    "state-management": "状态管理",
    "supported-response-types": "响应类型",
    "tool-transformation-with-fastmcp-and-mcpconfig": "工具转换",
}
DROP_ANCHOR_FALLBACKS = {
    "factory-functions",
    "tags",
}


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    slug: str


def strip_inline_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slug_base(title: str) -> str:
    title = strip_inline_markup(title).lower()
    chars: list[str] = []
    previous_dash = False

    for char in title:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif char.isspace() or char == "-":
            if chars and not previous_dash:
                chars.append("-")
                previous_dash = True
        # Other punctuation is dropped, matching common docs slug behavior.

    return "".join(chars).strip("-")


def unique_slug(title: str, seen: dict[str, int]) -> str:
    base = slug_base(title)
    if not base:
        base = "section"
    count = seen.get(base, 0)
    seen[base] = count + 1
    if count == 0:
        return base
    return f"{base}-{count}"


def iter_lines_with_code_state(text: str):
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            yield line, in_fence
            continue
        yield line, in_fence


def extract_headings(path: Path) -> list[Heading]:
    seen: dict[str, int] = {}
    headings: list[Heading] = []
    text = path.read_text(encoding="utf-8")
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append(Heading(level=level, title=title, slug=unique_slug(title, seen)))
    return headings


def pair_heading_slugs(en_headings: list[Heading], zh_headings: list[Heading]) -> dict[str, str]:
    mapping: dict[str, str] = {}

    # Best case: the translated page preserved heading count and order.
    if len(en_headings) == len(zh_headings):
        for en_heading, zh_heading in zip(en_headings, zh_headings):
            mapping[en_heading.slug] = zh_heading.slug
        return mapping

    # Fallback: pair by heading level sequence. This handles pages where a few
    # sections were added or removed but the nearby structure is still aligned.
    zh_by_level: dict[int, list[Heading]] = {}
    for heading in zh_headings:
        zh_by_level.setdefault(heading.level, []).append(heading)

    positions = {level: 0 for level in zh_by_level}
    for en_heading in en_headings:
        candidates = zh_by_level.get(en_heading.level, [])
        position = positions.get(en_heading.level, 0)
        if position < len(candidates):
            mapping[en_heading.slug] = candidates[position].slug
            positions[en_heading.level] = position + 1

    return mapping


def build_page_index(root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.suffix not in DOC_EXTENSIONS:
            continue
        rel = path.relative_to(root).with_suffix("").as_posix()
        index[rel] = path
        index[f"/zh/{rel}"] = path
        index[f"/{rel}"] = path
    return index


def resolve_target(link_path: str, source: Path, zh_root: Path, page_index: dict[str, Path]) -> Path | None:
    if not link_path:
        return source

    if link_path.startswith("/zh/"):
        return page_index.get(link_path)
    if link_path.startswith("/"):
        return page_index.get(link_path) or page_index.get("/zh" + link_path)

    rel = (source.parent / link_path).resolve()
    try:
        rel_key = rel.relative_to(zh_root.resolve()).with_suffix("").as_posix()
    except ValueError:
        return None
    return page_index.get(rel_key)


def split_link_target(target: str) -> tuple[str, str | None, str]:
    suffix = ""
    quote_match = re.search(r"\s+(['\"]).*\1$", target)
    if quote_match:
        suffix = target[quote_match.start() :]
        target = target[: quote_match.start()]

    if "#" not in target:
        return target, None, suffix
    path_part, anchor = target.split("#", 1)
    if "?" in anchor:
        anchor, query = anchor.split("?", 1)
        suffix = "?" + query + suffix
    return path_part, anchor, suffix


def build_anchor_maps(en_root: Path, zh_root: Path) -> tuple[dict[Path, dict[str, str]], dict[Path, set[str]]]:
    anchor_maps: dict[Path, dict[str, str]] = {}
    zh_anchor_sets: dict[Path, set[str]] = {}

    for zh_path in zh_root.rglob("*"):
        if zh_path.suffix not in DOC_EXTENSIONS:
            continue
        rel = zh_path.relative_to(zh_root)
        en_path = en_root / rel
        zh_headings = extract_headings(zh_path)
        zh_anchor_sets[zh_path] = {heading.slug for heading in zh_headings}
        if not en_path.exists():
            continue
        anchor_maps[zh_path] = pair_heading_slugs(extract_headings(en_path), zh_headings)

    return anchor_maps, zh_anchor_sets


def rewrite_line(
    line: str,
    source: Path,
    zh_root: Path,
    page_index: dict[str, Path],
    anchor_maps: dict[Path, dict[str, str]],
    zh_anchor_sets: dict[Path, set[str]],
    unresolved: list[str],
) -> tuple[str, int]:
    changes = 0

    def replacement_for(path_part: str, anchor: str | None, suffix: str, original: str) -> str:
        nonlocal changes
        if not anchor:
            return original
        decoded_anchor = unquote(anchor)
        target_path = resolve_target(path_part, source, zh_root, page_index)
        if target_path is None:
            return original
        if decoded_anchor in zh_anchor_sets.get(target_path, set()):
            return original

        new_anchor = anchor_maps.get(target_path, {}).get(decoded_anchor)
        fallback_anchor = KNOWN_ANCHOR_FALLBACKS.get(decoded_anchor)
        if not new_anchor and fallback_anchor in zh_anchor_sets.get(target_path, set()):
            new_anchor = fallback_anchor
        if not new_anchor and decoded_anchor in DROP_ANCHOR_FALLBACKS:
            changes += 1
            return f"{path_part}{suffix}"
        if not new_anchor:
            rel = source.relative_to(zh_root).as_posix()
            target_rel = target_path.relative_to(zh_root).as_posix()
            unresolved.append(f"{rel}: #{decoded_anchor} -> {target_rel}")
            return original

        changes += 1
        return f"{path_part}#{new_anchor}{suffix}"

    def replace_md(match: re.Match[str]) -> str:
        target = match.group(1)
        path_part, anchor, suffix = split_link_target(target)
        new_target = replacement_for(path_part, anchor, suffix, target)
        return match.group(0).replace(target, new_target, 1)

    def replace_href(match: re.Match[str]) -> str:
        quote = match.group(1)
        target = match.group(2)
        path_part, anchor, suffix = split_link_target(target)
        new_target = replacement_for(path_part, anchor, suffix, target)
        return f"href={quote}{new_target}{quote}"

    line = MD_LINK_RE.sub(replace_md, line)
    line = HREF_RE.sub(replace_href, line)
    return line, changes


def fix_file(
    path: Path,
    zh_root: Path,
    page_index: dict[str, Path],
    anchor_maps: dict[Path, dict[str, str]],
    zh_anchor_sets: dict[Path, set[str]],
    dry_run: bool,
    unresolved: list[str],
) -> int:
    text = path.read_text(encoding="utf-8")
    new_lines: list[str] = []
    changes = 0
    in_fence = False

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            new_lines.append(line)
            continue
        if in_fence:
            new_lines.append(line)
            continue

        new_line, line_changes = rewrite_line(
            line,
            path,
            zh_root,
            page_index,
            anchor_maps,
            zh_anchor_sets,
            unresolved,
        )
        changes += line_changes
        new_lines.append(new_line)

    if changes and not dry_run:
        path.write_text("".join(new_lines), encoding="utf-8")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zh-root", default="i18n/zh", type=Path)
    parser.add_argument("--en-root", default="i18n/en", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    zh_root = args.zh_root.resolve()
    en_root = args.en_root.resolve()
    if not zh_root.exists() or not en_root.exists():
        print("Both --zh-root and --en-root must exist.", file=sys.stderr)
        return 2

    page_index = build_page_index(zh_root)
    anchor_maps, zh_anchor_sets = build_anchor_maps(en_root, zh_root)

    changed_files = 0
    changed_links = 0
    unresolved: list[str] = []
    for path in sorted(zh_root.rglob("*")):
        if path.suffix not in DOC_EXTENSIONS:
            continue
        changes = fix_file(
            path,
            zh_root,
            page_index,
            anchor_maps,
            zh_anchor_sets,
            args.dry_run,
            unresolved,
        )
        if changes:
            changed_files += 1
            changed_links += changes
            print(f"fixed {changes:3d} anchor(s): {path.relative_to(zh_root)}")

    print(f"\nChanged files: {changed_files}")
    print(f"Changed anchors: {changed_links}")

    unique_unresolved = sorted(set(unresolved))
    if unique_unresolved:
        print(f"Unresolved anchors: {len(unique_unresolved)}")
        for item in unique_unresolved[:100]:
            print(f"  {item}")
        if len(unique_unresolved) > 100:
            print(f"  ... {len(unique_unresolved) - 100} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
