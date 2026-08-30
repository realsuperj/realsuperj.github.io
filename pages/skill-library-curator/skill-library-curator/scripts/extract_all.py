#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量解压与文本提取，为 skill 收藏目录的每个顶层条目产出一份文本 dump。

用法：
    python3 extract_all.py --target <待整理目录> [--workdir <中间产物目录>]
                           [--ledger <账本路径>] [--budget 8000]

设计要点：
- 判型一律先读 magic bytes，扩展名只作参考。伪扩展名（.SKILL/.dat 实为文本）很常见。
- zip/tar 走标准库；rar/7z 等交给 bsdtar(libarchive)。bsdtar 对 rar 只能整包解压，
  按成员路径提取到 stdout 会挂住十几秒后报错，所以一律整包解。
- 第三方库（PyMuPDF/python-docx/python-pptx）全部可选，缺失时记入失败清单而不是崩溃。
- 提取"成功"但内容近乎为空的条目在脚本层面看不出来，所以额外产出可疑清单。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

SUSPICIOUS_CHARS = 500          # dump 小于此字符数视为可疑
SUSPICIOUS_TOTAL_BYTES = 1024   # 无 SKILL.md 且总提取量小于此值视为可疑
SNIFF_BYTES = 4096

# 已整理的分类目录，整体跳过
CATEGORY_DIR_RE = re.compile(r"^(0[1-9]|9[89])[-_]")
# 收纳夹词表，仅用于提示，不在脚本内自动拆分
INBOX_WORDS = ("待整理", "新增", "未分类", "待处理", "inbox", "new", "temp")

TEXT_EXTS = {".md", ".markdown", ".txt", ".text", ".skill", ".dat", ".json",
             ".yaml", ".yml", ".csv", ".rst", ".org"}
HTML_EXTS = {".html", ".htm"}

MAGIC = [
    (b"Rar!\x1a\x07\x01\x00", "rar5"),
    (b"Rar!\x1a\x07\x00", "rar4"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"\x1f\x8b", "gzip"),
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ", "xz"),
    (b"%PDF", "pdf"),
    (b"PK\x03\x04", "zipfamily"),
    (b"PK\x05\x06", "zipfamily"),
    (b"PK\x07\x08", "zipfamily"),
    (b"\xd0\xcf\x11\xe0", "ole"),  # 老式 doc/ppt/xls
]

ARCHIVE_KINDS = {"rar4", "rar5", "7z", "gzip", "bzip2", "xz", "zip", "tar"}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def has_cmd(name):
    return shutil.which(name) is not None


def try_import(name):
    try:
        return __import__(name)
    except Exception:
        return None


# --------------------------------------------------------------------------
# 判型
# --------------------------------------------------------------------------

def sniff(path):
    """读文件头判断真实类型，返回类型字符串。扩展名只在无法区分时作参考。"""
    try:
        with open(path, "rb") as f:
            head = f.read(SNIFF_BYTES)
    except OSError:
        return "unreadable"
    if not head:
        return "empty"

    for sig, kind in MAGIC:
        if head.startswith(sig):
            if kind == "zipfamily":
                return _zip_subtype(path)
            if kind == "gzip":
                return "tar" if tarfile.is_tarfile(str(path)) else "gzip"
            return kind

    if tarfile.is_tarfile(str(path)):   # 未压缩 tar 的 magic 在偏移 257
        return "tar"
    if _looks_text(head):
        return "text"
    return "binary"


def _zip_subtype(path):
    """PK 开头的可能是 zip 包，也可能是 docx/pptx/xlsx。"""
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
    except Exception:
        return "zip"
    if any(n.startswith("word/") for n in names):
        return "docx"
    if any(n.startswith("ppt/") for n in names):
        return "pptx"
    if any(n.startswith("xl/") for n in names):
        return "xlsx"
    return "zip"


def _looks_text(head):
    if b"\x00" in head:
        return False
    for enc in ("utf-8", "gb18030"):
        try:
            head.decode(enc)
            return True
        except UnicodeDecodeError:
            continue
    # 截断多字节字符导致的解码失败不算二进制
    try:
        head[:-4].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


# --------------------------------------------------------------------------
# 解压
# --------------------------------------------------------------------------

def fix_zip_name(raw):
    """zip 里的中文名常以 cp437 存储，需还原后按 gbk/utf-8 重新解码。"""
    try:
        b = raw.encode("cp437")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return raw
    for enc in ("utf-8", "gb18030"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw


def extract_archive(src, dest, kind):
    """把压缩包解到 dest。返回 (是否成功, 说明)。"""
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if kind == "zip":
            return _extract_zip(src, dest)
        if kind in ("tar", "gzip", "bzip2", "xz"):
            with tarfile.open(src) as tf:
                tf.extractall(dest)
            return True, "tarfile"
    except Exception as e:
        log("  标准库解压失败，转 bsdtar: %s" % e)

    return _extract_bsdtar(src, dest)


def _extract_zip(src, dest):
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):   # 未标记 UTF-8 才需要修名
                name = fix_zip_name(name)
            name = name.replace("\\", "/")
            target = _safe_join(dest, name)
            if target is None:
                continue
            if info.is_dir() or name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # 目标已是目录时直接跳过，避免 IsADirectoryError 中断整个包
            if target.is_dir():
                continue
            with zf.open(info) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
    return True, "zipfile"


def _safe_join(base, name):
    """防目录穿越。"""
    target = (base / name).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def _extract_bsdtar(src, dest):
    """libarchive 兜底，能吃 rar/7z/cab 等。rar 必须整包解，不能按成员取。"""
    cmd = None
    for exe in ("bsdtar", "tar"):
        if has_cmd(exe):
            cmd = exe
            break
    if cmd is None:
        return False, "无 bsdtar/tar，无法解压该格式"
    try:
        r = subprocess.run(
            [cmd, "-xf", str(src), "-C", str(dest)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, "%s 解压超时" % cmd
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", "replace").strip()[:200]
        return False, "%s 解压失败: %s" % (cmd, err)
    return True, cmd


# --------------------------------------------------------------------------
# 文本提取
# --------------------------------------------------------------------------

def read_text_file(path):
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def strip_html(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"&nbsp;?", " ", raw)
    return re.sub(r"\s{2,}", " ", raw).strip()


def read_pdf(path, caps):
    fitz = caps.get("fitz")
    if fitz is None:
        if has_cmd("pdftotext"):
            try:
                r = subprocess.run(["pdftotext", str(path), "-"],
                                   capture_output=True, timeout=120)
                if r.returncode == 0:
                    return r.stdout.decode("utf-8", "replace"), None
            except Exception:
                pass
        return "", "缺 PyMuPDF 且无 pdftotext，PDF 无法提取"
    try:
        doc = fitz.open(str(path))
        text = "".join(p.get_text() for p in doc)
        pages = doc.page_count
        doc.close()
    except Exception as e:
        return "", "PDF 打开失败: %s" % e
    if len(text.strip()) < 20 and pages > 0:
        return "", "图片型 PDF，无可提取文本层，需用视觉能力阅读"
    return text, None


def read_docx(path, caps):
    docx = caps.get("docx")
    if docx is not None:
        try:
            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            return "\n".join(parts), None
        except Exception as e:
            return "", "docx 解析失败: %s" % e
    if has_cmd("textutil"):   # macOS 兜底
        try:
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                               capture_output=True, timeout=120)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", "replace"), None
        except Exception:
            pass
    return "", "缺 python-docx 且无 textutil，docx 无法提取"


def read_pptx(path, caps):
    pptx = caps.get("pptx")
    if pptx is None:
        return "", "缺 python-pptx，pptx 无法提取"
    try:
        prs = pptx.Presentation(str(path))
    except Exception as e:
        return "", "pptx 解析失败: %s" % e
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append("--- 第 %d 页 ---" % i)
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                parts.append(shape.text_frame.text)
    return "\n".join(parts), None


def content_of(path, caps):
    """返回 (文本, 失败原因)。失败原因为 None 表示成功。"""
    kind = sniff(path)
    ext = path.suffix.lower()

    if kind == "pdf":
        return read_pdf(path, caps)
    if kind == "docx":
        return read_docx(path, caps)
    if kind == "pptx":
        return read_pptx(path, caps)
    if kind == "xlsx":
        return "", "xlsx 表格不做文本提取"
    if kind == "ole":
        if has_cmd("textutil"):
            try:
                r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                                   capture_output=True, timeout=120)
                if r.returncode == 0:
                    return r.stdout.decode("utf-8", "replace"), None
            except Exception:
                pass
        return "", "老式 doc/ppt 格式，无可用转换工具"
    if kind == "text" or ext in TEXT_EXTS:
        raw = read_text_file(path)
        if ext in HTML_EXTS or raw.lstrip()[:200].lower().startswith(("<!doctype", "<html")):
            return strip_html(raw), None
        return raw, None
    if kind in ("empty",):
        return "", "空文件"
    if kind == "unreadable":
        return "", "文件不可读"
    return "", "二进制文件（%s），跳过" % kind


# --------------------------------------------------------------------------
# 哈希
# --------------------------------------------------------------------------

def file_digest(path):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return "unreadable"
    return h.hexdigest()


def entry_digest(path):
    """目录取全部文件的聚合指纹，单文件取自身指纹。"""
    if path.is_file():
        return file_digest(path)
    h = hashlib.md5()
    for p in sorted(path.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            rel = p.relative_to(path).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(file_digest(p).encode("ascii"))
    return h.hexdigest()


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def file_priority(p):
    """SKILL.md 最优先，README 次之，再按格式可读性排。"""
    name = p.name.lower()
    ext = p.suffix.lower()
    if name in ("skill.md", "skill.markdown") or name == "skill":
        return 0
    if name.startswith("readme"):
        return 1
    if ext in (".md", ".markdown"):
        return 2
    if ext in TEXT_EXTS:
        return 3
    if ext in (".pdf", ".docx", ".pptx", ".doc", ".ppt"):
        return 4
    if ext in HTML_EXTS:
        return 5
    return 6


def gather_files(entry):
    if entry.is_file():
        return [entry]
    files = [p for p in entry.rglob("*")
             if p.is_file() and not p.name.startswith(".")
             and "__MACOSX" not in p.parts]
    files.sort(key=lambda p: (file_priority(p), len(p.parts), p.name))
    return files


def should_skip(name, report_names):
    if name.startswith("."):
        return "隐藏条目"
    if CATEGORY_DIR_RE.match(name):
        return "已整理的分类目录"
    if name in report_names:
        return "报告或账本自身"
    return None


def detect_report_files(target):
    """按内容特征识别旧报告：含「原始文件名」列的 markdown 表格。"""
    names = {"Skill分析报告-数据.json"}
    for p in target.glob("*.md"):
        try:
            head = p.read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            continue
        if "原始文件名" in head and "| ---" in head:
            names.add(p.name)
    for p in target.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "entries" in data and "taxonomy" in data:
            names.add(p.name)
    return names


def main():
    ap = argparse.ArgumentParser(description="skill 收藏目录的批量解压与文本提取")
    ap.add_argument("--target", required=True, help="待整理目录")
    ap.add_argument("--workdir", default=None, help="中间产物目录，默认建在系统临时目录")
    ap.add_argument("--ledger", default=None, help="账本路径，用于增量跳过已入账且未变的条目")
    ap.add_argument("--budget", type=int, default=8000, help="单条目提取字符上限")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        log("目标目录不存在: %s" % target)
        return 2

    workdir = Path(args.workdir).expanduser().resolve() if args.workdir else \
        Path(tempfile.mkdtemp(prefix="skillcurator-"))
    dumps = workdir / "dumps"
    unpack = workdir / "unpacked"
    dumps.mkdir(parents=True, exist_ok=True)
    unpack.mkdir(parents=True, exist_ok=True)

    caps = {
        "fitz": try_import("fitz"),
        "docx": try_import("docx"),
        "pptx": try_import("pptx"),
    }
    log("工具能力: PyMuPDF=%s python-docx=%s python-pptx=%s bsdtar=%s textutil=%s"
        % (caps["fitz"] is not None, caps["docx"] is not None, caps["pptx"] is not None,
           has_cmd("bsdtar"), has_cmd("textutil")))

    known = {}
    if args.ledger and Path(args.ledger).is_file():
        try:
            data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            for e in data.get("entries", []):
                if e.get("original_name") and e.get("hash"):
                    known[e["original_name"]] = e["hash"]
        except Exception as e:
            log("账本读取失败，按首次整理处理: %s" % e)

    report_names = detect_report_files(target)
    if report_names:
        log("识别到报告/账本文件: %s" % ", ".join(sorted(report_names)))

    entries, failures, suspicious, skipped = [], [], [], []

    for item in sorted(target.iterdir(), key=lambda p: p.name):
        reason = should_skip(item.name, report_names)
        if reason:
            skipped.append({"name": item.name, "reason": reason})
            continue

        digest = entry_digest(item)
        if known.get(item.name) == digest:
            entries.append({"name": item.name, "status": "unchanged", "hash": digest})
            log("跳过（未变）: %s" % item.name)
            continue

        log("处理: %s" % item.name)
        rec = process_entry(item, digest, unpack, dumps, caps, args.budget)
        entries.append(rec)

        if rec.get("failed_files"):
            failures.append({"name": item.name, "details": rec["failed_files"]})
        if rec.get("suspicious"):
            suspicious.append({"name": item.name, "reason": rec["suspicious"]})
        if any(w in item.name.lower() for w in INBOX_WORDS) and item.is_dir():
            rec["maybe_inbox"] = True

    index = {
        "target": str(target),
        "workdir": str(workdir),
        "counts": {
            "entries": len(entries),
            "skipped": len(skipped),
            "failed": len(failures),
            "suspicious": len(suspicious),
        },
        "entries": entries,
        "skipped": skipped,
        "failures": failures,
        "suspicious": suspicious,
    }
    (workdir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(index["counts"], ensure_ascii=False))
    log("")
    log("中间产物: %s" % workdir)
    log("条目 %d，跳过 %d，提取失败 %d，可疑 %d"
        % (len(entries), len(skipped), len(failures), len(suspicious)))
    if suspicious:
        log("可疑清单（提取成功但内容近乎为空，需人工过目）:")
        for s in suspicious:
            log("  - %s : %s" % (s["name"], s["reason"]))
    if failures:
        log("失败清单:")
        for f in failures:
            for d in f["details"][:3]:
                log("  - %s : %s" % (f["name"], d))
    return 0


def process_entry(item, digest, unpack, dumps, caps, budget):
    rec = {
        "name": item.name,
        "status": "new",
        "hash": digest,
        "kind": "dir" if item.is_dir() else sniff(item),
        "failed_files": [],
        "suspicious": None,
    }

    root = item
    if item.is_file() and rec["kind"] in ARCHIVE_KINDS:
        dest = unpack / _slug(item.name)
        ok, how = extract_archive(item, dest, rec["kind"])
        rec["extracted_by"] = how
        if ok:
            rec["form"] = "解压包"
            root = _descend_single(dest)
        else:
            rec["form"] = "单文件"
            rec["failed_files"].append("解压失败: %s" % how)
            rec["suspicious"] = "压缩包无法解压"
            _write_dump(dumps, item.name, "")
            return rec
    elif item.is_dir():
        rec["form"] = "文件夹"
        # 文件夹内部若还有压缩包，额外解一份出来供阅读
        for sub in list(item.rglob("*")):
            if sub.is_file() and sniff(sub) in ARCHIVE_KINDS:
                dest = unpack / (_slug(item.name) + "__" + _slug(sub.stem))
                ok, _ = extract_archive(sub, dest, sniff(sub))
                if ok:
                    rec.setdefault("inner_archives", []).append(sub.name)
    else:
        rec["form"] = "单文件"

    files = gather_files(root)
    rec["file_count"] = len(files)
    rec["has_skill_md"] = any(f.name.lower() == "skill.md" for f in files)

    chunks, used, total_bytes = [], 0, 0
    for f in files:
        if used >= budget:
            break
        text, err = content_of(f, caps)
        if err:
            rec["failed_files"].append("%s : %s" % (f.name, err))
            continue
        text = text.strip()
        if not text:
            continue
        total_bytes += len(text.encode("utf-8"))
        # SKILL.md 全文优先不截断，其余按剩余预算填
        if f.name.lower() == "skill.md":
            piece = text
        else:
            piece = text[: max(0, budget - used)]
        if piece:
            rel = f.relative_to(root) if root in f.parents or root == f.parent else f.name
            chunks.append("===== %s =====\n%s" % (rel, piece))
            used += len(piece)

    dump = "\n\n".join(chunks)
    rec["chars"] = len(dump)
    rec["dump"] = _write_dump(dumps, item.name, dump)

    if len(dump) < SUSPICIOUS_CHARS:
        rec["suspicious"] = "提取文本仅 %d 字符" % len(dump)
    elif not rec["has_skill_md"] and total_bytes < SUSPICIOUS_TOTAL_BYTES:
        rec["suspicious"] = "无 SKILL.md 且总提取量仅 %d 字节" % total_bytes
    return rec


def _descend_single(path):
    """解压后若只有一个顶层目录，下沉进去，避免多包一层。"""
    kids = [p for p in path.iterdir() if p.name not in ("__MACOSX",) and not p.name.startswith(".")]
    if len(kids) == 1 and kids[0].is_dir():
        return kids[0]
    return path


def _slug(name):
    return re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", name)[:80]


def _write_dump(dumps, name, text):
    p = dumps / (_slug(name) + ".txt")
    p.write_text(text, encoding="utf-8")
    return str(p)


if __name__ == "__main__":
    sys.exit(main())
