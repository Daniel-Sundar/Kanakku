"""Block changes to files you don't own.  Owner: Daniel.

Local (pre-commit hook):  python tools/check_owner.py --staged
CI (pull request):        python tools/check_owner.py --branch a/health-cards --base origin/main
Owner comes from:  git config proofpilot.owner  (set by tools/install_hook.sh), or the branch prefix.
"""
import argparse
import fnmatch
import subprocess
import sys

OWNERS = {
    "daniel": ["*"],                                         # lead may touch everything
    "a": ["app.py", "assets/*", ".streamlit/*"],
    "b": ["profiler_checks.py", "eval.py", "EVAL.md", "README.md", "docs/screens/*"],
}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--staged", action="store_true")
    p.add_argument("--branch")
    p.add_argument("--base", default="origin/main")
    a = p.parse_args()

    if a.branch:
        owner = a.branch.split("/")[0].lower()
        changed = git("diff", "--name-only", f"{a.base}...HEAD").split()
    else:
        owner = git("config", "--get", "proofpilot.owner").strip().lower() if a.staged else ""
        changed = git("diff", "--cached", "--name-only").split()

    if owner not in OWNERS:
        print(f"✖ Unknown owner '{owner}'. Branch names must start with a/, b/ or daniel/ "
              f"(or run: bash tools/install_hook.sh <a|b|daniel>).")
        return 1
    allowed = OWNERS[owner]
    bad = [f for f in changed if not any(fnmatch.fnmatch(f, pat) for pat in allowed)]
    if bad:
        print(f"✖ {owner.upper()} may only change: {', '.join(allowed)}")
        print("  These files belong to someone else:")
        for f in bad:
            print(f"    - {f}")
        print("  Undo them with:  git restore --staged <file> && git restore <file>")
        print("  Need a change there? Ask the owner in the team chat (see OWNERS.md).")
        return 1
    print(f"✔ ownership OK for {owner.upper()} ({len(changed)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
