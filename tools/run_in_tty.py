"""
在伪终端里运行一个交互式脚本并喂入输入，拿到读者在真实终端里看到的完整画面。

为什么需要它：
    含 input() 的示例无法用管道验证——管道输入时用户敲的字符不会回显，
    输出会变成「第一个数字：第二个数字：105」这种读者根本看不到的样子。
    伪终端能还原真实画面（含输入回显），这样正文里贴的输出才是读者真实所见。

用法：
    python3 tools/run_in_tty.py 脚本.py 输入1 输入2 ...

例：
    python3 tools/run_in_tty.py card.py 小明 工程师 13800138000

说明：
    - 每个输入参数会被自动补上换行后依次送入
    - 用 python3.12 运行目标脚本（与教程实测版本一致，见规范 6.7）
    - 输出里的 \\r\\n 是伪终端的正常产物，贴进正文时按 \\n 处理
"""

import os
import pty
import sys
import time

INTERPRETER = "python3.12"


def run(script: str, inputs: list[str], feed_delay: float = 0.25) -> str:
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(INTERPRETER, [INTERPRETER, script])
        os._exit(1)

    time.sleep(0.3)
    for line in inputs:
        os.write(fd, (line + "\n").encode())
        time.sleep(feed_delay)

    time.sleep(0.5)
    out = b""
    try:
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            out += chunk
    except OSError:
        pass

    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass

    return out.decode(errors="replace")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    script, *inputs = sys.argv[1:]
    sys.stdout.write(run(script, inputs).replace("\r\n", "\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
