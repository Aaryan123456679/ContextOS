from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from supabase import create_client, Client
from core.config import settings

# SQLAlchemy async setup
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"prepared_statement_cache_size": 0},  # required for Supabase pooler
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# Dependency to get db session
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Supabase Client (used only for Storage; DB ops go through SQLAlchemy directly)
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
except Exception:
    supabase = None  # type: ignore[assignment]

# Helper function to upload files
async def upload_file(bucket: str, path: str, content: bytes) -> str:
    """Uploads file to Supabase storage and returns public URL."""
    # Note: supabase-py doesn't have an async storage upload in standard library,
    # so we run it in execution thread or direct synchronous call since it's an MVP.
    supabase.storage.from_(bucket).upload(path, content)
    return supabase.storage.from_(bucket).get_public_url(path)
