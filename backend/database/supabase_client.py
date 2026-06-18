"""Supabase client singleton — all DB operations go through this."""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


async def insert(table: str, data: dict) -> dict:
    client = get_client()
    result = client.table(table).insert(data).execute()
    return result.data[0] if result.data else {}


async def upsert(table: str, data: dict, on_conflict: str = "id") -> dict:
    client = get_client()
    result = client.table(table).upsert(data, on_conflict=on_conflict).execute()
    return result.data[0] if result.data else {}


async def fetch_all(table: str, filters: dict | None = None, limit: int = 100) -> list:
    client = get_client()
    query = client.table(table).select("*").limit(limit)
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    result = query.execute()
    return result.data or []


async def fetch_one(table: str, field: str, value: str) -> dict | None:
    client = get_client()
    result = client.table(table).select("*").eq(field, value).single().execute()
    return result.data


async def update(table: str, record_id: str, data: dict) -> dict:
    client = get_client()
    result = client.table(table).update(data).eq("id", record_id).execute()
    return result.data[0] if result.data else {}
