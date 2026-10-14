#!/usr/bin/env python3
"""
eml_to_mbox.py - Convert EML files to MBOX format with global character support.

This tool converts one or more .eml files (RFC 5322 formatted email messages)
into a single MBOX file (mboxrd variant), handling international character
encodings (UTF-8, ISO-8859-1, GB2312, Shift-JIS, etc.) correctly.

MBOX format (mboxrd):
  - Each message is preceded by a separator line:  From <addr> <date>
  - Any line in the message body that begins with "From " is prefixed with ">"
  - Messages are separated by a blank line
  - The file is written as UTF-8 bytes

Usage:
  python3 eml_to_mbox.py <eml_file_or_dir> [...] [-o output.mbox]
"""

import argparse
import os
import re
import sys
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, formatdate, getaddresses


def build_from_line(msg):
    """根据邮件头生成 MBOX 消息分隔行。

    参数:
        msg: 已解析的邮件对象，用于读取发件人和日期等邮件头。

    返回:
        str: 以 "From " 开头、包含发件人地址和日期的分隔行，不含换行符。

    发件人缺失时使用占位地址；日期缺失或无法解析时使用当前时间。
    """
    # Try to extract a sender address from common headers
    sender = None
    for hdr in ("From", "Sender", "Reply-To", "Return-Path"):
        val = msg.get(hdr)
        if val:
            addrs = getaddresses([val])
            if addrs:
                sender = addrs[0][1]
                break
    if not sender:
        sender = "unknown@unknown.invalid"

    # Try to extract the date
    date_hdr = msg.get("Date")
    if date_hdr:
        try:
            dt = parsedate_to_datetime(date_hdr)
            # MBOX From-line uses asctime() style: "Fri Dec 17 10:48:22 2004"
            from_date = dt.strftime("%a %b %d %H:%M:%S %Y")
        except (TypeError, ValueError, IndexError):
            from_date = formatdate(usegmt=False)
    else:
        from_date = formatdate(usegmt=False)

    # Clean sender for the From line (no spaces)
    sender = sender.replace(" ", "")
    return f"From {sender} {from_date}"


def escape_from_lines(raw_bytes):
    """为输入中可能被识别为 MBOX 分隔行的文本行添加转义前缀。

    参数:
        raw_bytes: 以 LF 分隔行的邮件字节内容；本方法不区分邮件头和正文。

    返回:
        bytes: 转义后的内容，将行首 "From " 改为 ">From "，
        将行首 ">From " 改为 ">>From "，其他行保持不变。
    """
    lines = raw_bytes.split(b"\n")
    escaped = []
    for line in lines:
        if line.startswith(b"From "):
            escaped.append(b">" + line)
        elif line.startswith(b">From "):
            # mboxrd: also escape already-escaped From lines
            count = 0
            stripped = line
            while stripped.startswith(b">"):
                count += 1
                stripped = stripped[1:]
            if stripped.startswith(b"From "):
                escaped.append(b">" + line)
            else:
                escaped.append(line)
        else:
            escaped.append(line)
    return b"\n".join(escaped)


def convert_eml_to_bytes(eml_path):
    """读取单个 EML 文件，生成可写入 MBOX 的消息字节内容。

    参数:
        eml_path: 待读取的 EML 文件路径。

    返回:
        bytes: 包含 MBOX 分隔行、转义后的邮件内容和末尾换行符的字节串。

    保留邮件原有字符编码和 MIME 内容，不进行字符集转码；
    仅规范化换行符并转义特殊行。文件读取或解析异常由调用方处理。
    """
    with open(eml_path, "rb") as f:
        raw = f.read()

    # Parse to extract From-line metadata (does not modify raw body)
    msg = BytesParser(policy=policy.default).parsebytes(raw)

    from_line = build_from_line(msg)

    # Normalize line endings to LF
    raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    # Escape From lines in the body
    body = escape_from_lines(raw)

    # Assemble: From line + body + trailing newline
    result = from_line.encode("utf-8") + b"\n" + body
    if not result.endswith(b"\n"):
        result += b"\n"
    return result


def collect_eml_files(inputs):
    """从指定文件和目录中收集 EML 文件，目录会被递归扫描。

    参数:
        inputs: 文件或目录路径的可迭代对象。

    返回:
        list[str]: 按路径排序、去除重复路径后的 EML 文件列表。

    扩展名匹配不区分大小写；非 EML 文件和不存在的路径会被跳过，
    并向标准错误输出警告。
    """
    eml_files = []
    for path in inputs:
        if os.path.isfile(path):
            if path.lower().endswith(".eml"):
                eml_files.append(path)
            else:
                print(f"Warning: skipping non-eml file: {path}", file=sys.stderr)
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for fn in sorted(files):
                    if fn.lower().endswith(".eml"):
                        eml_files.append(os.path.join(root, fn))
        else:
            print(f"Warning: path not found: {path}", file=sys.stderr)
    return sorted(set(eml_files))


def convert(inputs, output_path, append=False):
    """批量转换 EML 文件，并将消息写入同一个 MBOX 文件。

    参数:
        inputs: 包含 EML 文件或目录路径的可迭代对象。
        output_path: 目标 MBOX 文件路径。
        append: 为 True 时追加写入，为 False 时覆盖原文件。

    返回:
        int: 0 表示成功，1 表示未找到 EML 文件，2 表示单封邮件转换
        或写入失败。打开输出文件时的异常会继续向调用方抛出。

    转换失败时立即停止，已写入的消息不会回滚。
    """
    eml_files = collect_eml_files(inputs)
    if not eml_files:
        print("Error: no .eml files found.", file=sys.stderr)
        return 1

    mode = "ab" if append else "wb"
    with open(output_path, mode) as out:
        if not append and out.tell() == 0:
            # Nothing to do; fresh file
            pass
        for eml in eml_files:
            try:
                chunk = convert_eml_to_bytes(eml)
                out.write(chunk)
                out.write(b"\n")  # blank line separator between messages
                print(f"Converted: {eml}")
            except Exception as e:
                print(f"Error converting {eml}: {e}", file=sys.stderr)
                return 2

    print(f"\nSuccessfully wrote {len(eml_files)} message(s) to {output_path}")
    return 0


def main():
    """解析命令行参数，调用批量转换方法并以其返回码退出程序。

    接受一个或多个 EML 文件或目录，通过 -o 指定输出路径，
    通过 -a 启用追加模式。无参数、无返回值，退出时抛出 SystemExit。
    """
    parser = argparse.ArgumentParser(
        description="Convert EML files to MBOX format with global character support."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="EML file(s) or directory/directories containing EML files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.mbox",
        help="Output MBOX file path (default: output.mbox).",
    )
    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        help="Append to the output MBOX file instead of overwriting it.",
    )
    args = parser.parse_args()

    sys.exit(convert(args.inputs, args.output, args.append))


if __name__ == "__main__":
    main()
