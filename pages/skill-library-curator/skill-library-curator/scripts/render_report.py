#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由账本确定性渲染《Skill分析报告》，并校验每行的目标路径真实存在。

用法：
    python3 render_report.py --target <目录>                    # 用默认账本名
    python3 render_report.py --target <目录> --ledger <path> --out <报告名>
    python3 render_report.py --target <目录> --no-frontmatter
    python3 render_report.py --target <目录> --changes "新增 2 条，更新 1 条"

报告是账本的纯投影。交给脚本渲染是为了保证多次运行的列序、排序、编号不漂移。
"""

import argparse
import json
import sys
from pathlib import Path

CAT_DESC = {
    "01-职业发展": "求职、简历、面试、晋升、职业战略、职场沟通、团队管理",
    "02-个人成长": "自我认知、习惯、情绪、沟通、任务管理",
    "03-创业与商业": "商业模式、增长、销售、副业、门店经营",
    "04-内容创作": "写作、短视频、账号运营、选题",
    "05-英语学习": "听说读写、考试、词汇、翻译",
    "06-健康养生": "饮食、运动、睡眠、身体调理",
    "07-家庭教育": "亲子沟通、学习陪伴、儿童发展",
    "08-行业专业": "特定行业的专业工具与流程",
    "09-AI与方法论": "提示词、AI 工具、通用方法论框架",
    "98-参考素材": "有价值但不是 skill 的知识库、样例与设计稿",
    "99-重复版本归档": "与主清单某条内容重复，仅留档",
}

MATERIAL_CAT = "98-参考素材"
DUP_CAT = "99-重复版本归档"

HOWTO = """## 怎么读这份清单

**评分**：满分 100，由五项加权而成 —— %s。

**等级**：S≥90 直接可用且体系完整 ｜ A 80-89 质量好，小改即用 ｜ B 70-79 框架可用，细节需补 ｜ C 55-69 有参考价值，需重写 ｜ D<55 仅存档。

**形态**：`解压包` 已解压的完整 skill 包（原压缩包以 `_原始压缩包_` 前缀保留在同目录）；`文件夹` 原本就是多文件目录；`单文件` 单个 md/pdf/docx。

**可用**：`是` 可直接安装使用；`部分` 需转格式或补依赖文件。
"""

TAIL = """## 怎么用这些 skill

想用哪个，把它的编号或名字告诉你的 AI，让它装到你当前所用客户端对应的位置。各家客户端的目录约定不一样，让 AI 按你的实际环境判断即可。

建议按需要装单个，不要一次全装 —— 每个装上的 skill 都会占用 AI 的上下文，装太多反而容易误触发。
"""

WEIGHT_HINT = {
    "完整度": "角色/流程/规则/输出规范是否齐全",
    "结构化": "是否符合 Agent Skill 规范，能否直接喂给 AI",
    "实用度": "问题是否高频、受众是否广",
    "原创性": "有无独到方法论",
    "交付物": "参考文档/脚本/模板/示例是否配套",
}


def weights_sentence(weights):
    if not weights:
        weights = {"完整度": 30, "结构化": 25, "实用度": 25, "原创性": 10, "交付物": 10}
    parts = []
    for k, v in weights.items():
        hint = WEIGHT_HINT.get(k)
        parts.append("%s %d%%（%s）" % (k, v, hint) if hint else "%s %d%%" % (k, v))
    return "、".join(parts)


def anchor(title):
    """Obsidian / GitHub 风格的中文标题锚点。"""
    return "#" + title.replace(" ", "-")


def esc(text):
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def render(ledger, changes=None, frontmatter=True):
    entries = ledger.get("entries", [])
    skills = [e for e in entries
              if e.get("type") == "skill" and e.get("category") not in (MATERIAL_CAT, DUP_CAT)]
    materials = [e for e in entries if e.get("category") == MATERIAL_CAT]
    dups = [e for e in entries if e.get("category") == DUP_CAT]

    cats = {}
    for e in skills:
        cats.setdefault(e["category"], []).append(e)

    lines = []
    if frontmatter:
        lines += ["---", "tags:", "  - AI/skills/收集清单", "---", ""]

    lines.append("# Skill 收集清单（已分类评分）")
    lines.append("")
    lines.append("共收录 **%d** 个条目：主清单 **%d** 个可用 skill，参考素材 **%d** 个，重复版本归档 **%d** 个。"
                 % (len(entries), len(skills), len(materials), len(dups)))
    if changes:
        lines.append("")
        lines.append("本次变更：%s。" % changes)
    if ledger.get("curated_at"):
        lines.append("")
        lines.append("上次整理于 %s。" % ledger["curated_at"][:19].replace("T", " "))
    lines.append("")

    lines.append(HOWTO % weights_sentence(ledger.get("weights")))
    lines.append("---")
    lines.append("")
    lines.append("## 目录")
    lines.append("")
    for cat in sorted(cats):
        lines.append("- [%s](%s)（%d）—— %s"
                     % (cat, anchor(cat), len(cats[cat]), CAT_DESC.get(cat, "")))
    if materials:
        lines.append("- [%s](%s)（%d）—— %s"
                     % (MATERIAL_CAT, anchor(MATERIAL_CAT), len(materials), CAT_DESC[MATERIAL_CAT]))
    if dups:
        lines.append("- [%s](%s)（%d）—— %s"
                     % (DUP_CAT, anchor(DUP_CAT), len(dups), CAT_DESC[DUP_CAT]))
    lines.append("")
    lines.append("---")
    lines.append("")

    for cat in sorted(cats):
        lines.append("## %s" % cat)
        lines.append("")
        if CAT_DESC.get(cat):
            lines.append("> %s" % CAT_DESC[cat])
            lines.append("")
        lines.append("| 编号 | 名称 | 分 | 级 | 说明 | 形态 | 可用 | 原始文件名 |")
        lines.append("| --- | --- | --: | :-: | --- | :-: | :-: | --- |")
        # 展示按分数降序，编号只作 ID 列
        for e in sorted(cats[cat], key=lambda x: (-(x.get("score") or 0), x["no"])):
            lines.append("| %s | **%s** | %s | %s | %s | %s | %s | `%s` |" % (
                e["no"], esc(e.get("name") or Path(e["path"]).name),
                e.get("score", ""), e.get("grade", ""), esc(e.get("summary")),
                e.get("form", ""), e.get("usable", ""), esc(e.get("original_name"))))
        lines.append("")

    if materials:
        lines.append("## %s" % MATERIAL_CAT)
        lines.append("")
        lines.append("> %s。这些不是 skill，因此不打分、不参与排序。" % CAT_DESC[MATERIAL_CAT])
        lines.append("")
        lines.append("| 编号 | 名称 | 说明 | 原始文件名 |")
        lines.append("| --- | --- | --- | --- |")
        for e in sorted(materials, key=lambda x: x["no"]):
            lines.append("| %s | **%s** | %s | `%s` |" % (
                e["no"], esc(e.get("name") or Path(e["path"]).name),
                esc(e.get("summary")), esc(e.get("original_name"))))
        lines.append("")

    if dups:
        lines.append("## %s" % DUP_CAT)
        lines.append("")
        lines.append("> %s" % CAT_DESC[DUP_CAT])
        lines.append("")
        lines.append("| 编号 | 名称 | 与哪条重复 | 原始文件名 |")
        lines.append("| --- | --- | --- | --- |")
        for e in sorted(dups, key=lambda x: x["no"]):
            lines.append("| %s | **%s** | %s | `%s` |" % (
                e["no"], esc(e.get("name") or Path(e["path"]).name),
                e.get("duplicate_of") or "—", esc(e.get("original_name"))))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(TAIL)
    return "\n".join(lines)


def verify(target, ledger):
    """报告生成后的硬校验：路径真实存在、编号唯一。"""
    missing, seen, dup_no = [], set(), []
    for e in ledger.get("entries", []):
        p = target / e["path"]
        if not p.exists():
            missing.append("%s -> %s" % (e["no"], e["path"]))
        if e["no"] in seen:
            dup_no.append(e["no"])
        seen.add(e["no"])
    return missing, dup_no


def next_number(ledger, category):
    """增量时为新条目分配编号：该分类现有最大号加一，已有编号一律不动。"""
    prefix = category.split("-")[0]
    used = [int(e["no"].split("-")[1]) for e in ledger.get("entries", [])
            if e.get("category") == category and "-" in e.get("no", "")
            and e["no"].split("-")[1].isdigit()]
    return "%s-%02d" % (prefix, (max(used) + 1) if used else 1)


def main():
    ap = argparse.ArgumentParser(description="由账本渲染分析报告")
    ap.add_argument("--target", required=True)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--out", default=None, help="报告文件名，默认取账本记录的名字")
    ap.add_argument("--changes", default=None, help="本次变更摘要，增量时填")
    ap.add_argument("--no-frontmatter", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印不写文件")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    lp = Path(args.ledger) if args.ledger else target / "Skill分析报告-数据.json"
    if not lp.is_file():
        print("账本不存在: %s" % lp, file=sys.stderr)
        return 2
    ledger = json.loads(lp.read_text(encoding="utf-8"))

    out_name = args.out or ledger.get("report_filename") or "Skill分析报告.md"
    text = render(ledger, changes=args.changes, frontmatter=not args.no_frontmatter)

    missing, dup_no = verify(target, ledger)
    if missing:
        print("!! 以下条目的目标路径在磁盘上不存在：", file=sys.stderr)
        for m in missing[:20]:
            print("   - %s" % m, file=sys.stderr)
    if dup_no:
        print("!! 编号重复: %s" % ", ".join(sorted(set(dup_no))), file=sys.stderr)
    if missing or dup_no:
        print("校验未通过，报告未写入。", file=sys.stderr)
        return 3

    if args.dry_run:
        print(text)
        return 0

    out = target / out_name
    if out.exists():
        shutil_backup = target / "Skill分析报告-上一版.md"
        shutil_backup.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        print("旧报告已备份为 %s" % shutil_backup.name)
    out.write_text(text, encoding="utf-8")

    if ledger.get("report_filename") != out_name:
        ledger["report_filename"] = out_name
        lp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    print("报告已写入: %s（%d 个条目，校验通过）" % (out, len(ledger.get("entries", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
