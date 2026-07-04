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

import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


import qdrant_client
from llama_index.core import SimpleDirectoryReader
from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.ollama import OllamaEmbedding  # type: ignore
from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore

from . import config


def build_pipeline() -> IngestionPipeline:
    client = qdrant_client.QdrantClient(url=config.get_qdrant_url())
    vector_store = QdrantVectorStore(client=client, collection_name=config.get_collection())

    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(
                chunk_size=config.get_chunk_size(),
                chunk_overlap=config.get_chunk_overlap(),
            ),
            OllamaEmbedding(
                model_name=config.get_embedding_model(),
                base_url=config.get_ollama_url(),
            ),
        ],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
        # UPSERTS_AND_DELETE: правит изменённое И вычищает удалённые файлы.
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
    )

    # Подхватываем прошлое состояние; если его нет — первый (полный) прогон.
    try:
        pipeline_dir = config.get_pipeline_dir()
        pipeline.load(pipeline_dir)
        print(f"[ingest] состояние загружено из {pipeline_dir}")
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
    pipeline.persist(config.get_pipeline_dir())

    print(
        f"[ingest] готово: обработано {len(nodes)} новых/изменённых чанк(ов) "
        f"в коллекции '{config.get_collection()}' (0 = ничего не менялось)"
    )
