from pathlib import Path
import pandas as pd

from src.data.hover_loader import load_hover_json, extract_claim_rows
from src.data.gold_mapper import map_claim_to_gold_chunks


# HOVER claim과 parquet 청크를 연결해 gold_chunk_ids 결과 파일을 생성한다.
def build_gold_map(hover_path: Path, parquet_path: Path, output_path: Path):
    hover_data = load_hover_json(hover_path)
    claim_rows = extract_claim_rows(hover_data)

    df = pd.read_parquet(parquet_path)

    chunks = []
    for _, row in df.iterrows():
        chunks.append({
            "id": row["paragraph_uid"],
            "text": row["paragraph_text"],
            "metadata": {
                "title": row["title"],
            }
        })

    outputs = []

    for row in claim_rows:
        gold_ids = map_claim_to_gold_chunks(row, chunks)

        outputs.append({
            "uid": row["uid"],
            "claim": row["claim"],
            "gold_chunk_ids": gold_ids,
        })

    pd.DataFrame(outputs).to_json(output_path, orient="records", lines=True)

    print("Saved gold map:", output_path)
