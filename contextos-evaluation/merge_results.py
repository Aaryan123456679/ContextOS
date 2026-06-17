"""Merge results.csv from multiple run dirs (e.g. local shard + Colab shard) by run_id."""
import csv
import sys
from pathlib import Path


def merge(out_csv: str, *result_csvs: str):
    seen, rows, fields = set(), [], None
    for path in result_csvs:
        p = Path(path)
        if not p.exists():
            print(f"skip missing {p}")
            continue
        with p.open() as f:
            r = csv.DictReader(f)
            fields = fields or r.fieldnames
            for row in r:
                rid = row["run_id"]
                if rid in seen:
                    continue
                seen.add(rid)
                rows.append(row)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Merged {len(rows)} unique rows -> {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python merge_results.py OUT.csv IN1.csv IN2.csv ...")
        sys.exit(1)
    merge(sys.argv[1], *sys.argv[2:])
