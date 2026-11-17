#!/usr/bin/env python3
"""Ghép vào ~/.claude/settings.json: bật Remote Control cho mọi phiên + 2 hook SessionStart/SessionEnd.
Giữ nguyên mọi thứ khác, sao lưu file cũ trước khi ghi. Chạy lại nhiều lần không bị nhân đôi hook.
  merge_settings.py <python> <đường dẫn session-registry.py>
  merge_settings.py --remove          gỡ hook + dòng remoteControlAtStartup
"""
import json, os, shutil, sys, time

path = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
os.makedirs(os.path.dirname(path), exist_ok=True)

s = {}
if os.path.exists(path):
    with open(path, encoding='utf-8') as f:
        txt = f.read().strip()
    if txt:
        s = json.loads(txt)   # file hỏng thì dừng ở đây, không ghi đè
    bak = path + '.bak-' + time.strftime('%Y%m%d-%H%M%S')
    shutil.copy2(path, bak)
    print('Đã sao lưu settings cũ:', bak)

hooks = s.setdefault('hooks', {})
for ev in ('SessionStart', 'SessionEnd'):
    groups = []
    for g in hooks.get(ev, []):
        g = dict(g)
        g['hooks'] = [h for h in g.get('hooks', []) if 'session-registry.py' not in h.get('command', '')]
        if g['hooks']:
            groups.append(g)
    hooks[ev] = groups

if sys.argv[1:2] == ['--remove']:
    s.pop('remoteControlAtStartup', None)
    for ev in ('SessionStart', 'SessionEnd'):
        if not hooks[ev]:
            hooks.pop(ev)
    if not hooks:
        s.pop('hooks')
else:
    py, reg = (p.replace('\\', '/') for p in sys.argv[1:3])
    s['remoteControlAtStartup'] = True
    for ev, mode in (('SessionStart', 'start'), ('SessionEnd', 'end')):
        hooks[ev].append({'hooks': [{'type': 'command', 'command': f'"{py}" "{reg}" {mode}', 'timeout': 10}]})

tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(s, f, ensure_ascii=False, indent=2)
    f.write('\n')
os.replace(tmp, path)
print('Đã cập nhật', path)
