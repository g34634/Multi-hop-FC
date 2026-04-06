from src.common.config import Config
from src.data.utils import save_json


def compute_hit_at_k(gold_ids: list[str], retrieved_ids: list[str]) -> int:
    gold_set = set(gold_ids)
    retrieved_set = set(retrieved_ids)
    return int(len(gold_set & retrieved_set) > 0)


def compute_recall_at_k(gold_ids: list[str], retrieved_ids: list[str]) -> float:
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0

    retrieved_set = set(retrieved_ids)
    hits = len(gold_set & retrieved_set)
    return hits / len(gold_set)


def evaluate_retrieval(retrieval_rows: list[dict], top_k: int) -> dict:
    per_claim = []
    hit_scores = []
    recall_scores = []

    for row in retrieval_rows:
        gold_ids = row["gold_chunk_ids"]
        retrieved_ids = row["retrieved_ids"]

        hit_k = compute_hit_at_k(gold_ids, retrieved_ids)
        recall_k = compute_recall_at_k(gold_ids, retrieved_ids)

        hit_scores.append(hit_k)
        recall_scores.append(recall_k)

        per_claim.append(
            {
                "uid": row["uid"],
                "claim": row["claim"],
                "gold_chunk_ids": gold_ids,
                "retrieved_ids": retrieved_ids,
                f"hit@{top_k}": hit_k,
                f"recall@{top_k}": recall_k,
            }
        )

    summary = {
        "top_k": top_k,
        f"avg_hit@{top_k}": sum(hit_scores) / len(hit_scores) if hit_scores else 0.0,
        f"avg_recall@{top_k}": sum(recall_scores) / len(recall_scores) if recall_scores else 0.0,
        "num_claims": len(retrieval_rows),
        "per_claim": per_claim,
    }
    return summary


def save_eval_results(all_results: dict, config: Config) -> None:
    save_json(all_results, config.eval_results_path)