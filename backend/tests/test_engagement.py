"""Engagement-rate unit tests. Pure stdlib so it runs with `python -m tests.test_engagement`
(no pytest required) — though `pytest` discovers it too.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import engagement_rate  # noqa: E402


def test_basic():
    # (8000 + 400) / 100000 * 100 = 8.4
    assert engagement_rate(8000, 400, 100000) == 8.4


def test_rounding():
    assert engagement_rate(1, 0, 3) == 33.33


def test_zero_views_is_safe():
    assert engagement_rate(10, 5, 0) == 0.0
    assert engagement_rate(10, 5, None) == 0.0  # type: ignore[arg-type]


def test_no_engagement():
    assert engagement_rate(0, 0, 5000) == 0.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
