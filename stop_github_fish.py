#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
停止 github-fish。
通过单实例锁占用的端口找到进程，不误杀其他 Python 程序。
"""

import os
import subprocess
import sys

LOCK_PORT = 47822
NO_CONSOLE = 0
if os.name == "nt":
    NO_CONSOLE = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP


def find_pid():
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             encoding="gbk", errors="replace", timeout=10,
                             creationflags=NO_CONSOLE)
    except Exception as e:
        print("查询端口失败: %s" % e)
        return None

    for line in out.stdout.splitlines():
        f = line.split()
        if len(f) >= 5 and f[0].upper() == "TCP" and "LISTENING" in line.upper():
            if f[1].endswith(":%d" % LOCK_PORT):
                try:
                    return int(f[-1])
                except ValueError:
                    pass
    return None


def main():
    pid = find_pid()
    if not pid:
        print("github-fish 没有在运行")
        return 0

    r = subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, text=True, encoding="gbk",
                       errors="replace", creationflags=NO_CONSOLE)
    if r.returncode == 0:
        print("已停止 github-fish (PID %d)" % pid)
        return 0
    print("停止失败:", (r.stderr or r.stdout).strip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
