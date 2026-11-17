#!/usr/bin/env bash
# Cài claude-restore trên macOS (cũng chạy được trên Linux).
#   ./install-mac.sh            cài / cập nhật
#   ./install-mac.sh --uninstall   gỡ
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "Cần python3 (macOS: chạy 'xcode-select --install')."; exit 1; }

HOOK="$HOME/.claude/hooks/session-registry.py"
BIN="$HOME/.local/bin/claude-restore"

if [ "${1:-}" = "--uninstall" ]; then
  "$PY" merge_settings.py --remove
  for f in "$HOOK" "$BIN"; do [ -e "$f" ] && mv "$f" "$f.removed" && echo "Đã đổi tên $f -> $f.removed"; done
  echo "Đã gỡ. Mở lại Claude Code để áp dụng."
  exit 0
fi

mkdir -p "$(dirname "$HOOK")" "$(dirname "$BIN")"
cp session-registry.py "$HOOK"
cp claude-restore.py "$BIN"
chmod +x "$HOOK" "$BIN"
echo "Đã chép: $HOOK"
echo "Đã chép: $BIN"

"$PY" merge_settings.py "$PY" "$HOOK"

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *)
    RC="$HOME/.zshrc"; [ "$(basename "${SHELL:-zsh}")" = "bash" ] && RC="$HOME/.bashrc"
    if ! grep -qs '\.local/bin' "$RC"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
      echo "Đã thêm ~/.local/bin vào PATH trong $RC."
    fi
    echo "Mở terminal mới để lệnh claude-restore có hiệu lực."
    ;;
esac

cat <<'EOF'

Xong. Việc còn lại:
  1. Thoát và mở lại các phiên Claude Code đang chạy (hoặc gõ /hooks một lần trong mỗi phiên) để nạp hook.
  2. Sau khi máy tắt/bật lại: gõ  claude-restore
     Lần đầu macOS hỏi cho phép điều khiển iTerm/Terminal: bấm OK.
EOF
