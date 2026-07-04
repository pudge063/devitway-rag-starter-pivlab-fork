"""Инкрементальный ингест документов в Qdrant через LlamaIndex + ollama.

Запуск:
    python ingest.py ./docs

Каждый повторный запуск обновляет ТОЛЬКО изменившееся (сравнение по хэшу):
    * файл не менялся      -> пропускается
    * файл изменился       -> переэмбеддится и upsert в Qdrant
    * файл удалён из папки  -> его чанки удаляются из Qdrant

Состояние (что уже проиндексировано) лежит в config.PIPELINE_DIR.
Это и есть "процесс, который обновляется" — вешаешь на cron/watch (см. README).
"""
import sys

import qdrant_client
from llama_index.core import SimpleDirectoryReader
from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

import config


def build_pipeline() -> IngestionPipeline:
    client = qdrant_client.QdrantClient(url=config.QDRANT_URL)
    vector_store = QdrantVectorStore(client=client, collection_name=config.COLLECTION)

    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
            ),
            OllamaEmbedding(
                model_name=config.EMBED_MODEL,
                base_url=config.OLLAMA_URL,
            ),
        ],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
        # UPSERTS_AND_DELETE: правит изменённое И вычищает удалённые файлы.
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
    )

    # Подхватываем прошлое состояние; если его нет — первый (полный) прогон.
    try:
        pipeline.load(config.PIPELINE_DIR)
        print(f"[ingest] состояние загружено из {config.PIPELINE_DIR}")
    except FileNotFoundError:
        print("[ingest] прошлого состояния нет — первый полный индекс")

    return pipeline


def main(docs_dir: str) -> None:
    # filename_as_id=True — стабильный doc_id между запусками.
    # Без него дедуп и удаление НЕ работают (каждый раз новый UUID).
    documents = SimpleDirectoryReader(
        docs_dir,
        filename_as_id=True,
        recursive=True,
    ).load_data()
    print(f"[ingest] прочитано документов: {len(documents)} из {docs_dir}")

    pipeline = build_pipeline()
    nodes = pipeline.run(documents=documents, show_progress=True)
    pipeline.persist(config.PIPELINE_DIR)

    print(
        f"[ingest] готово: обработано {len(nodes)} новых/изменённых чанк(ов) "
        f"в коллекции '{config.COLLECTION}' (0 = ничего не менялось)"
    )


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "./docs"
    main(target)
