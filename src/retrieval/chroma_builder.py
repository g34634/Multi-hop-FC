from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from src.common.config import Config


def get_embedding_function(config: Config):
    return SentenceTransformerEmbeddingFunction(
        model_name=config.embedding_model_name
    )


def get_client(config: Config):
    return PersistentClient(path=str(config.chroma_dir))


def get_or_create_collection(config: Config):
    client = get_client(config)
    embedding_fn = get_embedding_function(config)

    if config.chroma_recreate_collection:
        try:
            client.delete_collection(name=config.collection_name)
            print(f"[chroma] deleted existing collection: {config.collection_name}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": config.distance_metric},
    )
    return collection


def get_existing_ids(collection, ids: list[str]) -> set[str]:
    """
    Return the subset of ids that already exist in the collection.
    Chroma get() supports filtering by ids.
    """
    if not ids:
        return set()

    existing_ids = set()
    # very large id lists can be chunked defensively
    step = 1000
    for start in range(0, len(ids), step):
        batch_ids = ids[start : start + step]
        result = collection.get(ids=batch_ids, include=[])
        found_ids = result.get("ids", []) if result else []
        existing_ids.update(found_ids)

    return existing_ids


def upsert_chunks(chunks: list[dict], config: Config) -> None:
    collection = get_or_create_collection(config)

    all_ids = [row["id"] for row in chunks]
    existing_ids = get_existing_ids(collection, all_ids)

    new_chunks = [row for row in chunks if row["id"] not in existing_ids]

    print(f"[chroma] total input chunks: {len(chunks)}")
    print(f"[chroma] existing chunks skipped: {len(existing_ids)}")
    print(f"[chroma] new chunks to insert: {len(new_chunks)}")

    if not new_chunks:
        print("[chroma] no new chunks to insert.")
        return

    batch_size = config.batch_size
    for start in range(0, len(new_chunks), batch_size):
        batch = new_chunks[start : start + batch_size]

        ids = [row["id"] for row in batch]
        docs = [row["text"] for row in batch]
        metas = [row["metadata"] for row in batch]

        collection.add(
            ids=ids,
            documents=docs,
            metadatas=metas,
        )