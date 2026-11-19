#!/usr/bin/env python3
"""Ghi các phiên Claude Code đang mở vào ~/.claude/open-sessions.json để claude-restore mở lại sau khi tắt máy.
Chạy từ hook:  session-registry.py start  (SessionStart)  |  session-registry.py end  (SessionEnd)
- start: thêm/cập nhật phiên. Trên Mac/Linux bỏ qua phiên không có terminal (claude -p, --bg).
- end:   chỉ xoá phiên khi thoát có chủ ý (/exit, Ctrl+D, /clear, logout). Đóng cửa sổ terminal, tắt máy ngang
         -> phiên vẫn còn trong danh sách = cần mở lại.
- cwd lưu là thư mục MỞ phiên (nơi `claude --resume` tìm được phiên), không phải thư mục Claude đã cd tới.
Mỗi lần chạy ghi một dòng vào ~/.claude/open-sessions.log để dò lỗi.
Không bao giờ làm hỏng phiên: mọi lỗi đều bị bỏ qua, luôn thoát 0. Chạy được trên macOS, Linux, Windows.
"""
import json, os, subprocess, sys, time

WIN = os.name == 'nt'
REG = os.path.join(os.path.expanduser('~'), '.claude', 'open-sessions.json')
LOG = REG[:-5] + '.log'
DELIBERATE = {'prompt_input_exit', 'clear', 'logout', 'resume'}   # /exit, Ctrl+D, /clear, /logout, /resume sang phiên khác; đóng cửa sổ = 'other' → giữ


def log(msg):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 200_000:
            os.replace(LOG, LOG + '.1')
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
    except Exception:
        pass


def launch_cwd(transcript):
    """thư mục mở phiên = cwd ở dòng đầu của transcript"""
    try:
        with open(transcript, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i > 200:
                    break
                if '"cwd"' in line:
                    c = json.loads(line).get('cwd')
                    if c:
                        return c
    except Exception:
        pass
    return None


def win_procs():
    """{pid: (ppid, tên exe)} trên Windows, không cần cài thêm gì"""
    import ctypes
    from ctypes import wintypes

    class PE(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * 260)]
    k = ctypes.windll.kernel32
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE)]
    k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE)]
    snap = k.CreateToolhelp32Snapshot(2, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    out = {}
    ok = k.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        out[pe.th32ProcessID] = (pe.th32ParentProcessID, pe.szExeFile.lower())
        ok = k.Process32NextW(snap, ctypes.byref(pe))
    k.CloseHandle(snap)
    return out


def claude_pid():
    """đi ngược cây tiến trình tới tiến trình claude (hook chạy qua shell nên cha trực tiếp là shell)"""
    pid = os.getppid()
    if WIN:
        procs = win_procs()
        node = None
        for _ in range(10):
            if pid not in procs:
                break
            ppid, name = procs[pid]
            if 'claude' in name:
                return pid
            if node is None and name == 'node.exe':   # cài bằng npm: claude chạy trong node.exe
                node = pid
            pid = ppid
        return node
    for _ in range(8):
        try:
            out = subprocess.run(['ps', '-o', 'ppid=,comm=', '-p', str(pid)],
                                 capture_output=True, text=True, timeout=2).stdout.strip()
        except Exception:
            return None
        if not out:
            return None
        ppid, comm = out.split(None, 1)
        if 'claude' in os.path.basename(comm).lower():
            return pid
        pid = int(ppid)
    return None


def has_terminal(pid):
    if WIN:
        return True      # Windows không có tty; phiên chạy nền vẫn bị xoá khi kết thúc (SessionEnd)
    try:
        t = subprocess.run(['ps', '-o', 'tty=', '-p', str(pid)], capture_output=True, text=True, timeout=2).stdout.strip()
        return t not in ('', '??')
    except Exception:
        return False


class Lock:
    def __enter__(self):
        self.f = open(REG + '.lock', 'a+')
        if WIN:
            import msvcrt
            for _ in range(50):
                try:
                    self.f.seek(0)
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                    self.locked = True
                    break
                except OSError:
                    time.sleep(0.1)
        else:
            import fcntl
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        try:
            if WIN and getattr(self, 'locked', False):
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.f.close()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    sid = data.get('session_id')
    if not sid or mode not in ('start', 'end'):
        return
    os.makedirs(os.path.dirname(REG), exist_ok=True)
    with Lock():
        try:
            with open(REG, encoding='utf-8') as f:
                reg = json.load(f)
        except Exception:
            reg = {}
        if mode == 'start':
            pid = claude_pid()
            src = data.get('source', '')
            if not pid or not has_terminal(pid):
                log(f'start {sid[:8]} {src} bỏ qua (pid={pid}, không có terminal)')
                return
            old = reg.get(sid, {})
            now = time.strftime('%Y-%m-%d %H:%M')
            tr = data.get('transcript_path', '')
            cwd = old.get('cwd') or (data.get('cwd') if src in ('startup', 'resume') else None) \
                or launch_cwd(tr) or data.get('cwd') or os.getcwd()
            reg[sid] = {'id': sid, 'cwd': cwd, 'pid': pid, 'source': src,
                        'first': old.get('first') or now, 't': now, 'transcript': tr}
            log(f'start {sid[:8]} {src} pid={pid} cwd={cwd}')
        else:
            reason = data.get('reason', '')
            if reason in DELIBERATE:
                reg.pop(sid, None)
                log(f'end {sid[:8]} {reason}: xoá khỏi danh sách')
            else:
                if sid in reg:
                    reg[sid]['closed'] = reason or 'unknown'
                log(f'end {sid[:8]} {reason or "?"}: giữ lại để mở lại')
        cutoff = time.strftime('%Y-%m-%d', time.localtime(time.time() - 14 * 86400))
        reg = {k: v for k, v in reg.items() if v.get('t', '9') >= cutoff}   # bỏ phiên quá 14 ngày
        tmp = REG + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(reg, f, ensure_ascii=False, indent=1)
        os.replace(tmp, REG)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
