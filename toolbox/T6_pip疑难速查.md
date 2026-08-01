# T6　pip 疑难速查

> **这一节的定位**：第 1.7 节讲了 pip 的入门用法，第 19 章讲了它和虚拟环境的配合。**这里收的是"出问题时回来查"的内容**——装库失败的各种原因、依赖冲突、离线安装。
>
> **前提**：本节所有命令都假设你**已经激活了虚拟环境**（第 19.4 节）。如果没有，先去激活——绝大多数 pip 的怪问题都源于装到了错误的环境。
>
> **一个贯穿本节的习惯**：**用 `python -m pip` 而不是 `pip`**。前者明确指定"用哪个 Python 的 pip"，能避免"机器上有多个 Python，pip 装到别处去了"这类问题。

---

## T6.1 常用命令一览

### 天天用的

| 命令 | 作用 |
|---|---|
| `python -m pip install 包名` | 安装 |
| `python -m pip install 包名==2.32.5` | 装指定版本 |
| `python -m pip install -U 包名` | 升级 |
| `python -m pip uninstall 包名` | 卸载 |
| `python -m pip list` | 列出已安装的包 |
| `python -m pip show 包名` | 看版本、依赖、**安装位置** |
| `python -m pip freeze > requirements.txt` | 导出依赖清单 |
| `python -m pip install -r requirements.txt` | 按清单安装 |

### 不常用但关键的

| 命令 | 作用 | 什么时候用 |
|---|---|---|
| `pip list --outdated` | 列出有新版本的包 | 定期检查该不该升级 |
| **`pip check`** | 检查依赖是否冲突 | 装完一批包后确认没搞坏 |
| `pip show -f 包名` | 列出这个包装了哪些文件 | 排查文件冲突 |
| `pip download 包名` | 只下载不安装 | 准备离线安装（T6.5） |
| `pip cache dir` / `pip cache info` | 缓存位置与占用 | 磁盘紧张、缓存疑似损坏 |
| `pip install --no-deps 包名` | 不装依赖 | 明确知道依赖已装好、想避免版本被改动 |
| `pip install --dry-run 包名` | 只看会装什么，不真装 | 升级前预览影响范围 |

---

## T6.2 装库失败的六种原因

这是本节最有用的部分。**先看报错的最后几行**，然后按下面的表对号入座。

### 原因一：包名不存在或拼错了

```text
ERROR: Could not find a version that satisfies the requirement nosuchpackage-xyz123 (from versions: none)
ERROR: No matching distribution found for nosuchpackage-xyz123
```

**关键特征是 `(from versions: none)`** —— 一个版本都没找到，说明这个名字在源上根本不存在。

**常见原因**：

| 情况 | 例子 |
|---|---|
| 拼错了 | `beatifulsoup4` → 正确是 `beautifulsoup4` |
| **安装名和 import 名不一样** | 装的是 `beautifulsoup4`，代码里 `import bs4`；装 `pillow`，`import PIL`；装 `opencv-python`，`import cv2` |
| 用了下划线而实际是减号 | `python_dotenv` → 正确是 `python-dotenv` |
| 那个包只在特定源上 | 私有源、需要 `--index-url` |

> **"安装名 ≠ import 名"这件事没有规律**，只能查文档。遇到 `ModuleNotFoundError` 时，别急着 `pip install 那个模块名`——先搜一下"这个模块属于哪个包"。

### 原因二：版本号不存在

```text
ERROR: Could not find a version that satisfies the requirement requests==99.99.99 (from versions: 0.2.0, 0.2.1, ... 2.32.5, 2.33.0, 2.34.1, 2.34.2)
ERROR: No matching distribution found for requests==99.99.99
```

**注意 `from versions:` 后面列出了所有可用版本**——这带来一个很实用的技巧：

> ### 查一个包有哪些版本的最快办法
> **故意装一个不存在的版本**，pip 会把所有可用版本列给你：
> ```
> pip install requests==999
> ```
> 比翻网页快，而且不需要额外命令。
>
> （也有专门的命令 `pip index versions requests`，但它目前还是实验性的，会打印一行警告说未来可能变化。）

### 原因三：网络超时或连接失败

报错里通常有 `ReadTimeoutError`、`Connection broken`、`Could not fetch URL`。

**解法**（回收第 19.12 节）：

```bash
# 临时换源
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple

# 永久换源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 加长超时（大包如 torch 值得加）
pip install 包名 --timeout 120
```

**注意镜像的两个副作用**：① 有同步延迟，刚发布几小时的新版本可能拿不到 ② 私有包不在镜像上，需要用 `--index-url` 指定原始源。

### 原因四：需要本地编译（新手最容易卡住的一种）

报错特征：出现 `Building wheel for xxx`、`error: Microsoft Visual C++ 14.0 or greater is required`（Windows）、`gcc: command not found` / `Python.h: No such file or directory`（Linux）。

**为什么会这样**：有些包含 C 代码。作者通常会提供**预编译的 wheel 包**（`.whl`），装的时候直接解压就行。但如果**你的 Python 版本或系统平台没有对应的 wheel**，pip 就只能下源码在你的机器上编译——而编译需要编译器和头文件。

**四种解法，按推荐顺序**：

| 解法 | 做法 | 说明 |
|---|---|---|
| **① 换一个 Python 版本** | 用 3.12 而不是刚发布的 3.14 | **最常见的原因就是这个**：新版本 Python 刚出来时，很多包还没编译对应的 wheel |
| ② 装稍旧一点的包版本 | `pip install 包名==上一个版本` | 老版本可能有你平台的 wheel |
| ③ 装编译工具 | Windows 装 Visual Studio Build Tools；Debian/Ubuntu 装 `build-essential` + `python3-dev` | 有效但费时（几个 GB） |
| ④ 换 conda | 用 conda 装那个包 | 科学计算类的包（含大量 C/Fortran）conda 支持更好 |

> **提前打个招呼**：你以后装 `numpy` / `pandas` / `lightgbm` 这类包时可能遇到这个问题。**先试解法 ①**——用主流的稳定 Python 版本（不要用最新发布的那个），九成问题就没了。

### 原因五：Python 版本不兼容

报错特征：`requires a different Python`，或者 `Could not find a version` 但明明这个包存在。

**原因**：包在元数据里声明了 `requires-python`（比如 `>=3.10`），而你的 Python 太老（或者太新，少数包会限制上限）。

**怎么确认**：

```bash
python --version                  # 看自己的版本
pip install --dry-run 包名        # 预览，不真装
```

**解法**：升级 Python，或者装那个包支持你版本的旧版。

### 原因六：依赖冲突

报错特征：`ResolutionImpossible`，pip 会列出一串"A 要求 B>=2.0，而 C 要求 B<2.0"的冲突链。

**先看懂它在说什么**——报错里会写清是哪两个包对同一个依赖有矛盾要求。

**三种解法**：

| 解法 | 做法 |
|---|---|
| 放宽自己的约束 | 如果是你在 `requirements.txt` 里锁死了版本，试试放宽 |
| 分别查两个包的兼容版本 | 用 T6.2 原因二的技巧列出版本，找一个都能满足的组合 |
| **建一个干净的虚拟环境重装** | 冲突常常是环境里积累了半年的包造成的，从头装一遍反而快 |

### 汇总：报错关键词 → 原因

| 报错里出现 | 原因 | 去看 |
|---|---|---|
| `(from versions: none)` | 包名不存在/拼错 | 原因一 |
| `(from versions: 一长串)` | 版本号不对 | 原因二 |
| `ReadTimeoutError` / `Connection` | 网络 | 原因三 |
| `Building wheel` + `C++` / `gcc` / `Python.h` | 需要编译 | 原因四 |
| `requires a different Python` | Python 版本 | 原因五 |
| `ResolutionImpossible` | 依赖冲突 | 原因六 |
| `Permission denied` | **没在虚拟环境里**（在往系统目录装） | T6.10 |

---

## T6.3 `pip check`：依赖冲突怎么看

装了一堆包之后，环境里可能已经存在不兼容但还没暴露的问题。`pip check` 能查出来：

```bash
python -m pip check
```

一切正常时输出：

```text
No broken requirements found.
```

有问题时它会指出"某个包要求的依赖版本不满足"。

**什么时候该跑它**：

- 用 `-U` 升级了某个包之后（升级可能打破别的包的依赖）
- 用 `--no-deps` 装过东西之后
- 程序出现"某个库的函数不存在了"这类怪问题时

---

## T6.4 缓存

pip 会把下载过的包缓存起来，重装时不用再下载。

```bash
python -m pip cache dir        # 缓存在哪
python -m pip cache info       # 占了多少空间
python -m pip cache purge      # 全部清掉
```

实际输出长这样：

```text
/root/.cache/pip
Package index page cache location: /root/.cache/pip/http
Package index page cache size: 1.9 MB
Locally built wheels location: /root/.cache/pip/wheels
```

**什么时候需要动它**：

| 情况 | 做法 |
|---|---|
| 磁盘紧张（缓存可能有几个 GB） | `pip cache purge` |
| 怀疑缓存里的包损坏 | `pip install --no-cache-dir 包名` 绕过缓存重下 |
| 想让编译过的包被复用 | 什么都不用做，pip 会自动缓存编译结果（这也是为什么第二次装同一个包快很多） |

---

## T6.5 离线安装

场景：目标机器不能上网（内网服务器、隔离环境）。

**两步走**：

```bash
# 第一步：在能上网的机器上下载（注意要和目标机器同平台、同 Python 版本）
python -m pip download -r requirements.txt -d ./packages

# 第二步：把 packages 目录拷到目标机器，然后
python -m pip install --no-index --find-links=./packages -r requirements.txt
```

| 参数 | 作用 |
|---|---|
| `--no-index` | 不去网上找 |
| `--find-links=目录` | 从这个本地目录找包 |

**一个坑**：`pip download` 下的包是**针对当前平台和 Python 版本**的。在 Windows + 3.12 上下载的包，拿到 Linux + 3.10 上装不了。要跨平台下载得用 `--platform` / `--python-version` / `--only-binary=:all:` 组合，比较麻烦——**最省事的办法是在和目标机器相同的环境里下载**。

---

## T6.6 从 Git / 本地路径安装

```bash
# 从 Git 仓库装（装某个还没发布到 PyPI 的库，或者需要最新的未发布修复）
pip install git+https://github.com/用户名/仓库名.git

# 指定分支或标签
pip install git+https://github.com/用户名/仓库名.git@v1.2.0

# 从本地目录装
pip install ./my-package

# 从下载好的 wheel 文件装
pip install ./requests-2.32.5-py3-none-any.whl
```

**从 Git 装的注意事项**：装完之后 `pip freeze` 会把这个 Git 地址原样写进 `requirements.txt`，别人要能访问那个仓库才装得上。**生产项目慎用**——依赖一个随时可能变的分支是风险。

---

## T6.7 `pip install -e .` 可编辑安装

**场景**：你自己写了一个包（第 18 章的多模块项目），想在别处 `import` 它，但又不想每改一次代码就重装一遍。

```bash
# 在项目根目录（有 pyproject.toml 的地方）执行
pip install -e .
```

`-e` 是 `--editable`。它不会把代码复制到 `site-packages`，而是**做一个指向你项目目录的链接**——你改代码，立刻生效。

**这解决了什么问题**：第 18.8 节那个"明明有文件却 import 失败"的问题。可编辑安装之后，你的包在任何目录下都能被 import，不用折腾 `sys.path`。

**前提**：项目里要有 `pyproject.toml`（第 37 章会讲怎么写）。这是专项 E 的内容，现在知道有这回事就行。

---

## T6.8 `requirements.txt` 进阶

### 分层：区分"运行需要"和"开发需要"

```text
requirements.txt          ← 运行必需的：requests、pandas
requirements-dev.txt      ← 只有开发要用的：pytest、ruff、mypy
```

`requirements-dev.txt` 里可以用 `-r` 引用另一个文件：

```text
-r requirements.txt

pytest>=8.0
ruff
mypy
```

这样开发时装 `-r requirements-dev.txt` 一条命令搞定，部署到服务器时只装 `-r requirements.txt`（不必带上测试工具）。

### 加注释说明为什么需要它

```text
# HTTP 请求（第 24 章的接口采集用）
requests>=2.32,<3.0

# 数据处理
pandas>=2.0

# 锁死这个版本：2.5 有个 bug 会导致中文文件名乱码
some-package==2.4.1
```

**这一点很重要**：半年后你看到一个不认识的包，注释能告诉你能不能删。回收第 19.10 节——`pip freeze` 的输出没有注释、还混着间接依赖，**手工维护的 `requirements.txt` 更有价值**。

### 常用约束写法

| 写法 | 含义 | 适合 |
|---|---|---|
| `requests` | 任何版本 | 只有自己用的小脚本 |
| `requests==2.32.5` | 锁死 | **应用**（要可复现） |
| `requests>=2.32` | 不低于 | 库 |
| `requests>=2.32,<3.0` | 区间 | **推荐**：允许小版本更新，挡住可能有破坏性变更的大版本 |
| `requests~=2.32.0` | 兼容版本，等价于 `>=2.32.0,<2.33.0` | 只想拿补丁更新 |

---

## T6.9 查看依赖树

`pip list` 是平的，看不出谁依赖谁。想看树状结构：

```bash
pip install pipdeptree
pipdeptree
```

**什么时候需要**：

- 想知道某个不认识的包是谁装进来的（回收第 19.10 节的间接依赖问题）
- 排查依赖冲突时，需要看清依赖链
- 想删一个包，但不确定有没有别的包在用它

```bash
pipdeptree -r -p urllib3      # 反向查：谁依赖了 urllib3
```

---

## T6.10 什么时候都不该用 `sudo pip`

**看到 `Permission denied` 时，正确的反应不是加 `sudo`，而是意识到"我没在虚拟环境里"。**

| 做法 | 后果 |
|---|---|
| `sudo pip install X` | 装进系统 Python，**可能覆盖系统工具依赖的库，把操作系统搞坏**（某些 Linux 发行版的系统工具是用 Python 写的） |
| `pip install --user X` | 装进用户目录，不会搞坏系统，但**多个项目仍然共用一套包**，回到第 19.1 节那些问题 |
| **激活虚拟环境后 `pip install X`** | ✅ 正确做法 |

**唯一可以接受不用虚拟环境的场合**：装那种"全局命令行工具"性质的东西（比如 `uv` 本身）。这时候推荐用 `pipx`，它专门为此设计——给每个工具建独立环境，但把命令暴露到全局。

---

## T6.11 用 `uv` 替代 pip（★ 可选）

`uv` 是 Astral（就是做 Ruff 那家）用 Rust 写的包管理工具，**比 pip 快一到两个数量级**，而且能同时管理 Python 版本和虚拟环境。

```bash
uv venv                          # 建虚拟环境（比 python -m venv 快）
uv pip install requests          # 命令和 pip 几乎一样
uv pip install -r requirements.txt
uv pip freeze
```

**本书的态度**（和第 19.16 节一致）：

- **先把 `venv` + `pip` 用熟**——它们是内置的，任何环境都有，而且你以后维护别人的老项目一定会遇到
- 等你觉得"装包等得烦"或者"要管好几个 Python 版本"时，再上 `uv`
- `uv` 的命令设计成兼容 pip，学会 pip 就等于学会了 uv 的大部分

> **一个现实情况**：`uv` 在 2025-2026 年普及得很快，PyCharm 2025.3 起已经把它作为默认的环境管理器。所以**知道它的存在是必要的**，但作为新手，不必第一天就换。

---

## 本节小结

| 遇到什么 | 先做什么 |
|---|---|
| 任何 pip 的怪问题 | **确认虚拟环境激活了**（`python -c "import sys; print(sys.executable)"`） |
| 装库失败 | 看报错**最后几行**，按 T6.2 的关键词表对号入座 |
| 需要编译的报错 | **先试换一个稳定的 Python 版本**（别用刚发布的最新版） |
| 想知道包有哪些版本 | 故意装一个不存在的版本，pip 会列出全部 |
| `Permission denied` | 不是加 `sudo`，是去激活虚拟环境 |
| 升级完出怪问题 | `pip check` |
| 不认识的包是谁装的 | `pipdeptree -r -p 包名` |

**一句话记住**：**用 `python -m pip`、在虚拟环境里、报错读最后几行。** 这三条能解决九成的 pip 问题。

> 部分内容参考 [pip 官方文档](https://pip.pypa.io/) 与 [uv 官方文档](https://docs.astral.sh/uv/)，已改写以符合内容许可要求。
