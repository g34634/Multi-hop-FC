from src.common.config import Config
from src.data.utils import make_chunk_id, normalize_title, save_json


def enrich_hover_with_gold_chunks(sampled_claims: list[dict], config: Config) -> list[dict]:
    enriched = []

    for row in sampled_claims:
        gold_doc_titles = []
        gold_chunk_ids = []

        for item in row.get("supporting_facts", []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue

            doc_title, sent_id = item[0], item[1]
            gold_doc_titles.append(doc_title)

            chunk_id = make_chunk_id(
                doc_title=doc_title,
                sent_id=sent_id,
                lowercase=config.lowercase_titles_for_id,
            )
            gold_chunk_ids.append(chunk_id)

        gold_doc_titles = sorted(set(gold_doc_titles))
        gold_chunk_ids = sorted(set(gold_chunk_ids))

        new_row = dict(row)
        new_row["gold_doc_titles"] = gold_doc_titles
        new_row["gold_chunk_ids"] = gold_chunk_ids

        enriched.append(new_row)

    return enriched


def run_gold_mapping(sampled_claims: list[dict], config: Config) -> list[dict]:
    enriched = enrich_hover_with_gold_chunks(sampled_claims, config)
    save_json(enriched, config.hover_with_gold_path)
    return enriched