import json
from pathlib import Path


def load_hover_dataset_from_local_json(json_path: Path) -> list[dict]:
    """
    data/raw/hover 에서 hover_train_release_v1.1.json 불러오기
    로컬 경로에 hover train data가 없다면 에러 발생
    """
    if not json_path.exists():
        raise FileNotFoundError(
            f"HoVer train json not found: {json_path}\n"
            "Please download `hover_train_release_v1.1.json` from the official HoVer site "
            "and place it under `data/raw/hover/`."
        )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Unexpected HoVer json format: expected list, got {type(data)}")

    return data


def validate_hotpot_wiki_dir(wiki_dir: Path) -> Path:
    """
    hotpot qa wiki 로드하는 함수 
    PoC 단계에서는 api로 wiki corpus 가져오므로 미사용
    """
    if not wiki_dir.exists():
        raise FileNotFoundError(
            f"HotpotQA processed Wikipedia directory not found: {wiki_dir}\n"
            "Please download and extract the HotpotQA processed Wikipedia corpus, then set "
            "`hotpot_wiki_dir` in config.py correctly."
        )
    if not wiki_dir.is_dir():
        raise NotADirectoryError(f"Expected directory, got file: {wiki_dir}")
    return wiki_dir