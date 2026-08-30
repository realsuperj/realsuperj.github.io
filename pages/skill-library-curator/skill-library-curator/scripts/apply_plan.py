#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按规划把条目移动到分类目录、规范化命名，并回验无丢失、写出账本。

用法：
    python3 apply_plan.py --target <目录> --plan <plan.json>          # dry-run
    python3 apply_plan.py --target <目录> --plan <plan.json> --apply  # 实际执行
    python3 apply_plan.py --target <目录> --plan <plan.json> --apply --backup <备份目录>

plan.json 结构：
{
  "weights": {...}, "model": "...", "taxonomy": [...],
  "report_filename": "Skill分析报告.md",
  "entries": [
    {"src": "原始文件名", "no": "01-01", "name": "中文名", "category": "01-职业发展",
     "type": "skill", "score": 98, "grade": "S", "summary": "一句话",
     "form": "解压包", "usable": "是", "dedup_key": "k1", "duplicate_of": null}
  ]
}

默认只打印计划不动文件。--apply 时才落盘，落盘后与备份逐一比对内容指纹。
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ARCHIVE_SUFFIXES = (".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz", ".skill")

# Windows 非法字符 -> 全角等价物。按最严规则清洗，保证三平台都能落地。
CHAR_MAP = {
    "<": "＜", ">": "＞", ":": "：", '"': "＂",
    "/": "／", "\\": "＼", "|": "｜", "?": "？", "*": "＊",
}
RESERVED = {"CON", "PRN", "AUX", "NUL"} | \
           {"COM%d" % i for i in range(1, 10)} | \
           {"LPT%d" % i for i in range(1, 10)}
MAX_NAME = 80          # 单个文件名上限，给路径留余量
MAX_PATH = 260         # Windows 默认路径总长上限


def sanitize(name):
    """按 Windows 最严规则清洗文件名，返回 (清洗后, 是否有改动)。"""
    original = name
    out = []
    for ch in name:
        if ch in CHAR_MAP:
            out.append(CHAR_MAP[ch])
        elif ord(ch) < 32:
            continue
        else:
            out.append(ch)
    s = "".join(out).strip().rstrip(".")
    s = re.sub(r"\s{2,}", " ", s)
    stem = s.rsplit(".", 1)[0] if "." in s else s
    if stem.upper() in RESERVED:
        s = "_" + s
    if len(s) > MAX_NAME:
        if "." in s[-8:]:
            stem, ext = s.rsplit(".", 1)
            s = stem[: MAX_NAME - len(ext) - 1] + "." + ext
        else:
            s = s[:MAX_NAME]
    if not s:
        s = "unnamed"
    return s, s != original


def file_digest(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_manifest(root):
    """目录下所有文件的 相对路径 -> 指纹，用于回验。"""
    m = {}
    if not root or not Path(root).is_dir():
        return m
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file() and p.name != ".DS_Store" and "__MACOSX" not in p.parts:
            try:
                m[p.relative_to(root).as_posix()] = file_digest(p)
            except OSError:
                pass
    return m


def target_basename(entry):
    """生成目标文件名：编号_名称[.扩展名]。"""
    src = entry["src"]
    no = entry["no"]
    name = entry.get("name") or Path(src).stem
    is_archive = Path(src).suffix.lower() in ARCHIVE_SUFFIXES
    src_path_is_dir = entry.get("_is_dir", False)

    if is_archive or src_path_is_dir:
        base = "%s_%s" % (no, name)          # 解压后是目录，不带扩展名
    else:
        ext = Path(src).suffix.lower()
        ext = {".markdown": ".md", ".text": ".txt", ".skill": ".md",
               ".dat": ".md", ".htm": ".html"}.get(ext, ext)
        base = "%s_%s%s" % (no, name, ext)
    return sanitize(base)


def plan_moves(target, plan):
    """产出移动计划，不执行。"""
    moves, problems = [], []
    seen_lower = {}

    for e in plan["entries"]:
        src = target / e["src"]
        e["_is_dir"] = src.is_dir()
        if not src.exists():
            problems.append("源不存在: %s" % e["src"])
            continue

        base, changed = target_basename(e)
        cat = e["category"]
        dest = target / cat / base

        rel_len = len(str(dest))
        if rel_len > MAX_PATH:
            problems.append("路径过长(%d): %s" % (rel_len, dest))

        key = str(dest).lower()          # 按小写比较，兼容大小写不敏感的文件系统
        if key in seen_lower:
            problems.append("目标重名: %s 与 %s" % (e["src"], seen_lower[key]))
        seen_lower[key] = e["src"]

        moves.append({
            "src": src, "dest": dest, "entry": e,
            "renamed": changed, "is_dir": e["_is_dir"],
            "is_archive": Path(e["src"]).suffix.lower() in ARCHIVE_SUFFIXES,
            # 增量场景下大部分条目原地不动，只是随账本一起重新登记
            "unchanged": src.resolve() == dest.resolve(),
        })
    return moves, problems


def do_move(m, unpacked_root):
    """执行单条移动。压缩包已在提取阶段解开的，取解压产物；否则直接搬。"""
    src, dest = m["src"], m["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)

    if m["is_archive"]:
        cand = None
        if unpacked_root:
            slug = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", src.name)[:80]
            p = Path(unpacked_root) / slug
            if p.is_dir():
                cand = p
                kids = [k for k in p.iterdir()
                        if not k.name.startswith(".") and k.name != "__MACOSX"]
                if len(kids) == 1 and kids[0].is_dir():
                    cand = kids[0]
        if cand:
            shutil.copytree(cand, dest, dirs_exist_ok=True)
            # 原始压缩包留在解压目录内，便于溯源和重装
            shutil.move(str(src), str(dest / ("_原始压缩包_" + src.name)))
            return "解压并归档"
        shutil.move(str(src), str(dest))
        return "移动（未解压）"

    shutil.move(str(src), str(dest))
    return "移动"


def main():
    ap = argparse.ArgumentParser(description="按规划落盘并回验")
    ap.add_argument("--target", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--apply", action="store_true", help="真正执行，默认只预演")
    ap.add_argument("--backup", default=None, help="备份目录，用于落盘后回验")
    ap.add_argument("--unpacked", default=None, help="extract_all.py 的 unpacked 目录")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    moves, problems = plan_moves(target, plan)

    print("=" * 72)
    print("目标目录: %s" % target)
    print("条目 %d，问题 %d" % (len(moves), len(problems)))
    print("=" * 72)

    changing = [m for m in moves if not m["unchanged"]]
    print("其中需要实际移动 %d 条，原地不动 %d 条"
          % (len(changing), len(moves) - len(changing)))

    by_cat = {}
    for m in changing:
        by_cat.setdefault(m["entry"]["category"], []).append(m)
    for cat in sorted(by_cat):
        print("\n## %s (%d)" % (cat, len(by_cat[cat])))
        for m in sorted(by_cat[cat], key=lambda x: x["entry"]["no"]):
            flag = " [名称已清洗]" if m["renamed"] else ""
            try:
                src_show = m["src"].relative_to(target).as_posix()
            except ValueError:
                src_show = m["src"].name
            print("  %s\n    <- %s%s" % (m["dest"].name, src_show, flag))

    if problems:
        print("\n!! 需要先解决的问题:")
        for p in problems:
            print("   - %s" % p)

    renamed = [m for m in changing if m["renamed"]]
    if renamed:
        print("\n## 文件名清洗对照（按 Windows 最严规则）")
        for m in renamed:
            print("  %s\n  -> %s" % (m["src"].name, m["dest"].name))

    if not args.apply:
        print("\n[dry-run] 未做任何改动。确认无误后加 --apply 执行。")
        return 1 if problems else 0

    if problems:
        print("\n存在未解决的问题，拒绝执行。")
        return 2

    if args.backup:
        if not Path(args.backup).is_dir():
            print("\n备份目录不存在，拒绝执行: %s" % args.backup)
            return 2
        before = dir_manifest(args.backup)
    else:
        print("\n未提供 --backup，跳过回验（不推荐）。")
        before = {}

    print("\n开始执行...")
    for m in changing:
        how = do_move(m, args.unpacked)
        print("  %s: %s" % (how, m["dest"].name))
    if not changing:
        print("  （无需移动，仅重写账本）")

    ledger = {
        "version": 1,
        "curated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "report_filename": plan.get("report_filename", "Skill分析报告.md"),
        "model": plan.get("model", ""),
        "weights": plan.get("weights", {}),
        "taxonomy": plan.get("taxonomy", []),
        "entries": [],
    }
    for m in moves:
        e = m["entry"]
        ledger["entries"].append({
            "no": e["no"],
            "name": e.get("name", ""),
            "path": m["dest"].relative_to(target).as_posix(),
            # 增量时 src 是条目在库内的现有位置，此时原始文件名要沿用账本里已记的那个
            "original_name": e.get("original_name") or e["src"],
            "hash": e.get("hash", ""),
            "type": e.get("type", "skill"),
            "score": e.get("score"),
            "grade": e.get("grade"),
            "category": e["category"],
            "summary": e.get("summary", ""),
            "form": e.get("form", ""),
            "usable": e.get("usable", ""),
            "dedup_key": e.get("dedup_key", ""),
            "duplicate_of": e.get("duplicate_of"),
            "user_override": e.get("user_override"),
        })
    lp = target / "Skill分析报告-数据.json"
    lp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n账本已写入: %s" % lp)

    if before:
        after = dir_manifest(target)
        after_hashes = set(after.values())
        missing = [rel for rel, h in before.items() if h not in after_hashes]
        print("\n回验：备份 %d 个文件，落盘后 %d 个，缺失 %d 个"
              % (len(before), len(after), len(missing)))
        if missing:
            print("!! 以下文件在落盘结果中找不到对应内容:")
            for rel in missing[:20]:
                print("   - %s" % rel)
            return 3
        print("回验通过，零丢失。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
