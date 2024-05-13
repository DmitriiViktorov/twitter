from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./recipe.db"

engine = create_async_engine(DATABASE_URL, echo=False)

async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

session = async_session()
Base = declarative_base()

