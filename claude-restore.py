#!/usr/bin/env python3
"""Mở lại các phiên Claude Code còn dang dở sau khi tắt máy: mỗi phiên một tab mới, chạy `claude --resume <id>`.
Danh sách do hook session-registry.py ghi ở ~/.claude/open-sessions.json.
Tab mở ra: macOS dùng iTerm (không có thì Terminal), Windows dùng Windows Terminal (không có thì cửa sổ cmd).

  claude-restore              liệt kê, hỏi rồi mở
  claude-restore -y           mở hết, không hỏi
  claude-restore --list       chỉ liệt kê
  claude-restore --forget 2,3 bỏ phiên số 2, 3 khỏi danh sách
"""
import json, os, shlex, shutil, subprocess, sys

WIN = os.name == 'nt'
REG = os.path.join(os.path.expanduser('~'), '.claude', 'open-sessions.json')

if WIN:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def win_procs():
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
        out[pe.th32ProcessID] = pe.szExeFile.lower()
        ok = k.Process32NextW(snap, ctypes.byref(pe))
    k.CloseHandle(snap)
    return out


_PROCS = None


def alive(pid):
    global _PROCS
    if not pid:
        return False
    try:
        if WIN:
            if _PROCS is None:
                _PROCS = win_procs()
            name = _PROCS.get(int(pid), '')
            return 'claude' in name or name == 'node.exe'
        out = subprocess.run(['ps', '-o', 'comm=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        return 'claude' in os.path.basename(out).lower()
    except Exception:
        return False


def title(s):
    """tên phiên (/rename) nếu có, không thì câu đầu tiên người dùng gõ"""
    p = s.get('transcript')
    if not p or not os.path.exists(p):
        return '(không thấy transcript)'
    name, first = None, None
    try:
        with open(p, encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get('type') in ('custom-title', 'title'):
                    name = d.get('customTitle') or d.get('title') or name
                if first is None and d.get('type') == 'user' and not d.get('isMeta'):
                    c = (d.get('message') or {}).get('content')
                    if isinstance(c, list):
                        c = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
                    if isinstance(c, str) and c.strip() and not c.lstrip().startswith('<'):
                        first = ' '.join(c.split())
    except Exception:
        pass
    t = name or first or '(chưa có lời nhắn)'
    return t[:70] + ('…' if len(t) > 70 else '')


def load():
    try:
        with open(REG, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save(reg):
    tmp = REG + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, REG)


def open_tab_mac(cwd, sid):
    cmd = f'cd {shlex.quote(cwd)} && claude --resume {sid}'
    if os.path.isdir('/Applications/iTerm.app'):
        osa = f'''
tell application "iTerm"
  activate
  if (count of windows) = 0 then
    create window with default profile
  else
    tell current window to create tab with default profile
  end if
  tell current session of current window to write text {json.dumps(cmd)}
end tell'''
    else:
        osa = f'''
tell application "Terminal"
  activate
  do script {json.dumps(cmd)}
end tell'''
    subprocess.run(['osascript', '-e', osa], check=True)


def open_tab_win(cwd, sid):
    wt = shutil.which('wt')
    if wt:
        subprocess.Popen([wt, '-w', '0', 'nt', '-d', cwd, 'powershell', '-NoExit', '-Command',
                          f'claude --resume {sid}'])
    else:
        subprocess.Popen(['cmd', '/c', 'start', '', 'cmd', '/k', f'claude --resume {sid}'], cwd=cwd)


def open_tab_linux(cwd, sid):
    cmd = f'cd {shlex.quote(cwd)} && claude --resume {sid}; exec $SHELL'
    for term in (['gnome-terminal', '--tab', '--', 'bash', '-c', cmd], ['x-terminal-emulator', '-e', 'bash', '-c', cmd]):
        if shutil.which(term[0]):
            subprocess.Popen(term)
            return
    print(f'     tự mở: cd {shlex.quote(cwd)} && claude --resume {sid}')


def main():
    a = sys.argv[1:]
    reg = load()
    rows = sorted(reg.values(), key=lambda s: s.get('t', ''), reverse=True)
    todo = [s for s in rows if not alive(s.get('pid'))]
    if '--forget' in a:
        idx = {int(x) for x in a[a.index('--forget') + 1].split(',') if x.strip().isdigit()}
        for i, s in enumerate(todo, 1):
            if i in idx:
                reg.pop(s['id'], None)
        save(reg)
        print('Đã bỏ', len(idx), 'phiên khỏi danh sách.')
        return
    running = len(rows) - len(todo)
    if not todo:
        print('Không có phiên nào cần mở lại.' + (f' ({running} phiên đang chạy)' if running else ''))
        return
    home = os.path.expanduser('~')
    print(f'Phiên cần mở lại ({len(todo)}' + (f', bỏ qua {running} đang chạy' if running else '') + '):')
    for i, s in enumerate(todo, 1):
        print(f'  {i}. [{s.get("t", "")}] {s["cwd"].replace(home, "~")}\n     {title(s)}')
    if '--list' in a:
        return
    pick = list(range(1, len(todo) + 1))
    if '-y' not in a:
        ans = input('\nMở tất cả? [Enter = có / n = không / số, vd 1,3]: ').strip().lower()
        if ans in ('n', 'no', 'k', 'không'):
            return
        if ans:
            pick = [int(x) for x in ans.replace(' ', '').split(',') if x.isdigit() and 1 <= int(x) <= len(todo)]
    opener = open_tab_win if WIN else open_tab_mac if sys.platform == 'darwin' else open_tab_linux
    for i in pick:
        s = todo[i - 1]
        if not os.path.isdir(s['cwd']):
            print(f'  bỏ {i}: thư mục không còn ({s["cwd"]})')
            continue
        opener(s['cwd'], s['id'])
        print(f'  đã mở {i}')


if __name__ == '__main__':
    main()
