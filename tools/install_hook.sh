#!/usr/bin/env bash
# Usage: bash tools/install_hook.sh a      (or b, or daniel)
# Makes git refuse any commit that touches a file you don't own.
set -e
owner="${1:?say who you are: a, b or daniel}"
git config proofpilot.owner "$owner"
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
PY=$(command -v python3 || command -v python)
"$PY" tools/check_owner.py --staged
HOOK
chmod +x .git/hooks/pre-commit
echo "Hook installed. You are '$owner'. Commits touching other people's files will be blocked."
