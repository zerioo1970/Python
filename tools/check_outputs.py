"""
核对章节正文里的示例输出是否与实际运行结果一致。

用途：规范（02_施工图.md 第 7 节自检清单）要求"所有输出标注必须与真实运行结果一致，
不能凭记忆写"。这个脚本自动完成核对。

用法：
    python3 tools/check_outputs.py                # 检查全部章节
    python3 tools/check_outputs.py chapters/ch03_变量与基本数据类型.md

工作方式：
    抽出所有 ```python 代码块，逐行执行，凡是带 `# =>` 标注的行就把实际输出
    与标注对比。故意报错的示例和依赖上下文的行会被自动跳过并计入 skipped。

注意：
    - `id()`、内存地址、随机数、当前时间这类输出每次运行都不同，会被报为不一致，
      属于预期，文中应已注明"你运行时的结果会不同"。
    - 建议用与教程要求一致的版本运行（3.10+），因为报错文字随版本变化。
"""

import contextlib
import io
import pathlib
import re
import sys

# 输出天然会变化、或依赖执行方式的调用，不参与比对
#   id() / 内存地址 / 时间 / 随机数：每次运行都不同
#   is 比较：结果取决于代码是整块编译还是逐行执行（见第 4 章示例 4-17）。
#            本脚本是逐行 exec，与读者把示例存成 .py 整块运行的结果可能相反，
#            这种示例的输出必须人工按"整块运行"的方式核对。
VOLATILE = (
    "id(", "time(", "now(", "random", "uuid", "sys.executable", "__defaults__",
    " is ", " is not ",
)


def check_output_blocks(text: str):
    """核对「```python 代码块紧跟 ```text 输出块」这种成对结构。

    行内 `# =>` 标注只能核对单行输出，多行输出（如对齐的表格）必须靠这个函数，
    否则手工估算的空格数会和真实输出不一致——这类错误肉眼极难发现。
    """
    pairs = re.findall(r"```python\n(.*?)```\s*\n+```text\n(.*?)```", text, re.S)
    checked = skipped = 0
    problems = []

    for code, expected in pairs:
        if any(v in code for v in VOLATILE) or "❌" in code or "# =>" in code:
            skipped += 1
            continue
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, {})
        except Exception:
            skipped += 1
            continue
        actual = buf.getvalue()
        # 忽略行尾空格和整体首尾空行的差异
        norm = lambda s: "\n".join(l.rstrip() for l in s.strip("\n").split("\n"))
        checked += 1
        if norm(actual) != norm(expected):
            problems.append((code.strip()[:60], norm(expected), norm(actual)))

    return checked, skipped, problems


def check_file(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)

    total = ok = skipped = volatile = 0
    problems = []

    for block_no, block in enumerate(blocks, 1):
        if not re.search(r"#\s*=>", block):
            continue

        env: dict = {}
        for line in block.split("\n"):
            marker = re.search(r"#\s*=>\s*(.+)$", line)
            code = line.split("#")[0].rstrip() if marker else line
            if not code.strip():
                continue

            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    exec(code, env)
            except Exception:
                # 故意报错的示例，或依赖别处定义的变量
                if marker:
                    skipped += 1
                continue

            if not marker:
                continue

            if any(v in code for v in VOLATILE):
                volatile += 1
                continue

            total += 1
            expected = marker.group(1).strip()
            actual = buf.getvalue().strip()

            # 标注里常带中文说明（如 "3 不是 4"），只要开头对上就算通过
            head = expected.split()[0] if expected else ""
            if actual == expected or (head and actual.startswith(head)):
                ok += 1
            else:
                problems.append((block_no, code.strip(), expected, actual))

    return total, ok, skipped, volatile, problems


def main():
    targets = [pathlib.Path(a) for a in sys.argv[1:]]
    if not targets:
        root = pathlib.Path(__file__).resolve().parent.parent
        targets = sorted((root / "chapters").glob("ch*.md"))

    failed = 0
    for path in targets:
        total, ok, skipped, volatile, problems = check_file(path)
        blk_checked, blk_skipped, blk_problems = check_output_blocks(
            path.read_text(encoding="utf-8")
        )
        print("=" * 64)
        print(path.name)
        print(f"  行内标注：核对 {total} | 一致 {ok} | 跳过 {skipped} | 易变 {volatile}")
        print(f"  输出块　：核对 {blk_checked} | 跳过 {blk_skipped}")

        if problems:
            failed += len(problems)
            for block_no, code, exp, act in problems:
                print(f"  ✗ 代码块 {block_no}：{code}")
                print(f"      文中标注：{exp}")
                print(f"      实际输出：{act}")

        if blk_problems:
            failed += len(blk_problems)
            for code, exp, act in blk_problems:
                print(f"  ✗ 输出块不一致，代码：{code}")
                print("      文中写的：")
                for line in exp.split("\n"):
                    print(f"        |{line}|")
                print("      实际输出：")
                for line in act.split("\n"):
                    print(f"        |{line}|")

        if not problems and not blk_problems:
            print("  ✓ 全部一致")

    print("=" * 64)
    print("发现 %d 处需要核对" % failed if failed else "全部通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
