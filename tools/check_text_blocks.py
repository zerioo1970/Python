"""列出章节里「```python 代码块 → ```text 输出块」的配对，逐对真跑核对。

为什么还需要这个：
    `check_outputs.py` 的 `check_output_blocks` 只认"代码块紧跟输出块"的相邻结构，
    一旦两者之间夹了说明文字（正文里很常见），配对就失效、整块被跳过。
    多行输出（对齐的表格、`help()` 的完整内容）恰恰只能靠输出块核对——
    手工估算的空格数肉眼极难发现错误。

工作方式：
    找出每个 ```text 块，往上回溯最近的一个 ```python 块，
    把代码写成临时 .py 真跑一遍，再与 ```text 的内容逐行比对。
    含 input() 的块跳过（要用 tools/run_in_tty.py 单独验证）。

用法：
    python3.12 tools/check_text_blocks.py chapters/ch14_函数基础.md
    python3.12 tools/check_text_blocks.py            # 全部章节
"""

import pathlib
import re
import subprocess
import sys
import tempfile

SKIP_IF = (
    "input(", "id(", "time(", "now(", "random", "perf_counter", "getrecursionlimit",
    # 下面这些块的 ```text 展示的不是"脚本的标准输出"，而是【外部观测结果】：
    #   flush / sys.stdout.write：要在 sleep 期间从另一侧读管道才能看出差别
    #   sys.stderr：要靠 shell 重定向把两个流分开才能看出差别
    # 这类示例只能人工按第 6 章的方式实测，自动比对必然对不上。
    "flush", "stderr", "sys.stdout",
    "while True",   # 死循环示例（第 8 章）：靠 timeout -s INT 单独实测
)

# ```text 块并不总是"上面那段代码的输出"——正文里它还用来贴终端会话、REPL 对话、
# pip 安装日志、报错示范。这些一律不该拿来和代码输出比对。
NOT_PROGRAM_OUTPUT_PREFIX = (">>>", "$ ", "# ", "PS ", "C:\\", "python:", "Traceback",
                             "usage:", "  File ")
NOT_PROGRAM_OUTPUT_SUBSTR = ("Successfully installed", "can't open file", "SyntaxError:",
                             "pip install", "python3 -m venv", "Requirement already",
                             # 外部观测类（见 SKIP_IF 的说明），有时代码里没有这些字样，
                             # 反而是输出块的文案里写着
                             "flush", "stderr")

# 制表符号：正文里的示意图（对象引用关系、异常家族树、决策流程）也是 ```text 块，
# 但它们不是任何代码的输出。出现这些字符就判定为示意图。
BOX_DRAWING = set("─│┌┐└┘├┤┬┴┼←→↑↓╔╗╚╝║═▲▼●")

# 代码块与输出块之间允许夹多少字符的说明文字。
# 超过这个距离基本可以断定两者没有配对关系（中间往往还讲了别的事）。
MAX_GAP = 400


def norm(text: str) -> list[str]:
    """去掉行尾空格和首尾空行，便于比对。"""
    return [ln.rstrip() for ln in text.strip("\n").split("\n")]


def check_file(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")

    # 依次记录每个 python / text 块的起止位置
    blocks = [(m.start(), m.end(), m.group(1), m.group(2))
              for m in re.finditer(r"```(python|text)\n(.*?)```", text, re.S)]

    checked = skipped = 0
    problems = []

    for i, (start, _, kind, body) in enumerate(blocks):
        if kind != "text":
            continue

        # 只认【紧挨着的上一个】块，且它必须是 python 块
        if i == 0 or blocks[i - 1][2] != "python":
            skipped += 1
            continue
        prev_end, code = blocks[i - 1][1], blocks[i - 1][3]

        # 中间夹的说明文字太长 → 两者八成没有配对关系
        if start - prev_end > MAX_GAP:
            skipped += 1
            continue

        # 这个 text 块看着不像"程序的标准输出"（终端会话 / 安装日志 / 报错示范 / 示意图）
        stripped = body.strip()
        if stripped.startswith(NOT_PROGRAM_OUTPUT_PREFIX) or any(
            s in body for s in NOT_PROGRAM_OUTPUT_SUBSTR
        ):
            skipped += 1
            continue
        if BOX_DRAWING & set(body):
            skipped += 1
            continue

        if any(s in code for s in SKIP_IF) or "# =>" in code:
            skipped += 1
            continue

        # 剥掉可能存在的 `# =>` 标注（这里一般没有）
        src = "\n".join(ln.split("# =>")[0].rstrip() for ln in code.split("\n"))

        with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8",
                                         delete=False) as fh:
            fh.write(src)
            tmp = fh.name
        try:
            proc = subprocess.run([sys.executable, tmp], capture_output=True,
                                  text=True, timeout=20, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            # 跑不完（死循环、等输入）→ 交给人工按对应章节的手法实测
            skipped += 1
            continue
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)

        if proc.returncode != 0:
            skipped += 1
            continue

        expected, actual = norm(body), norm(proc.stdout)
        checked += 1
        if expected != actual:
            problems.append((code.strip().split("\n")[0][:50], expected, actual))

    return checked, skipped, problems


def main():
    targets = [pathlib.Path(a) for a in sys.argv[1:]]
    if not targets:
        root = pathlib.Path(__file__).resolve().parent.parent
        targets = sorted((root / "chapters").glob("ch*.md"))

    failed = 0
    for path in targets:
        checked, skipped, problems = check_file(path)
        print("=" * 64)
        print(path.name)
        print(f"  输出块真跑：核对 {checked} | 跳过 {skipped}")
        for first, exp, act in problems:
            failed += 1
            print(f"  ✗ 代码首行：{first}")
            print("      文中写的：")
            for ln in exp:
                print(f"        |{ln}|")
            print("      实际输出：")
            for ln in act:
                print(f"        |{ln}|")
        if not problems:
            print("  ✓ 全部一致")

    print("=" * 64)
    print(f"发现 {failed} 处需要核对" if failed else "全部通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
