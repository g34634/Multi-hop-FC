from typing import Tuple
from src.common.config import Config
from src.data.utils import save_json, set_seed, safe_get_supporting_facts


def sample_hover_claims(ds, config: Config) -> Tuple[list[dict], list[str]]:
    set_seed(config.random_seed)

    filtered = [row for row in ds if row.get("num_hops") == config.target_num_hops]
    sampled = filtered[: config.sample_size]

    sampled_claims = []
    required_titles = set()

    for row in sampled:
        supporting_facts = safe_get_supporting_facts(row)

        sampled_claims.append(
            {
                "uid": row.get("uid"),
                "claim": row.get("claim"),
                "label": row.get("label"),
                "num_hops": row.get("num_hops"),
                "supporting_facts": supporting_facts,
            }
        )

        for item in supporting_facts:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                doc_title = item[0]
                required_titles.add(doc_title)

    return sampled_claims, sorted(required_titles)


def run_hover_sampling(ds, config: Config) -> tuple[list[dict], list[str]]:
    sampled_claims, required_titles = sample_hover_claims(ds, config)
    save_json(sampled_claims, config.sampled_hover_path)
    save_json(required_titles, config.required_titles_path)
    return sampled_claims, required_titles