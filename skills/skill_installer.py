#!/usr/bin/env python3
"""
将 skills/ 目录下的 AI 技能安装到目标 AI 工具目录。

支持的目标：
  - codex: OpenAI Codex CLI  -> .codex/skills/<技能名>/
  - claude: Claude Code      -> .claude/skills/<技能名>/
  - opencode: OpenCode CLI   -> .opencode/skills/<技能名>/

用法：
  python install_skill.py                   # 显示帮助信息
  python install_skill.py --all             # 安装所有技能到所有目标
  python install_skill.py -t codex          # 仅安装到 codex
  python install_skill.py -t claude         # 仅安装到 claude
  python install_skill.py -t opencode       # 仅安装到 opencode
  python install_skill.py -t codex claude   # 显式指定安装到多个目标
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SKILLS_DIR.parent

CODEX_DIR = PROJECT_ROOT / ".codex" / "skills"
CLAUDE_DIR = PROJECT_ROOT / ".claude" / "skills"
OPENCODE_DIR = PROJECT_ROOT / ".opencode" / "skills"


def discover_skills() -> list[Path]:
    """返回包含 SKILL.md 的技能目录列表（按名称排序）。"""
    return sorted(
        p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    )


def resolve_install_base(target_name: str, candidates: list[Path]) -> Path:
    """
    解析可用安装目录。
    - 按顺序尝试 candidates，选择第一个可创建目录的路径；
    - 如果父路径是同名文件（例如 .codex 是文件），自动跳过；
    - 全部失败时抛出清晰错误。
    """
    errors: list[str] = []
    for base_dir in candidates:
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
            return base_dir
        except NotADirectoryError as exc:
            errors.append(f"{base_dir} (路径冲突: {exc})")
        except OSError as exc:
            errors.append(f"{base_dir} ({exc})")
    msg = "\n".join(f"  - {e}" for e in errors)
    raise RuntimeError(f"{target_name} 安装目录不可用，已尝试：\n{msg}")


def install_to_dir(skill: Path, base_dir: Path, target_name: str) -> None:
    """将技能目录完整复制到指定目标目录。"""
    target = base_dir / skill.name
    # 清除该技能的旧安装以保持同步
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(skill, target)
    print(f"  {target_name:<8} -> {target}")


def install_to_codex(skill: Path) -> None:
    """
    将技能目录复制到 codex skills 目录。
    优先项目内 .codex/skills，若冲突则回退到 CODEX_HOME/skills 或 ~/.codex/skills。
    """
    codex_home = os.environ.get("CODEX_HOME")
    fallback = Path(codex_home) if codex_home else (Path.home() / ".codex")
    base_dir = resolve_install_base("codex", [CODEX_DIR, fallback / "skills"])
    install_to_dir(skill, base_dir, "codex")


def install_to_claude(skill: Path) -> None:
    """将技能目录完整复制到 .claude/skills/。"""
    install_to_dir(skill, CLAUDE_DIR, "claude")


def install_to_opencode(skill: Path) -> None:
    """将技能目录完整复制到 .opencode/skills/。"""
    install_to_dir(skill, OPENCODE_DIR, "opencode")


INSTALLERS = {
    "codex": install_to_codex,
    "claude": install_to_claude,
    "opencode": install_to_opencode,
}

VALID_TARGETS = list(INSTALLERS.keys())


def install(skills: list[Path], targets: list[str]) -> None:
    """执行技能安装。"""
    for skill in skills:
        print(f"\n[{skill.name}]")
        for target in targets:
            INSTALLERS[target](skill)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 AI 技能安装到 codex、claude 和/或 opencode 工具目录。",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="install_all",
        help="安装所有技能到所有目标",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        choices=VALID_TARGETS,
        default=None,
        help=f"指定安装目标工具（可选：{' '.join(VALID_TARGETS)}）",
    )
    args = parser.parse_args()

    # 未指定 --all 或 --target 时，显示帮助信息
    if not args.install_all and args.target is None:
        parser.print_help()
        sys.exit(0)

    skills = discover_skills()
    if not skills:
        print(f"在 {SKILLS_DIR} 中未找到任何技能")
        sys.exit(1)

    # --all 安装所有目标；否则使用 -t 指定的目标
    targets = VALID_TARGETS if args.install_all else args.target

    print(f"正在安装 {len(skills)} 个技能到：{', '.join(targets)}")
    install(skills, targets)
    print(f"\n完成。已安装 {len(skills)} 个技能。")


if __name__ == "__main__":
    main()
