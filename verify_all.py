"""Re-run every proof script in a fresh process and check it prints the expected value.  Owner: Daniel.
Usage:  python verify_all.py        (exit code 0 = all PASS)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / "proofs" / "expected.json"


def main() -> int:
    import verifier
    expected = json.loads(EXPECTED.read_text())
    failed = 0
    for rel, want in expected.items():
        out = verifier.rerun(rel)
        ok = out["match"]
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {rel}  expected={want}  got={out['value']}")
    print(f"\n{len(expected) - failed}/{len(expected)} proofs re-ran identically")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
