## 这是什么

让桌面宠物替你看 GitHub。

有人 star 你的仓库，她跳舞；CI 挂了，她垂头叹气；有人提 issue，她凑过来念给你听。

![demo](https://github.com/jingdq11-web/github-fish/raw/master/docs/demo.jpg)

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

- 未配置 GitHub Token 时，API 限制为每小时 60 次请求。监控多个仓库建议填 Token
- 仅支持 Windows（exe 版）
- 桌宠没开时程序会继续运行，只是不播报

## License

MIT
