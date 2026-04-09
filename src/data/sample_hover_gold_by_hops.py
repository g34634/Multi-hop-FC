from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


PREFERRED_STATUSES = {"exact_match", "normalized_match"}


# 샘플링 스크립트 실행에 필요한 CLI 인자를 정의하고 파싱한다.
def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_input = project_root / "data" / "interim" / "gold_mapping" / "hover_train_mapped_from_parquet_final.json"
    default_output_dir = project_root / "data" / "interim" / "gold_mapping"

    parser = argparse.ArgumentParser(
        description="Sample HOVER mapped data by num_hops with preference for exact/normalized matches."
    )
    parser.add_argument("--input-path", type=Path, default=default_input)
    parser.add_argument("--output-dir", type=Path, default=default_output_dir)
    parser.add_argument("--sample-size-per-hop", type=int, default=100)
    parser.add_argument("--hops", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


# gold_alignment_status에서 선호 상태 개수/비율/총개수를 계산한다.
def _match_stats(row: dict) -> tuple[int, float, int]:
    statuses = row.get("gold_alignment_status", [])
    if not isinstance(statuses, list):
        return 0, 0.0, 0

    preferred_count = 0
    for item in statuses:
        if isinstance(item, dict) and item.get("status") in PREFERRED_STATUSES:
            preferred_count += 1

    total = len(statuses)
    ratio = (preferred_count / total) if total > 0 else 0.0
    return preferred_count, ratio, total


# 특정 hop의 row를 점수 기반으로 정렬해 상위 n개를 샘플링한다.
def _sample_for_hop(rows: list[dict], hop: int, n: int, seed: int) -> list[dict]:
    filtered = [r for r in rows if r.get("num_hops") == hop]
    if len(filtered) < n:
        raise ValueError(f"Not enough rows for num_hops={hop}: required={n}, available={len(filtered)}")

    rng = random.Random(seed + hop)
    rng.shuffle(filtered)

    ranked = sorted(
        filtered,
        key=lambda r: _match_stats(r),
        reverse=True,
    )
    return ranked[:n]


# hop별 샘플 파일을 생성하고 선호 매칭 통계를 출력한다.
def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.input_path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    for hop in args.hops:
        sample_rows = _sample_for_hop(
            rows=rows,
            hop=hop,
            n=args.sample_size_per_hop,
            seed=args.seed,
        )

        out_path = args.output_dir / f"hover_train_mapped_from_parquet_final_hop{hop}_sample{args.sample_size_per_hop}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(sample_rows, f, ensure_ascii=False, indent=2)

        preferred_total = sum(_match_stats(r)[0] for r in sample_rows)
        print(
            f"saved: {out_path} | rows={len(sample_rows)} | preferred_status_total={preferred_total}"
        )


if __name__ == "__main__":
    main()
