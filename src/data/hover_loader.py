import json


# HOVER 원본 JSON 파일을 로드해 리스트 형태로 반환한다.
def load_hover_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


# HOVER 항목에서 claim 매핑에 필요한 핵심 필드만 추출한다.
def extract_claim_rows(data: list[dict]) -> list[dict]:
    rows = []

    for item in data:
        rows.append({
            "uid": item["uid"],
            "claim": item["claim"],
            "label": item["label"],
            "supporting_facts": item.get("supporting_facts", []),
        })

    return rows
