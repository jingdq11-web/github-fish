#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
github-fish — 让你的桌面宠物替你看 GitHub
================================================

它做一件很简单的事：轮询你的 GitHub，一旦有人 star、开 issue、提 PR，
或者 CI 挂了，就让桌面上的宠物开口告诉你，顺便做个动作。

设计目标：
  * 零第三方依赖，只用 Python 标准库
  * 通过 MCP 协议驱动宠物，兼容任何实现了 say / play_action 的桌宠
  * 首次运行只建立基线，不会把你积压的历史通知一次性全喊出来

用法：
  python github_fish.py            # 前台运行
  python github_fish.py --once     # 只轮询一次，方便调试
  python github_fish.py --test     # 测试宠物连接，不做轮询

配置文件：同目录下 config.json（首次运行会从 config.example.json 生成）
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
EXAMPLE_FILE = os.path.join(APP_DIR, "config.example.json")
STATE_FILE = os.path.join(APP_DIR, "state.json")
LOG_FILE = os.path.join(APP_DIR, "github-fish.log")

# Windows 上让子进程彻底脱离控制台。
# 注意：CREATE_NO_WINDOW 在 Windows 11（默认终端为 Windows Terminal）下会被
# Terminal 接管并弹出标签页，实测无效，必须用 DETACHED_PROCESS。
NO_CONSOLE = 0
if os.name == "nt":
    NO_CONSOLE = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

DEFAULT_CONFIG = {
    "github": {
        "token": "",
        "user": "",
        "repos": [],
        "poll_interval": 90,
        "watch": {
            "star": True,
            "fork": True,
            "issue": True,
            "pull_request": True,
            "release": True,
            "push": False,
            "ci": True,
        },
    },
    "pet": {
        "enabled": True,
        "bridge_exe": r"D:\deepseek\蓝色大肥鱼\BigBlueFish.Mcp.exe",
        "quiet_hours": [],
        "speak_prefix": "",
    },
    "actions": {
        "star": "工作状态-雀跃庆祝",
        "fork": "点击回应-开心跃动",
        "issue": "工作状态-思考冒泡",
        "pull_request": "工作状态-清点归档",
        "release": "放烟花",
        "ci_fail": "工作状态-垂头叹气冒汗",
        "ci_ok": "工作状态-雀跃庆祝",
    },
}

# 事件类型 -> 配置里的类别
EVENT_KIND = {
    "WatchEvent": "star",
    "ForkEvent": "fork",
    "IssuesEvent": "issue",
    "PullRequestEvent": "pull_request",
    "ReleaseEvent": "release",
    "PushEvent": "push",
}


def log(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ------------------------------------------------------------------ 配置与状态
def load_config():
    if not os.path.isfile(CONFIG_FILE):
        if os.path.isfile(EXAMPLE_FILE):
            with open(EXAMPLE_FILE, encoding="utf-8") as f:
                text = f.read()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(text)
            log("已从 config.example.json 生成 config.json，请填写 token 和用户名后重跑")
        else:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            log("已生成默认 config.json")
        sys.exit(0)

    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)

    # 补齐缺失字段
    for section, defaults in DEFAULT_CONFIG.items():
        if isinstance(defaults, dict):
            cfg.setdefault(section, {})
            for k, v in defaults.items():
                if isinstance(v, dict):
                    cfg[section].setdefault(k, {})
                    for kk, vv in v.items():
                        cfg[section][k].setdefault(kk, vv)
                else:
                    cfg[section].setdefault(k, v)
        else:
            cfg.setdefault(section, defaults)
    return cfg


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"seen_events": [], "ci_status": {}, "initialized": False}


def save_state(state):
    # 只保留最近 500 条事件 id，避免文件无限增长
    if len(state.get("seen_events", [])) > 500:
        state["seen_events"] = state["seen_events"][-500:]
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


# ------------------------------------------------------------------ 宠物客户端
class PetClient:
    """通过 MCP 的 stdio 桥接程序控制桌面宠物。"""

    def __init__(self, bridge_exe):
        self.bridge_exe = bridge_exe
        self.proc = None
        self.lock = threading.Lock()
        self.next_id = 1
        self.responses = {}
        self.alive = False

    def start(self):
        if not os.path.isfile(self.bridge_exe):
            log("找不到桌宠桥接程序: %s" % self.bridge_exe)
            return False
        try:
            self.proc = subprocess.Popen(
                [self.bridge_exe],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                creationflags=NO_CONSOLE)
        except Exception as e:
            log("启动桥接失败: %s" % e)
            return False

        threading.Thread(target=self._read_loop, daemon=True).start()
        result = self._call("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "github-fish", "version": "1.0"},
        }, timeout=20)
        if not result:
            log("MCP 握手失败（桌宠可能没启动，或没开启 MCP 接口）")
            return False
        self._notify({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.alive = True
        log("已连接桌宠: %s" % result.get("serverInfo", {}).get("name", "?"))
        return True

    def _read_loop(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                if "id" in msg:
                    self.responses[msg["id"]] = msg
        except Exception:
            pass
        self.alive = False

    def _write(self, obj):
        with self.lock:
            self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()

    def _notify(self, obj):
        try:
            self._write(obj)
        except Exception:
            pass

    def _call(self, method, params, timeout=25):
        rid = self.next_id
        self.next_id += 1
        try:
            self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        except Exception as e:
            log("发送请求失败: %s" % e)
            return None
        end = time.time() + timeout
        while time.time() < end:
            if rid in self.responses:
                return self.responses.pop(rid).get("result")
            time.sleep(0.05)
        return None

    def tool(self, name, args=None, timeout=25):
        r = self._call("tools/call", {"name": name, "arguments": args or {}}, timeout)
        if not r:
            return None
        try:
            return json.loads(r["content"][0]["text"])
        except Exception:
            return r

    def say(self, text):
        if not self.alive:
            return False
        return self.tool("say", {"text": text}) is not None

    def play(self, action):
        if not self.alive or not action:
            return False
        return self.tool("play_action", {"action": action}) is not None


# ------------------------------------------------------------------ GitHub API
class GitHub:
    API = "https://api.github.com"

    def __init__(self, token=""):
        self.token = token or ""

    def _get(self, path):
        url = self.API + path
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "github-fish")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                log("GitHub API 403（可能是速率限制，未配置 token 时每小时只有 60 次）")
            elif e.code == 404:
                log("GitHub API 404: %s" % path)
            else:
                log("GitHub API 错误 %d: %s" % (e.code, path))
            return None
        except Exception as e:
            log("请求 GitHub 失败: %s" % e)
            return None

    def user_events(self, user):
        data = self._get("/users/%s/events?per_page=50" % user)
        return data if isinstance(data, list) else []

    def repo_events(self, repo):
        data = self._get("/repos/%s/events?per_page=30" % repo)
        return data if isinstance(data, list) else []

    def latest_ci(self, repo):
        """返回最近一次 workflow run 的 (状态, 结论, 名称)。"""
        data = self._get("/repos/%s/actions/runs?per_page=1" % repo)
        if not data or not data.get("workflow_runs"):
            return None
        run = data["workflow_runs"][0]
        return {
            "id": run.get("id"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "name": run.get("name") or "CI",
            "branch": run.get("head_branch") or "",
        }


# ------------------------------------------------------------------ 播报
def build_message(kind, event, repo):
    actor = (event.get("actor") or {}).get("login", "有人")
    payload = event.get("payload") or {}

    if kind == "star":
        n = event.get("repo", {}).get("stargazers_count")
        return "%s star 了 %s ！" % (actor, repo)
    if kind == "fork":
        return "%s 把 %s fork 走了" % (actor, repo)
    if kind == "issue":
        action = payload.get("action", "opened")
        num = (payload.get("issue") or {}).get("number", "")
        title = ((payload.get("issue") or {}).get("title") or "")[:40]
        if action == "opened":
            return "%s 在 %s 提了新 issue #%s：%s" % (actor, repo, num, title)
        if action == "closed":
            return "%s 关掉了 %s 的 issue #%s" % (actor, repo, num)
        return None
    if kind == "pull_request":
        action = payload.get("action", "opened")
        num = (payload.get("pull_request") or {}).get("number", "")
        if action == "opened":
            return "%s 给 %s 提了 PR #%s" % (actor, repo, num)
        if action == "closed":
            merged = (payload.get("pull_request") or {}).get("merged")
            if merged:
                return "%s 的 PR #%s 被合并进 %s 了！" % (actor, num, repo)
            return "%s 关掉了 %s 的 PR #%s" % (actor, repo, num)
        return None
    if kind == "release":
        tag = (payload.get("release") or {}).get("tag_name", "")
        return "%s 给 %s 发了新版本 %s" % (actor, repo, tag)
    if kind == "push":
        commits = len(payload.get("commits") or [])
        if commits >= 3:
            return "%s 往 %s 推了 %d 个提交" % (actor, repo, commits)
        return None
    return None


class Watcher:
    def __init__(self, cfg, pet):
        self.cfg = cfg
        self.pet = pet
        self.gh = GitHub(cfg["github"].get("token", ""))
        self.state = load_state()
        self.watch = cfg["github"].get("watch", {})
        self.actions = cfg.get("actions", {})

    def in_quiet_hours(self):
        hours = self.cfg["pet"].get("quiet_hours") or []
        if len(hours) != 2:
            return False
        now = time.localtime().tm_hour
        start, end = hours
        if start <= end:
            return start <= now < end
        return now >= start or now < end

    def announce(self, text, kind):
        if not text:
            return
        log("播报: %s" % text)
        if self.in_quiet_hours():
            log("（静默时段，只记录不播报）")
            return
        prefix = self.cfg["pet"].get("speak_prefix", "")
        if self.pet and self.cfg["pet"].get("enabled", True):
            self.pet.say(prefix + text)
            self.pet.play(self.actions.get(kind, ""))

    def collect_events(self):
        """拉取所有关注来源的事件，返回 (repo_name, event) 列表。"""
        items = []
        user = self.cfg["github"].get("user", "")
        if user:
            for ev in self.gh.user_events(user):
                repo = (ev.get("repo") or {}).get("name", "")
                items.append((repo, ev))
        for repo in self.cfg["github"].get("repos", []):
            for ev in self.gh.repo_events(repo):
                items.append((repo, ev))
        return items

    def poll_once(self):
        items = self.collect_events()
        if not items:
            # 即使这次没拉到任何事件，也要把 initialized 落盘。
            # 否则下次真来事件时会被当成"首次运行"整批跳过。
            if not self.state.get("initialized"):
                self.state["initialized"] = True
                save_state(self.state)
                log("首次运行，暂无事件，已记录基线")
            return 0

        first_run = not self.state.get("initialized")
        seen = set(self.state.get("seen_events", []))
        announced = 0

        # 事件按时间正序处理，先发生的先说
        items.sort(key=lambda x: x[1].get("created_at", ""))

        for repo, ev in items:
            eid = ev.get("id")
            if not eid or eid in seen:
                continue
            seen.add(eid)

            kind = EVENT_KIND.get(ev.get("type", ""))
            if not kind or not self.watch.get(kind, False):
                continue

            if first_run:
                continue  # 首次运行只记基线，不播报历史

            text = build_message(kind, ev, repo)
            if text:
                self.announce(text, kind)
                announced += 1
                time.sleep(3)  # 多条消息之间留点间隔，别把宠物刷爆

        self.state["seen_events"] = list(seen)
        self.state["initialized"] = True
        save_state(self.state)

        if first_run:
            log("首次运行，已建立基线（%d 条历史事件，不播报）" % len(seen))
        return announced

    def check_ci(self):
        if not self.watch.get("ci", False):
            return 0
        announced = 0
        for repo in self.cfg["github"].get("repos", []):
            run = self.gh.latest_ci(repo)
            if not run or run["status"] != "completed":
                continue
            last = self.state.get("ci_status", {}).get(repo)
            cur = "%s:%s" % (run["id"], run["conclusion"])
            if last == cur:
                continue
            self.state.setdefault("ci_status", {})[repo] = cur

            if not self.state.get("initialized"):
                continue

            if run["conclusion"] == "failure":
                self.announce("%s 的 CI 挂了（%s / %s）" % (repo, run["name"], run["branch"]), "ci_fail")
                announced += 1
            elif run["conclusion"] == "success" and last:
                self.announce("%s 的 CI 过了！" % repo, "ci_ok")
                announced += 1
            time.sleep(2)

        save_state(self.state)
        return announced


# ------------------------------------------------------------------ 入口
def single_instance():
    """用本地端口做单实例锁，避免重复启动。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 47822))
        s.listen(1)
        return s
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description="让桌面宠物替你看 GitHub")
    ap.add_argument("--once", action="store_true", help="只轮询一次")
    ap.add_argument("--test", action="store_true", help="测试宠物连接")
    args = ap.parse_args()

    cfg = load_config()

    if not cfg["github"].get("user") and not cfg["github"].get("repos"):
        log("config.json 里既没有 github.user 也没有 github.repos，先填一个")
        return 1

    pet = None
    if cfg["pet"].get("enabled", True):
        pet = PetClient(cfg["pet"]["bridge_exe"])
        if not pet.start():
            log("宠物连接失败，将只打印到控制台（不播报）")
            pet = None

    if args.test:
        if pet:
            pet.say("github-fish 连接成功，我准备好替你看仓库了！")
            pet.play(cfg.get("actions", {}).get("star", ""))
            log("测试播报已发送")
        else:
            log("宠物未连接，测试失败")
        return 0

    watcher = Watcher(cfg, pet)

    if args.once:
        n = watcher.poll_once()
        n += watcher.check_ci()
        log("单次轮询完成，播报 %d 条" % n)
        return 0

    lock = single_instance()
    if not lock:
        log("已有一个 github-fish 在运行，退出")
        return 0

    interval = max(30, int(cfg["github"].get("poll_interval", 90)))
    log("开始监控，轮询间隔 %d 秒。Ctrl+C 退出。" % interval)
    try:
        while True:
            try:
                watcher.poll_once()
                watcher.check_ci()
            except Exception as e:
                log("轮询出错: %s" % e)
            time.sleep(interval)
    except KeyboardInterrupt:
        log("已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
