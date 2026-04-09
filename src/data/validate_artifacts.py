import pandas as pd


# parquet 산출물의 기본 통계/중복/결측 여부를 빠르게 점검한다.
def validate_parquet(path: str):
    df = pd.read_parquet(path)

    print("===== BASIC STATS =====")
    print("rows:", len(df))
    print("unique docs:", df["doc_id"].nunique())
    print("unique titles:", df["title_norm"].nunique())

    print("\n===== DUP CHECK =====")
    print("duplicate paragraph_uid:", df.duplicated("paragraph_uid").sum())
    print("duplicate paragraph_id :", df.duplicated("paragraph_id").sum())

    print("\n===== NULL CHECK =====")
    print(df.isnull().sum())

    print("\n===== SAMPLE =====")
    print(df.head(3))
