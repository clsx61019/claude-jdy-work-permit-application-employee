"""
对比测试：每个样例生成一次，与 tests/expected/ 里保存的"正确结果"逐个域比较。

运行:      python tests/run_tests.py
更新基准:  python tests/run_tests.py --update   （确认改动正确后再用）

每个样例配一个表单名，见 CASES。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from service.generate import render  # noqa: E402

CASES = [
    ("form09", "ict"),
    ("form09", "investment"),
    ("form09", "ict_extension"),
    ("form09_5", "investment_employer"),
    ("form09_5", "investment_client"),
    ("form09_10", "ict_employer"),
    ("form09_10", "ict_client"),
    ("form09", "employment_extension"),
    ("form09_6", "employment_employer"),
    ("form09_6", "employment_client"),
    ("form09_6", "employment_extension"),
    ("form09_8", "hungarian_card_employer"),
    ("form09_8", "hungarian_card_client"),
    ("form09_8", "hungarian_card_change"),
    ("form09", "hungarian_card_change"),
]


def label(doc, no):
    return doc.labels(int(no))


def main(update=False):
    failed = 0
    for form, sample in CASES:
        record = json.loads((ROOT / "tests/samples" / f"{sample}.json").read_text(encoding="utf-8"))
        doc = render(form, record)
        got = doc.snapshot()
        path = ROOT / "tests/expected" / f"{form}_{sample}.json"
        if update or not path.exists():
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({k: [label(doc, k), v] for k, v in got.items()},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"已保存基准 {path.name}（{len(got)} 个域）")
            continue
        expected = {k: v for k, (_, v) in json.loads(path.read_text(encoding="utf-8")).items()}
        diffs = [(k, expected.get(k), got.get(k)) for k in sorted(set(expected) | set(got), key=int)
                 if expected.get(k) != got.get(k)]
        if diffs:
            failed += 1
            print(f"✗ {form} / {sample}")
            for k, a, b in diffs:
                print(f"   域 {k}（{label(doc, k)}）: 原来 {a!r} → 现在 {b!r}")
        else:
            print(f"✓ {form} / {sample}（{len(got)} 个域）")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(update="--update" in sys.argv)
