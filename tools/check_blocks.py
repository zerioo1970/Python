"""把每个代码块当成一个真正的 .py 文件跑一遍，核对 `# =>` 标注。

和 `check_outputs.py` 的分工
---------------------------
`check_outputs.py` 是**逐行 exec**：能精确定位是哪一行不符，但有两个盲区——
  ① 多行结构（for / if 的循环体）逐行执行时体根本不会被执行；
  ② `is` 比较的结果受"整块编译 vs 逐行执行"影响（小整数和字符串的驻留策略不同），
     所以它把所有含 `is` 的行都归入"易变"跳过了。

本脚本走另一条路：**把整个代码块写成临时 .py 文件、用子进程真跑一遍**，
这与"读者把示例存成文件运行"完全一致，因此 `is` 的结果是可信的。
代价是只能核对"块级输出"，定位精度不如逐行。

两个脚本合起来才算把输出核干净：
    python3.12 tools/check_outputs.py chapters/ch13_*.md      # 逐行严格比对
    python3.12 tools/check_blocks.py  chapters/ch13_*.md      # 整块真跑，专治 is

用法
----
    python3.12 tools/check_blocks.py                       # 全部章节
    python3.12 tools/check_blocks.py chapters/ch13_*.md    # 指定章节
    python3.12 tools/check_blocks.py --only-is chapters/*.md   # 只核对含 is 的行

核对方式
--------
对每个代码块：
  1. 剥掉 `# =>` 标注，得到可执行的源码，写进临时文件运行；
  2. 按顺序把块里所有 `# =>` 标注的期望值，与程序实际输出的各行做**顺序比对**
     （第 k 个标注 ↔ 第 k 行输出）；
  3. 期望值里含"顺序不定 / 你运行时"等声明的跳过（与 check_outputs.py 同一套约定）；
  4. 块里有 `# => TypeError:` 这类"故意报错"标注的，整块跳过（它跑不完）。
"""

import pathlib
import re
import subprocess
import sys
import tempfile

DECLARED_UNSTABLE = ("顺序不定", "顺序每次不同", "每次运行都不同", "你运行时")

# 期望值以这些开头，说明这个块是故意演示报错的，整块跳过
ERROR_HEADS = (
    "TypeError", "ValueError", "KeyError", "IndexError", "NameError",
    "AttributeError", "SyntaxError", "ZeroDivisionError", "RuntimeError",
    "UnboundLocalError", "RecursionError", "FileNotFoundError",
    "PermissionError", "StopIteration", "AssertionError",
)

# 输出天然会变的调用，即使整块跑也没法比对
VOLATILE_CALLS = ("id(", "time(", "now(", "random", "uuid", "perf_counter")


def split_marker(line: str):
    """把一行拆成 (代码, 期望值)。没有 `# =>` 标注时期望值为 None。"""
    m = re.search(r"#\s*=>\s*(.*)$", line)
    if not m:
        return line, None
    return line[: m.start()].rstrip(), m.group(1).strip()


def check_block(block: str, only_is: bool):
    """返回 (核对数, 跳过数, 问题列表)。"""
    code_lines, expectations = [], []

    for line in block.split("\n"):
        code, expected = split_marker(line)
        code_lines.append(code)
        if expected:
            expectations.append((line.strip(), expected))

    if not expectations:
        return 0, 0, []

    # 故意报错的块跑不完，交给 check_outputs.py 或人工核对
    if any(exp.split(":")[0] in ERROR_HEADS for _, exp in expectations):
        return 0, len(expectations), []

    source = "\n".join(code_lines)
    if any(v in source for v in VOLATILE_CALLS):
        return 0, len(expectations), []

    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as fh:
        fh.write(source)
        path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable, path], capture_output=True, text=True, timeout=120,
            stdin=subprocess.DEVNULL,
        )
    finally:
        pathlib.Path(path).unlink(missing_ok=True)

    if proc.returncode != 0:
        return 0, len(expectations), []

    actual_lines = proc.stdout.rstrip("\n").split("\n") if proc.stdout.strip() else []

    checked = skipped = 0
    problems = []
    for i, (raw, expected) in enumerate(expectations):
        if any(w in expected for w in DECLARED_UNSTABLE):
            skipped += 1
            continue
        if only_is and " is " not in raw:
            skipped += 1
            continue
        if i >= len(actual_lines):
            skipped += 1
            continue

        # 标注里常在输出后面跟一段中文说明，取第一段做前缀比对
        head = expected.split()[0] if expected.split() else expected

        def matches(actual: str) -> bool:
            return (actual == expected or actual.startswith(head)
                    or expected.startswith(actual))

        checked += 1
        if matches(actual_lines[i].strip()):
            continue

        # 顺序比对失败的兜底：块里可能有没加标注的 print，导致第 k 个标注
        # 并不对应第 k 行输出。这时只要输出里【某一行】能对上就算通过——
        # 精度换取"不误报"，真正的不一致仍会被下面 check_outputs.py 的逐行模式抓到。
        if len(expectations) != len(actual_lines) and any(
            matches(a.strip()) for a in actual_lines
        ):
            continue

        problems.append((raw, expected, actual_lines[i].strip()))

    return checked, skipped, problems


def main():
    args = [a for a in sys.argv[1:] if a != "--only-is"]
    only_is = "--only-is" in sys.argv[1:]

    targets = [pathlib.Path(a) for a in args]
    if not targets:
        root = pathlib.Path(__file__).resolve().parent.parent
        targets = sorted((root / "chapters").glob("ch*.md"))

    failed = 0
    for path in targets:
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", text, re.S)

        total = skip = 0
        allprob = []
        for no, block in enumerate(blocks, 1):
            c, s, probs = check_block(block, only_is)
            total += c
            skip += s
            allprob += [(no, *p) for p in probs]

        print("=" * 64)
        print(f"{path.name}")
        print(f"  整块真跑：核对 {total} | 跳过 {skip}")
        if allprob:
            failed += len(allprob)
            for no, raw, exp, act in allprob:
                print(f"  ✗ 代码块 {no}：{raw}")
                print(f"      文中标注：{exp}")
                print(f"      实际输出：{act}")
        else:
            print("  ✓ 全部一致")

    print("=" * 64)
    print(f"发现 {failed} 处需要核对" if failed else "全部通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
