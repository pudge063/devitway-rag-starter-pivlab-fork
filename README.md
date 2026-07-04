# devitway-rag-starter

Минимальный, но полный E2E-стек локального RAG: документы → векторы → поиск,
подключаемый к любому агенту через **MCP**. RAG здесь — **самостоятельный слой**,
а не часть конкретного агента: один и тот же сервер цепляется и к `qwen-code`,
и к `Claude Code` без переделок.

```
OFFLINE  (cron / watch — «обновляется само»):
  docs/ ─► Reader ─► Splitter ─► ollama(bge-m3) ─► Qdrant
            │           │             ▲                ▲
            └── docstore (хэш по doc_id) ─┘  не менялся→skip,
                                             изменился→upsert, удалён→delete

QUERY  (runtime, любой агент):
  agent ─MCP─► search(q) ─► ollama(bge-m3) ─► Qdrant top-k ─► фрагменты ─► agent
```

**Роли:** `ollama` крутит только эмбеддинг-модель (векторизация, локально) ·
`Qdrant` хранит и ищет векторы · `MCP-сервер` — единая точка входа для агентов.
Генерацию ответа делает сам агент своей моделью (Qwen / Claude).

---

## Требования

- **Docker** (для Qdrant)
- **Python 3.10+**
- **[ollama](https://ollama.com)** установлена и запущена

## Быстрый старт

```bash
# 1. Поднять Qdrant
docker compose up -d

# 2. Скачать эмбеддинг-модель (мультиязычная, RU/EN/код)
ollama pull bge-m3

# 3. Python-окружение
poetry install
. .venv/bin/activate

# 4. Проиндексировать документы (в ./docs уже лежит пример)
rag ingest -d ./docs

# 5. Проверить, что сервер поднимается (Ctrl+C для выхода)
rag mcp-server
```

Готово — RAG работает. Осталось подключить агента (ниже).

## Как работает инкрементальное обновление

`ingest.py` хранит состояние в `pipeline_storage/` (какие файлы уже
проиндексированы + их хэши). При повторном запуске:

| Что случилось с файлом | Действие |
|------------------------|----------|
| не менялся             | пропуск (по хэшу) |
| изменился              | переэмбеддится и upsert в Qdrant |
| удалён из `./docs`     | его чанки удаляются из Qdrant |

Полного реиндекса нет — только дельта. Поэтому запускать можно хоть каждую минуту.

### Повесить на автообновление

**Cron** (каждые 15 минут):
```cron
*/15 * * * * cd /home/ai/rag_server && /home/ai/rag_server/.venv/bin/rag ingest -d "/home/ai/rag_server/docs" >> /home/ai/rag_server/ingest.log 2>&1
```

**Watch** (реагировать на изменения сразу, нужен `inotify-tools`):
```bash
while inotifywait -r -e modify,create,delete ./docs; do
  .venv/bin/python ingest.py ./docs
done
```

## Подключение агентов

Оба агента цепляются к **одному и тому же** серверу. Обкатай на том, что уже
работает, потом добавь второй — переделывать нечего.

> ⚠️ В `command` указывай **абсолютный путь к python из .venv** — агент запускает
> сервер без активации окружения, иначе не найдутся зависимости.

### qwen-code

В `settings.json` (обычно `~/.qwen/settings.json` или `.qwen/settings.json` в проекте):
```json
{
  "mcpServers": {
    "rag": {
      "command": "/home/ai/rag_server/.venv/bin/rag",
      "args": ["mcp-server"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add rag -- /home/ai/rag_server/.venv/bin/rag /home/ai/rag_server/.venv/bin/rag
```

Проверка: спроси агента что-нибудь по содержимому `./docs` — он должен вызвать
инструмент `search`.

## Главный инвариант (не нарушай)

**Индексация и поиск обязаны идти одной эмбеддинг-моделью.** Проиндексируешь одной
(1024d), поищешь другой (например 384d) — получишь мусор или ошибку размерности.
Поэтому модель и адреса заданы в одном месте — `config.py`, — откуда их берут оба
скрипта. Меняешь модель — меняешь в `config.py` и делаешь полный реиндекс
(удали `pipeline_storage/` и коллекцию в Qdrant).

## Траблшутинг

| Симптом | Причина / решение |
|---------|-------------------|
| Ошибка про `OpenAI API key` | LlamaIndex по умолчанию берёт OpenAI-эмбеддер. В этом репо `Settings.embed_model` задан явно — проверь, что не переопределил. |
| Поиск возвращает мусор / пусто | Модель при индексации ≠ при поиске. Держи одну (см. инвариант выше). |
| `Connection refused` к Qdrant | Не поднят `docker compose up -d` или занят порт 6333. |
| `model not found` | Забыл `ollama pull bge-m3`. |
| Агент не видит MCP-сервер | `command` должен указывать на `.venv/bin/python` (абсолютный путь), не на системный python. |

## Структура

```
devitway-rag-starter/
├── docker-compose.yml   # Qdrant
├── requirements.txt
├── config.py            # единая конфигурация (embed-модель, адреса) — источник инварианта
├── ingest.py            # инкрементальный ингест docs -> Qdrant
├── mcp_server.py        # read-only MCP: инструмент search()
├── env.example          # cp env.example .env
└── docs/                # сюда кладёшь свои документы
    └── example.md
```

## Куда расти

- **Reranker** вторым этапом (`bge-reranker-v2-m3`) — заметно поднимает точность.
- **Redis-docstore** вместо файлового — для большого корпуса и параллельного ингеста.
- **Больше форматов** — `SimpleDirectoryReader` уже читает pdf/docx/md/txt; коннекторы
  (Google Drive, Notion, БД) — отдельные пакеты `llama-index-readers-*`.
