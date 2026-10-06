"""Re-run every proof script in a fresh process and check it prints the expected value.  Owner: Daniel.
Usage:  python verify_all.py        (exit code 0 = all PASS)"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / "proofs" / "expected.json"


def run_proof(path: Path):
    out = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=60, cwd=ROOT)
    for line in out.stdout.splitlines():
        if line.startswith("RESULT="):
            return json.loads(line[len("RESULT="):])
    raise RuntimeError(out.stderr.strip() or "no RESULT= line printed")


def main() -> int:
    expected = json.loads(EXPECTED.read_text())
    failed = 0
    for rel, want in expected.items():
        try:
            got = run_proof(ROOT / rel)
            got_value = got.get("value", {k: v["value"] for k, v in got.items() if isinstance(v, dict)})
            ok = json.dumps(got_value, sort_keys=True) == json.dumps(want, sort_keys=True)
        except Exception as e:  # noqa: BLE001
            got_value, ok = f"ERROR: {e}", False
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {rel}  expected={want}  got={got_value}")
    print(f"\n{len(expected) - failed}/{len(expected)} proofs re-ran identically")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
