"""Единая точка конфигурации.

И ingest.py, и mcp_server.py импортируют отсюда embed-модель и адреса.
Это гарантирует главный инвариант RAG: индексация и поиск идут ОДНОЙ
эмбеддинг-моделью. Разъехались модели -> поиск возвращает мусор.
Держим их в одном месте — рассинхрон структурно невозможен.
"""

from os import getenv as os_getenv


def get_ollama_url():
    """
    Локальная ollama: крутит только эмбеддинг-модель (векторизацию).
    """
    return os_getenv("OLLAMA_URL", "http://localhost:11434")


def get_qdrant_url():
    """
    Vector DB.
    """
    return os_getenv("QDRANT_URL", "http://localhost:6333")


def get_collection():
    return os_getenv("RAG_COLLECTION", "devitway_docs")


def get_embedding_model():
    """
    Мультиязычная модель (RU/EN/код), 1024d. Сначала: `ollama pull bge-m3`.
    """
    return os_getenv("EMBED_MODEL", "bge-m3")


def get_chunk_size():
    """
    Нарезка документов на чанки.
    """
    return int(os_getenv("CHUNK_SIZE", "512"))


def get_chunk_overlap():
    return int(os_getenv("CHUNK_OVERLAP", "64"))


def get_pipeline_dir():
    """
    Где хранится состояние ингеста (какие доки уже проиндексированы + их хэши).
    Без персиста каждый запуск = полный реиндекс, инкремент не работает.
    """
    return os_getenv("PIPELINE_DIR", "./pipeline_storage")
