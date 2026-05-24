#!/usr/bin/env python3
"""Fix root-level MDX imports inside i18n language directories."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DOC_EXTENSIONS = {".md", ".mdx"}
SKIP_DIRS = {".git", ".mintlify", ".next", "node_modules", "dist", "build", "__pycache__"}
IMPORT_PATH_RE = re.compile(r"(?P<quote>['\"])/(?P<path>snippets/[^'\"]+)(?P=quote)")


def iter_doc_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DOC_EXTENSIONS:
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        yield path


def fix_text(text: str, language_prefix: str) -> tuple[str, int]:
    prefix = language_prefix.strip("/")

    def replace(match: re.Match[str]) -> str:
        quote = match.group("quote")
        import_path = match.group("path")
        if import_path.startswith(f"{prefix}/"):
            return match.group(0)
        return f"{quote}/{prefix}/{import_path}{quote}"

    return IMPORT_PATH_RE.subn(replace, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Language docs root, e.g. i18n/zh")
    parser.add_argument("--language-prefix", required=True, help="Language prefix, e.g. zh")
    parser.add_argument("--check", action="store_true", help="Report files that need changes without writing")
    args = parser.parse_args()

    changed_files = []
    changed_imports = 0
    for path in iter_doc_files(args.root):
        text = path.read_text(encoding="utf-8")
        fixed, count = fix_text(text, args.language_prefix)
        if count == 0 or fixed == text:
            continue
        changed_files.append(path)
        changed_imports += count
        if not args.check:
            path.write_text(fixed, encoding="utf-8")

    action = "Need changes in" if args.check else "Changed"
    print(f"{action} {len(changed_files)} files, {changed_imports} MDX imports")
    for path in changed_files:
        print(path)

    return 1 if args.check and changed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
