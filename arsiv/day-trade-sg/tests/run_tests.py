"""pytest kurulu değilse testleri doğrudan çalıştırır: python tests/run_tests.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import test_engine as T  # noqa: E402

fails = 0
for name in [n for n in dir(T) if n.startswith("test_")]:
    try:
        getattr(T, name)()
        print("OK  ", name)
    except Exception as e:  # noqa: BLE001
        fails += 1
        print("FAIL", name, repr(e))
sys.exit(1 if fails else 0)
