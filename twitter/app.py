
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File, Depends
from contextlib import asynccontextmanager

from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import os
from werkzeug.utils import secure_filename
import uuid
from typing import Tuple, Optional


from database import engine, Base, SessionLocal
from models import User, Post, Media, Like, Subscription
from schemas import UserResponse, PostResponse
from init_db import create_db
# from utils import logger


@asynccontextmanager
async def lifespan(_application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await create_db(SessionLocal())
    yield
    await SessionLocal().close()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


async def get_db() -> AsyncSession:
    async with SessionLocal() as db:
        yield db


async def _get_user_and_tweet(tweet_id: int, user_api_key: str, db: AsyncSession) -> Tuple[User, Post]:

    current_user = await _get_user_by_filter(db=db, api_key=user_api_key)

    query_tweet = select(Post).filter_by(id=tweet_id)
    tweet = await db.execute(query_tweet)
    current_tweet = tweet.unique().scalar_one_or_none()

    if not current_tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    return current_user, current_tweet


async def _get_user_by_filter(db: AsyncSession, api_key: str = None, user_id: int = None):
    filters = []

    filters.append(User.api_key == api_key) if api_key else filters.append(User.id == user_id) #REVIEW А если и то и то?
    query = select(User).options(joinedload(User.followers), joinedload(User.followings)).filter(*filters)
    result = await db.execute(query)

    user = result.unique().scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _get_followers(db: AsyncSession, follower_id: int, current_user_api_key: str = None) -> Tuple[User, User]:
    current_user = await _get_user_by_filter(db=db, api_key=current_user_api_key)
    follower = await _get_user_by_filter(db=db, user_id=follower_id)
    return current_user, follower


async def _get_and_formatted_user(db: AsyncSession, api_key: Optional[str] = None, user_id: Optional[int] = None):
    user = await _get_user_by_filter(db=db, api_key=api_key, user_id=user_id)
    return user.formatted_data


@app.get("/api/tweets", response_model=PostResponse, )
async def read_tweets(db: AsyncSession = Depends(get_db)):

    query = (select(Post)
             .options(joinedload(Post.user), joinedload(Post.likes))
             .order_by(Post.created_at.desc()))
    result = await db.execute(query)
    all_posts = result.unique().scalars().all()
    tweets = [post.formatted_data for post in all_posts]

    return {
        'result': True,
        'tweets': tweets
    }


@app.get("/api/users/me", response_model=UserResponse)
async def read_me(api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):

    current_user = await _get_and_formatted_user(db=db, api_key=api_key)
    return {'result': True, 'user': current_user}


@app.get("/api/users/{id}")
async def read_user(id: int, db: AsyncSession = Depends(get_db)):

    user_by_id = await _get_and_formatted_user(db=db, user_id=id)
    return {'result': True, 'user': user_by_id}


@app.post("/api/medias") # medias нет такого слова в английском языке
async def upload_media(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not os.path.exists("media"):
        os.makedirs("media")

    unique_id = uuid.uuid4()
    filename = str(unique_id) + secure_filename(file.filename)
    file_path = os.path.join("media", filename)
    new_media = Media(url=file_path)
    db.add(new_media)
    await db.commit()

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    media_id = new_media.id
    return {"result": True, "media_id": media_id}


@app.post("/api/tweets")
async def create_tweet(request: Request, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):
    query = select(User).filter_by(api_key=api_key)
    user = await db.execute(query)
    current_user = user.unique().scalar_one()
    tweet_data = await request.json()

    content = tweet_data.get('tweet_data')
    attachments_ids = tweet_data.get('tweet_media_ids')

    attachments = await db.execute(select(Media).filter(Media.id.in_(attachments_ids)))
    images = attachments.unique().scalars().all()
    images_urls = [media.url for media in images]

    new_post = Post(content=content, user_id=current_user.id, attachments=images_urls)
    new_post.images.extend(images)
    for image in images:
        image.post = new_post
    db.add(new_post)
    await db.commit()
    return {
        'result': True,
        'tweet_id': new_post.id,
    }


@app.delete("/api/tweets/{id}")
async def delete_tweet(id: int, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):
    current_user, current_tweet = await _get_user_and_tweet(tweet_id=id, user_api_key=api_key, db=db)

    if current_tweet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await db.delete(current_tweet)
    await db.commit()
    await db.invalidate()
    return {'result': True}


@app.post("/api/tweets/{id}/likes")
async def like_tweet(id: int, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):

    current_user, current_tweet = await _get_user_and_tweet(tweet_id=id, user_api_key=api_key, db=db)

    try:
        like = Like(user_id=current_user.id, post_id=current_tweet.id)
        db.add(like) # нужен ли тут await?
        await db.commit()
        await db.invalidate()
        return {'result': True}

    except IntegrityError:
        raise HTTPException(status_code=400, detail="You have already liked this tweet")


@app.delete("/api/tweets/{id}/likes")
async def unlike_tweet(id: int, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):
    current_user, current_tweet = await _get_user_and_tweet(tweet_id=id, user_api_key=api_key, db=db)

    query = select(Like).filter_by(user_id=current_user.id, post_id=current_tweet.id)
    like = await db.execute(query)
    current_like = like.unique().scalar_one_or_none()
    if not current_like:
        raise HTTPException(status_code=404, detail="Like not found")

    await db.delete(current_like)
    await db.commit()
    await db.invalidate()
    return {'result': True}


@app.post("/api/users/{id}/follow")
async def follow(id: int, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):
    current_user, follower = await _get_followers(db=db, current_user_api_key=api_key, follower_id=id)
    subscription = Subscription(follower_id=current_user.id, following_id=follower.id)

    try:
        db.add(subscription)
        await db.commit()
        await db.invalidate()
        return {'result': True}

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="You have already subscribed to this user")


@app.delete("/api/users/{id}/follow")
async def unfollow(id: int, api_key: str = Header('api-key'), db: AsyncSession = Depends(get_db)):
    current_user, follower = await _get_followers(db=db, current_user_api_key=api_key, follower_id=id)
    query = select(Subscription).filter_by(follower_id=current_user.id, following_id=follower.id)
    subscription = await db.execute(query)
    current_subscription = subscription.unique().scalar_one_or_none()
    if current_subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.delete(current_subscription)
    await db.commit()
    await db.invalidate()
    return {'result': True}
