"""MCP-сервер: read-only семантический поиск по проиндексированному корпусу.

Отдаёт один инструмент `search(query, k)`. Наполнение индекса живёт НЕ здесь,
а в ingest.py (отдельный процесс). Этот сервер только читает Qdrant.

Эмбеддер берётся из config.py — тот же, что в ingest.py. Поэтому индекс и
поиск всегда на одной модели (рассинхрон невозможен).

Подключение (один и тот же сервер к обоим агентам):
    qwen-code   -> секция mcpServers в settings.json
    Claude Code -> claude mcp add rag -- /path/.venv/bin/python /path/mcp_server.py
"""
import qdrant_client
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from mcp.server.fastmcp import FastMCP

import config

embed_model = OllamaEmbedding(model_name=config.EMBED_MODEL, base_url=config.OLLAMA_URL)

# Явно задаём эмбеддер, иначе LlamaIndex по умолчанию полезет в OpenAI.
Settings.embed_model = embed_model
Settings.llm = None  # ретриверу LLM не нужен — только векторный поиск.

client = qdrant_client.QdrantClient(url=config.QDRANT_URL)
vector_store = QdrantVectorStore(client=client, collection_name=config.COLLECTION)
index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

mcp = FastMCP("rag")


@mcp.tool()
def search(query: str, k: int = 5) -> str:
    """Семантический поиск по корпусу документов.

    Возвращает k наиболее релевантных фрагментов с указанием источника.
    Вызывай перед ответом на вопросы о содержимом проиндексированных документов.
    """
    nodes = index.as_retriever(similarity_top_k=k).retrieve(query)
    if not nodes:
        return "Ничего релевантного не найдено."

    blocks = []
    for i, node in enumerate(nodes, 1):
        src = node.metadata.get("file_name") or node.metadata.get("file_path") or "unknown"
        score = f"{node.score:.3f}" if node.score is not None else "n/a"
        blocks.append(f"[{i}] score={score} источник={src}\n{node.text}")
    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run()  # stdio transport
