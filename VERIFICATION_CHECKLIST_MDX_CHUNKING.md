# MDX Chunking at Startup — Verification Checklist

**Objective:** Verify that when the FastAPI server starts, it extracts chunks from MDX files stored in `nbd_web/content/docs` and stores them in the database.

---

## 1. Code Flow Verification ✓

### 1.1 Startup Entry Point: `lifespan()` Context Manager
**File:** [nbd_backend/app/app.py](nbd_backend/app/app.py#L215)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... setup code ...
    await create_db_and_tables()
    await setup_checkpointer_tables()
    initialize_llm_router()
    
    # THIS IS WHERE MDX CHUNKING HAPPENS:
    try:
        await asyncio.wait_for(seed_nfd_docs(), timeout=120)
    except TimeoutError:
        logging.getLogger(__name__).warning(
            "NFD docs seeding timed out after 120s — skipping. "
            "Docs will be indexed on the next restart."
        )

    log_system_snapshot("startup_complete")
    yield
    await close_checkpointer()
```

**Verified:** ✓ `seed_nfd_docs()` is called during startup with a 120-second timeout.

---

### 1.2 Seeding Function: `seed_nfd_docs()`
**File:** [nbd_backend/app/tasks/nfd_docs_indexer.py](nbd_backend/app/tasks/nfd_docs_indexer.py#L204)

The function performs the following:
1. **Finds all MDX files** in `nbd_web/content/docs` via `get_all_mdx_files()`
2. **Parses frontmatter** using `parse_mdx_frontmatter()` to extract title
3. **Creates chunks** from content via `create_nfd_docs_chunks(content)`
4. **Generates embeddings** for each chunk using `embed_text(chunk.text)`
5. **Stores in database** as `NFDDocsDocument` and `NFDDocsChunks` records

**Verified:** ✓ The function indexes MDX files and creates chunked representations.

---

### 1.3 Chunk Creation Logic
**File:** [nbd_backend/app/tasks/nfd_docs_indexer.py](nbd_backend/app/tasks/nfd_docs_indexer.py#L83)

```python
def create_nfd_docs_chunks(content: str) -> list[NFDDocsChunks]:
    """Create chunks from NFD documentation content."""
    return [
        NFDDocsChunks(
            content=chunk.text,
            embedding=embed_text(chunk.text),
        )
        for chunk in config.chunker_instance.chunk(content)
    ]
```

**Verified:** ✓ Each chunk has:
- `content`: the text chunk
- `embedding`: vector representation (via `embed_text()`)

---

## 2. MDX Files Discovery ✓

### 2.1 Directory Structure
**Expected Location:** `nbd_web/content/docs/`

**Verified Files Found:**
```
✓ nbd_web/content/docs/connectors/gmail.mdx
✓ nbd_web/content/docs/connectors/luma.mdx
✓ nbd_web/content/docs/connectors/github.mdx
✓ nbd_web/content/docs/connectors/google-drive.mdx
✓ nbd_web/content/docs/connectors/airtable.mdx
✓ nbd_web/content/docs/connectors/google-calendar.mdx
✓ nbd_web/content/docs/connectors/confluence.mdx
✓ nbd_web/content/docs/connectors/obsidian.mdx
✓ nbd_web/content/docs/connectors/notion.mdx
✓ nbd_web/content/docs/connectors/elasticsearch.mdx
✓ nbd_web/content/docs/connectors/jira.mdx
✓ nbd_web/content/docs/connectors/clickup.mdx
✓ nbd_web/content/docs/connectors/circleback.mdx
✓ nbd_web/content/docs/connectors/microsoft-teams.mdx
✓ nbd_web/content/docs/connectors/linear.mdx
✓ nbd_web/content/docs/connectors/bookstack.mdx
✓ nbd_web/content/docs/connectors/discord.mdx
✓ nbd_web/content/docs/connectors/web-crawler.mdx
✓ nbd_web/content/docs/connectors/slack.mdx
✓ nbd_web/content/docs/index.mdx
... (more files exist)
```

**Total Count:** 20+ MDX files discovered.

---

## 3. Database Schema Verification

### 3.1 Expected Tables

The seeding process creates/updates two main tables:

#### **Table 1: `nfd_docs_document`**
Stores full document metadata:
- `id` (PK)
- `source` (file path relative to docs/)
- `title` (extracted from frontmatter)
- `content` (full document text)
- `content_hash` (SHA-256 of raw content for change detection)
- `embedding` (vector embedding of full content)
- `updated_at` (timestamp of last index)

#### **Table 2: `nfd_docs_chunks`**
Stores individual chunks with embeddings:
- `id` (PK)
- `nfd_docs_document_id` (FK to nfd_docs_document)
- `content` (chunk text)
- `embedding` (vector embedding of chunk)

### 3.2 How to Verify (After Server Start)

**Connect to database and run:**

```sql
-- Check total documents
SELECT COUNT(*) as total_documents FROM nfd_docs_document;

-- Check total chunks
SELECT COUNT(*) as total_chunks FROM nfd_docs_chunks;

-- Verify embeddings exist (non-null)
SELECT COUNT(*) as chunks_with_embeddings 
FROM nfd_docs_chunks 
WHERE embedding IS NOT NULL;

-- View sample documents
SELECT id, source, title, updated_at 
FROM nfd_docs_document 
LIMIT 10;

-- View chunks for a specific document
SELECT 
    nfc.id,
    nfc.nfd_docs_document_id,
    LENGTH(nfc.content) as content_length,
    (nfc.embedding IS NOT NULL) as has_embedding
FROM nfd_docs_chunks nfc
WHERE nfc.nfd_docs_document_id = 1
LIMIT 5;
```

---

## 4. Startup Behavior — What You Should See in Logs

When the server starts, you should see logs like:

```
[INFO] app.tasks.nfd_docs_indexer: Starting NFD docs indexing...
[INFO] app.tasks.nfd_docs_indexer: Found 20 MDX files to index
[INFO] app.tasks.nfd_docs_indexer: Creating new document: connectors/gmail.mdx
[INFO] app.tasks.nfd_docs_indexer: Creating new document: connectors/luma.mdx
[INFO] app.tasks.nfd_docs_indexer: Creating new document: connectors/github.mdx
...
[INFO] app.tasks.nfd_docs_indexer: Indexing complete: 20 created, 0 updated, 0 skipped, 0 deleted
[INFO] app.utils.perf: [system_snapshot] startup_complete
```

Or, on subsequent starts (if content hasn't changed):

```
[INFO] app.tasks.nfd_docs_indexer: Starting NFD docs indexing...
[INFO] app.tasks.nfd_docs_indexer: Found 20 MDX files to index
[DEBUG] app.tasks.nfd_docs_indexer: Skipping unchanged: connectors/gmail.mdx
[DEBUG] app.tasks.nfd_docs_indexer: Skipping unchanged: connectors/luma.mdx
...
[INFO] app.tasks.nfd_docs_indexer: Indexing complete: 0 created, 0 updated, 20 skipped, 0 deleted
```

---

## 5. Failure Modes & Recovery

### 5.1 Timeout (120s exceeded)
**What happens:** If indexing takes longer than 120 seconds, a `TimeoutError` is caught and logged as a warning. The server **continues to start anyway** (doesn't block startup).

**Log:** 
```
[WARNING] app.app: NFD docs seeding timed out after 120s — skipping. Docs will be indexed on the next restart.
```

**Recovery:** Restart the server to retry indexing.

### 5.2 Database Connection Failure
**What happens:** The indexing task will fail, the exception is logged, and the function returns `(0, 0, 0, 0)`.

**Log:**
```
[ERROR] app.tasks.nfd_docs_indexer: Failed to seed NFD docs: <error details>
```

### 5.3 Missing `nbd_web/content/docs` Directory
**What happens:** `get_all_mdx_files()` checks if the directory exists and returns an empty list if it doesn't.

**Log:**
```
[WARNING] app.tasks.nfd_docs_indexer: Docs directory not found: /path/to/nbd_web/content/docs
[INFO] app.tasks.nfd_docs_indexer: Indexing complete: 0 created, 0 updated, 0 skipped, 0 deleted
```

---

## 6. Example Verification: Content Hash & Change Detection

The indexer uses **content hash** (SHA-256) to detect changes:

1. **First startup:** All files are new → all documents created.
2. **Modify an MDX file** (e.g., add a paragraph to `connectors/gmail.mdx`).
3. **Restart the server:** The hash changes → document is updated, new chunks created.
4. **No changes to any file, restart again:** All hashes match → all files skipped (0 created, 0 updated, 20 skipped).

---

## 7. Manual Triggering (For Testing)

**File:** [nbd_backend/scripts/seed_nfd_docs.py](nbd_backend/scripts/seed_nfd_docs.py)

```bash
cd /Users/macbook/Desktop/Sales_Kyanon/SurfSense/nbd_backend
python scripts/seed_nfd_docs.py
```

**Expected output:**
```
==================================================
  NFD Documentation Seeding
==================================================

Results:
  Created: 20
  Updated: 0
  Skipped: 0
  Deleted: 0
==================================================
```

(On second run, `Created` and `Updated` would be 0, `Skipped` would be 20.)

---

## 8. Conclusion

### ✓ Confirmed Behavior:
1. **Startup Flow:** `lifespan()` → `seed_nfd_docs()` → `index_nfd_docs()` → chunk creation
2. **MDX Source:** `nbd_web/content/docs/*.mdx` files (20+ files found)
3. **Chunking:** `config.chunker_instance.chunk(content)` splits document content into chunks
4. **Embeddings:** Each chunk gets a vector embedding via `embed_text()`
5. **Storage:** Chunks stored in `nfd_docs_chunks` table linked to `nfd_docs_document`
6. **Change Detection:** Content hash prevents re-indexing unchanged files
7. **Timeout Handling:** 120-second timeout with graceful fallback if exceeded

### ✓ The answer to your original question:
**Yes**, when the server starts, it **extracts chunks for MDX files** stored at `nbd_web/content/docs` and stores them with embeddings in the database.

---

## 9. Next Steps (For Local Verification)

If you want to run the actual verification:

1. **Install Python 3.12** (currently not installed; pyenv shows 3.10.14 and 3.11.5 available)
2. **Install dependencies:** `pip install -e .` or `poetry install`
3. **Set up database & Redis** with environment variables in `.env`
4. **Run the seed script:** `python scripts/seed_nfd_docs.py`
5. **Start the server:** `uvicorn app.app:app --reload`
6. **Query the database** to verify documents and chunks were created

Alternatively, **view the logs during server startup** to see the seeding messages live.
