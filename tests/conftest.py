import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app import app, get_db
from database import Base
from models import User
from init_db import create_db as create_test_db


DATABASE_URL = "postgresql+asyncpg://example:example@localhost:5433/example_test"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_db() -> AsyncSession:
    async with async_session() as db:
        yield db

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, checkfirst=True)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await create_test_db(async_session())
    yield
    await engine.dispose()


@pytest.fixture
async def async_app_client(create_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client


@pytest.fixture
async def db_session(create_db):
    async with AsyncSession(bind=engine) as session:
        yield session
    await session.close()


@pytest.fixture
async def user_post_tweet(async_app_client):
    header = {'api-key': 'test'}
    tweet_data = {'tweet_data': 'new test tweet', 'tweet_media_ids': []}
    post_tweet = await async_app_client.post('/api/tweets', json=tweet_data, headers=header)
    tweet_id = post_tweet.json()['tweet_id']
    return tweet_id, header


@pytest.fixture
async def add_new_user(db_session):
    header = {'api-key': 'test'}
    new_user_id = 11
    new_user = User(id=new_user_id, api_key='test-999', name='Test User', )
    db_session.add(new_user)
    await db_session.commit()
    return header, new_user_id


def correct_response(response):
    assert response.status_code == 200
    assert 'result' in response.json() and response.json()['result'] is True
