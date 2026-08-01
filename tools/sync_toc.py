"""
把某一章的小节列表整块替换进 01_目录.md。

用途：施工图写完一章后，目录里的小节需要同步更新。手工写 str_replace 要精确匹配原文，
      容易因为标点、空格差异失败；而把新内容写进文件再由脚本替换，既不用匹配原文，
      也避开了 shell / Python 的引号冲突。

用法：
    python3 tools/sync_toc.py 21 新小节.txt

参数：
    章号        目录里 "### 第 N 章" 的 N
    内容文件    每行一个小节（形如 "- 21.1 xxx"），UTF-8 编码

行为：
    - 定位 "### 第 N 章 ..." 标题行，替换到下一个 "### " / "> ### " / "## " 之前的全部内容
    - 标题下方以 "> " 开头的引言行会被保留（有些章节有编写说明）
"""

import pathlib
import re
import sys


def replace_chapter(toc_path: pathlib.Path, chapter_no: int, new_body: str) -> int:
    text = toc_path.read_text(encoding="utf-8")

    m = re.search(rf"^### 第 {chapter_no} 章[^\n]*\n", text, re.M)
    if not m:
        raise SystemExit(f"找不到「### 第 {chapter_no} 章」标题")

    start = m.end()
    nxt = re.search(r"^(### |> ### |## )", text[start:], re.M)
    end = start + (nxt.start() if nxt else len(text) - start)

    # 保留标题下方原有的引言行（以 "> " 开头）
    old_lines = text[start:end].split("\n")
    quote_lines = [l for l in old_lines if l.startswith("> ")]
    keep = ("\n".join(quote_lines) + "\n") if quote_lines else ""

    body = keep + new_body.strip("\n") + "\n\n"
    toc_path.write_text(text[:start] + body + text[end:], encoding="utf-8")

    return len([l for l in new_body.strip().split("\n") if l.startswith("- ")])


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)

    chapter_no = int(sys.argv[1])
    content = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")

    root = pathlib.Path(__file__).resolve().parent.parent
    count = replace_chapter(root / "01_目录.md", chapter_no, content)

    print(f"第 {chapter_no} 章目录已替换，{count} 个小节")
    return 0


if __name__ == "__main__":
    sys.exit(main())
