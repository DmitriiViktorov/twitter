import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base


def get_database_url():
    """Get a link to the database depending on the mode of operation of the application"""
    if os.environ.get("ENV") == "test":
        return os.getenv("DATABASE_URL_TEST")
    elif os.environ.get("ENV") == "debug":
        return os.getenv("DATABASE_URL_DEBUG")
    else:
        return os.getenv("DATABASE_URL")


echo_value = bool(os.environ.get("ECHO"))
engine = create_async_engine(get_database_url(), echo=echo_value)
SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False,
    class_=AsyncSession,
    autoflush=True,
)
Base = declarative_base()
