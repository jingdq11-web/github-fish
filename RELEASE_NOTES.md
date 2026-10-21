## 这是什么

让桌面宠物替你看 GitHub。

有人 star 你的仓库，她跳舞；CI 挂了，她垂头叹气；有人提 issue，她凑过来念给你听。

![demo](https://github.com/jingdq11-web/whale-girl-github/raw/master/docs/demo.jpg)

## v1.0.1 修了什么

上一版有个不好受的毛病：**它会假装还在工作。**

| 问题 | 现在 |
|---|---|
| Token 失效后一直拿旧卡去敲门，日志只写「错误 401」，你根本不知道门卫已经瞎了 | 发现 401 就丢掉旧卡、换一张重试；两张都不行就明确写「请重新登录 gh」 |
| 撞上速率限制时，提示永远怪「你没配 Token」，其实可能只是这会儿请求太密 | 说清楚是被限流，以及还有几分钟恢复 |
| 桌宠还没加载完模型就去连，连不上就退化成只会写日志的哑巴 | 先在门口等一会儿（默认 30 秒），等它起来再连 |
| 桌宠没开时得自己去开，回来再启动一遍 | 配了 `pet.app_exe` 就会自动把它叫起来 |
| 配置里没填 Token 就只能吃每小时 60 次的匿名额度 | 本机装了 GitHub CLI 并登录过，就自动借它的 Token，**不用手填** |
| 备份配置文件时，`config.json.bak` 不在忽略规则里，明文 Token 差一步就传上来 | 已忽略 `config.json.*` 和 `*.bak` |

## 下载哪个

| 文件 | 适合谁 |
|---|---|
| **github-fish.exe** | 不想装 Python 的人。双击即用 |
| **Source code (zip)** | 想改代码、或者不信任 exe 的人 |

## 用 exe 的话

1. 下载 `github-fish.exe`，放到一个固定文件夹（比如 `D:\github-fish\`）
2. 双击运行一次 —— 它会在同目录生成 `config.json`，然后自动退出
3. 用记事本打开 `config.json`，填上：
   - `github.user`：你的 GitHub 用户名
   - `github.repos`：要监控的仓库，格式 `用户名/仓库名`
   - `pet.bridge_exe`：你的桌宠 MCP 桥接程序路径
   - `pet.app_exe`：可选。桌宠本体程序，填了就会自动帮你打开它
   - `github.token`：可选。**留空也行** —— 装了 GitHub CLI 并登录过，会自动借用
4. 再双击运行 —— 启动成功时桌宠会开口说「门卫上班了」

**exe 是单文件、无窗口的后台程序**，运行后不会弹出任何界面。
想看它在干什么，看同目录的 `github-fish.log`。

## 功能

- 监控 star、fork、issue、PR、release、CI 状态
- 首次运行只建立基线，不会把积压的历史通知一次性全喊出来
- 状态持久化，关掉重开不会重复播报
- 支持静默时段
- 事件与动作的对应关系全部可配
- 零第三方依赖（源码版）

## 前置要求

需要先装好 [蓝色大肥鱼](https://github.com/Bai-Cute/big-blue-fish-desktop-pet)（或任何支持 `say` / `play_action` 的 MCP 桌宠），
并在桌宠设置里开启「MCP 接口」。

本项目是独立第三方程序，不包含原项目的任何代码或素材。

## 已知限制

- 不填 Token 且本机没有登录过 GitHub CLI 时，API 限制为每小时 60 次请求
- 仅支持 Windows（exe 版）
- 桌宠一直没起来时，程序会等一段时间后继续运行，只是不播报

## 关于你的凭据

本项目**不收集、不上传任何 Token**。

- `config.json` 已被 `.gitignore` 排除，连同它的备份一起
- 配置文件里留空 Token 时，程序只在本机内存里向 GitHub CLI 借用，不写回文件
- 仓库历史里从未出现过任何 Token（可用 `git log -S'gho_'` 自行验证）

## License

MIT
