# github-fish 🐟

**让你的桌面宠物替你看 GitHub。**

有人 star 你的仓库，她跳舞；CI 挂了，她垂头叹气；有人提了 issue，她凑过来告诉你。

你写代码的时候，桌角有个东西真的在"关心"你的进度。

> 这是给 [蓝色大肥鱼](https://github.com/Bai-Cute/big-blue-fish-desktop-pet) 写的，
> 但因为走的是标准 MCP 协议，任何支持 `say` / `play_action` 的桌宠都能接。

---

## 它长什么样

```
[14:32:08] 播报: KirisakiChitoge star 了 you/github-fish ！
[14:41:55] 播报: some-user 在 you/github-fish 提了新 issue #3：README 里的截图挂了
[15:02:11] 播报: you/github-fish 的 CI 挂了（build / main）
```

与此同时，你的桌宠会说出来，并做一个对应动作。

---

## 特性

- **零第三方依赖** — 只用 Python 标准库，`pip install` 都不用跑
- **首次运行不炸屏** — 只建立基线，不会把你积压的 50 条历史通知一次性全喊出来
- **状态持久化** — 关掉重开不会重复播报同一条
- **静默时段** — 设好时间段，半夜没人 star 你也能睡个好觉
- **CI 状态跟踪** — 记录每个仓库最近一次 workflow 的结论，只在状态**变化**时播报
- **动作可配** — 什么事件配什么动作，全在配置文件里改，不用碰代码

---

## 快速开始

### 1. 确认桌宠在跑

以蓝色大肥鱼为例：先打开桌宠，右键 → 设置 → **Agent 与 MCP** → 勾上「开启 MCP 接口」。

### 2. 生成配置

```bash
python github_fish.py
```

第一次运行会自动从 `config.example.json` 生成 `config.json`，然后退出。

### 3. 填配置

打开 `config.json`，至少改这两项：

```json
"user": "你的GitHub用户名",
"repos": ["你的用户名/仓库名"]
```

想要私有仓库或更高 API 速率？填 `token`（见下方「关于 token」）。

### 4. 测试连接

```bash
python github_fish.py --test
```

桌宠应该会说话并做个动作。没反应就检查 `bridge_exe` 路径对不对。

### 5. 跑起来

```bash
python github_fish.py
```

第一次运行会建立基线，之后有新事件才会播报。

---

## 配置说明

| 字段 | 说明 |
|---|---|
| `github.token` | Personal Access Token。留空也能用，但每小时只有 60 次请求 |
| `github.user` | 你的用户名，会监控你的公开事件流 |
| `github.repos` | 要监控的仓库列表，格式 `owner/repo` |
| `github.poll_interval` | 轮询间隔（秒），最低 30，默认 90 |
| `github.watch` | 每种事件是否播报，`push` 默认关（太吵） |
| `pet.bridge_exe` | 桌宠 MCP 桥接程序路径 |
| `pet.quiet_hours` | 静默时段，如 `[23, 8]` 表示 23 点到次日 8 点只记录不播报 |
| `pet.speak_prefix` | 每句话的前缀，比如填 `"乐，"` 就是"乐，有人 star 了！" |
| `actions` | 事件类型 → 动作名 |

### 关于 token

不填也能跑，但 GitHub 对未认证请求限制 **每小时 60 次**。如果你监控多个仓库、间隔又短，很容易撞上限。

生成方式：GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → 只勾 `public_repo` 读权限就够（私有仓库才需要 `repo`）。

---

## 支持哪些桌宠

只要满足这两个条件：

1. 提供 MCP stdio 桥接程序
2. 实现了 `say`（说话）和 `play_action`（播动作）两个工具

`bridge_exe` 指向那个桥接程序就行。如果动作名不一样，改 `actions` 里的值即可。

---

## 常见问题

**Q：一直提示 MCP 握手失败？**
A：桌宠没启动，或者设置里没开 MCP 接口。桥接程序不会自己拉起桌宠。

**Q：动作没反应，但话说了？**
A：动作名对不上。用桌宠的 `list_actions` 查一下准确名称，然后改 `actions` 里的值。

**Q：第一次运行什么都没播报？**
A：正常。首次运行只建立基线，这是故意的。

**Q：能开机自启吗？**
A：Windows 上把启动命令丢进 `shell:startup` 目录即可（做一个 `.vbs` 用 `pythonw.exe` 静默启动）。

---

## 路线图

- [ ] GitHub App 方式认证，免 token
- [ ] 贡献图情绪联动：绿格子多就活泼，断更就蔫
- [ ] 桌面通知兜底（桌宠没开时用系统通知）
- [ ] 多桌宠适配层

---

## License

MIT
