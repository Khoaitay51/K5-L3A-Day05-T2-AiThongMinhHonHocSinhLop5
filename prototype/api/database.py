import asyncpg
from pgvector.asyncpg import register_vector
from config import settings
import httpx
from typing import List, Optional

pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        # First ensure vector extension exists before registering vector type
        try:
            temp_conn = await asyncpg.connect(settings.database_url)
            await temp_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await temp_conn.close()
        except Exception as e:
            print(f"Extension check notice: {e}")

        async def init_connection(conn):
            try:
                await register_vector(conn)
            except Exception as e:
                print(f"register_vector notice: {e}")

        pool = await asyncpg.create_pool(
            settings.database_url,
            init=init_connection,
            min_size=2,
            max_size=10
        )
    return pool

async def init_db():
    p = await get_db_pool()
    async with p.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Table for course documents (Section 3.1 - 3.5, syllabus, assignments)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS course_documents (
                id SERIAL PRIMARY KEY,
                section_code VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                is_active_assignment BOOLEAN DEFAULT FALSE,
                embedding vector(768)
            );
        """)

        # Table for TA Tickets
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ta_tickets (
                id SERIAL PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL,
                question TEXT NOT NULL,
                context TEXT,
                status VARCHAR(50) DEFAULT 'PENDING_REVIEW',
                expected_reply_at VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Table for FAQ Drafts (requires approval)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS faq_drafts (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                suggested_answer TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'DRAFT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await conn.execute("""
            ALTER TABLE ta_tickets ADD COLUMN IF NOT EXISTS owner_id TEXT;
            ALTER TABLE ta_tickets ADD COLUMN IF NOT EXISTS request_id UUID;
            CREATE UNIQUE INDEX IF NOT EXISTS ticket_request ON ta_tickets (owner_id, request_id);

            ALTER TABLE faq_drafts ADD COLUMN IF NOT EXISTS owner_id TEXT;
            ALTER TABLE faq_drafts ADD COLUMN IF NOT EXISTS source_section TEXT;
            ALTER TABLE faq_drafts ADD COLUMN IF NOT EXISTS source_quote TEXT;
            CREATE UNIQUE INDEX IF NOT EXISTS one_pending_draft
                ON faq_drafts (owner_id, source_section) WHERE status = 'DRAFT';

            CREATE TABLE IF NOT EXISTS source_flags (
                section_code TEXT PRIMARY KEY,
                quote TEXT NOT NULL,
                example TEXT NOT NULL,
                dismissed BOOLEAN NOT NULL DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS source_interest (
                section_code TEXT NOT NULL REFERENCES source_flags (section_code),
                owner_id TEXT NOT NULL,
                PRIMARY KEY (section_code, owner_id)
            );

            CREATE TABLE IF NOT EXISTS assignment_progress (
                owner_id TEXT PRIMARY KEY,
                step SMALLINT NOT NULL CHECK (step = 2)
            );
        """)


async def get_embedding(text: str) -> List[float]:
    """Generates 768-dim embedding using Gemini API.
    If GEMINI_API_KEY is not set or network fails, returns a zero vector for fallback."""
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() in ("", "your_gemini_api_key_here"):
        return [0.0] * 768

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.EMBEDDING_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "model": f"models/{settings.EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 768
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embedding", {}).get("values", [0.0] * 768)
            else:
                print(f"Embedding API error (status {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Error fetching embedding: {e}")
    return [0.0] * 768
