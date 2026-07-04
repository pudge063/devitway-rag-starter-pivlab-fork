"""Единая точка конфигурации.

И ingest.py, и mcp_server.py импортируют отсюда embed-модель и адреса.
Это гарантирует главный инвариант RAG: индексация и поиск идут ОДНОЙ
эмбеддинг-моделью. Разъехались модели -> поиск возвращает мусор.
Держим их в одном месте — рассинхрон структурно невозможен.
"""
import os

# Локальная ollama: крутит только эмбеддинг-модель (векторизацию).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Vector DB.
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("RAG_COLLECTION", "devitway_docs")

# Мультиязычная модель (RU/EN/код), 1024d. Сначала: `ollama pull bge-m3`.
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")

# Нарезка документов на чанки.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))

# Где хранится состояние ингеста (какие доки уже проиндексированы + их хэши).
# Без персиста каждый запуск = полный реиндекс, инкремент не работает.
PIPELINE_DIR = os.getenv("PIPELINE_DIR", "./pipeline_storage")
