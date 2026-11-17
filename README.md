# claude-session-restore

Mở lại các phiên Claude Code đang dở sau khi máy tắt, và bật sẵn Remote Control cho mọi phiên.

**Cách hoạt động**
- Hook `SessionStart` ghi phiên vừa mở vào `~/.claude/open-sessions.json`. Hook `SessionEnd` xoá phiên khi bạn thoát bình thường (`/exit`, Ctrl+D).
- Nếu máy tắt đột ngột, phiên vẫn nằm trong danh sách. Gõ `claude-restore` để mở lại mỗi phiên trong một tab mới bằng `claude --resume <id>`.
- `remoteControlAtStartup: true` có tác dụng như bật "Enable Remote Control for all sessions" trong `/config`.

Lịch sử phiên chỉ lưu trên máy đã chạy phiên đó, nên mỗi máy chỉ mở lại được phiên của chính nó.

## Cài đặt

Cần Python 3 và Claude Code.

**macOS / Linux**
```bash
git clone https://github.com/danielNg25/claude-session-restore.git
cd claude-session-restore && ./install-mac.sh
```

**Windows** (PowerShell)
```powershell
git clone https://github.com/danielNg25/claude-session-restore.git
cd claude-session-restore
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

Trình cài làm 3 việc:
- chép script vào `~/.claude/`;
- ghép thêm cấu hình vào `~/.claude/settings.json`, không đè các thiết lập sẵn có, và lưu bản sao `settings.json.bak-*`;
- thêm lệnh `claude-restore` vào PATH.

Chạy lại trình cài để cập nhật; hook sẽ không bị nhân đôi.

Sau khi cài, hãy thoát rồi mở lại các phiên Claude Code đang chạy, hoặc gõ `/hooks` một lần, để phiên nạp hook.

## Dùng

```
claude-restore              liệt kê, hỏi rồi mở (Enter = mở hết, hoặc gõ 1,3)
claude-restore -y           mở hết, không hỏi
claude-restore --list       chỉ xem danh sách
claude-restore --forget 2   bỏ phiên số 2 khỏi danh sách
```

Tab mới được mở như sau:

| Hệ điều hành | Mở bằng |
|---|---|
| macOS | iTerm; nếu không có thì Terminal. Lần đầu macOS hỏi quyền điều khiển, bấm OK. |
| Windows | Windows Terminal (`wt`); nếu không có thì cửa sổ cmd. |
| Linux | gnome-terminal; nếu không có thì in lệnh ra để bạn tự chạy. |

Các phiên đang chạy sẽ được bỏ qua.

## Gỡ

```bash
./install-mac.sh --uninstall
```
```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -Uninstall
```

Trình gỡ xoá các hook và dòng `remoteControlAtStartup` khỏi settings, đồng thời đổi tên các script thành `*.removed`.
