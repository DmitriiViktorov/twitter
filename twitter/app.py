import os
import uuid
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Optional,
    Tuple,
)

from contextlib import asynccontextmanager
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    status,
    UploadFile,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from database import engine, Base, SessionLocal
from init_db import create_db
from models import Like, Media, Post, Subscription, User
from schemas import (
    MediaResponse,
    PostResponse,
    SuccessfulResponse,
    TweetResponse,
    UserResponse,
)
from utils import logger, log_function_calls


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Initialize the database engine and create initial users, posts, and likes.

    Args:
        application (FastAPI): An instance of the FastAPI application.

    Yields:
        None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await create_db(SessionLocal())
    yield
    await SessionLocal().close()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def exception_handler(exc: Exception) -> JSONResponse:
    """Handle exceptions raised by the app."""
    error_type = exc.__class__.__name__
    error_message = str(exc)
    return JSONResponse(
        status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        content={
            'result': False,
            'error_type': error_type,
            'error_message': error_message,
        }
    )


def get_api_key(api_key: str = Header(...)):
    """
    Get api-key of current user from header

    Parameters:
        api_key (str): api-key of current user

    Returns:
        str: api-key value of current user
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key header missing"
        )
    return api_key


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get Session with the current database."""
    async with SessionLocal() as db:
        yield db


DEFAULT_DB = Depends(get_db)
API_KEY_HEADER = 'api-key'
SUCCESS_RESPONSE = {'result': True}
DEFAULT_FILE = File(...)

HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_INTERNAL_SERVER_ERROR = 500


async def get_user_and_tweet(
    tweet_id: int, user_api_key: str, db: AsyncSession,
) -> Tuple[User, Post]:
    """
    Get the desired user and the required tweet that he posted.

    Parameters:
        tweet_id (int): The id of the tweet to retrieve.
        user_api_key (str): The api key of the user.
        db (AsyncSession): Session with the current database.

    Returns:
        Tuple containing the user and the tweet.
    """
    current_user = await get_user_by_filter(db=db, api_key=user_api_key)

    query_tweet = select(Post).filter_by(id=tweet_id)
    tweet = await db.execute(query_tweet)
    current_tweet = tweet.unique().scalar_one_or_none()

    if not current_tweet:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail='Tweet not found')

    return current_user, current_tweet


async def get_user_by_filter(
    db: AsyncSession, api_key: Optional[str] = None, user_id: Optional[int] = None,
) -> User:
    """
    Get a user by their api-key or id.

    Parameters:
        db (AsyncSession): Session with the current database.
        user_id (int): The id of the desired user.
        api_key (str): The api key of the current user.

    Returns:
        Required user object or None.
    """
    filters = []
    if api_key:
        filters.append(User.api_key == api_key)
    if user_id:
        filters.append(User.id == user_id)
    query = (
        select(User)
        .options(joinedload(User.followers), joinedload(User.followings))
        .filter(*filters)
    )
    queried_user = await db.execute(query)

    user = queried_user.unique().scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail='User not found')
    return user


@log_function_calls(logger)
async def get_followers(
    db: AsyncSession, follower_id: int, current_user_api_key: str,
) -> Tuple[User, User]:
    """
    Get the desired user and his follower.

    Parameters:
        db (AsyncSession): Session with the current database.
        follower_id (int): The id of the follower of the desired user.
        current_user_api_key (str): The api key of the current user.

    Returns:
        Tuple containing the user and the follower of the desired user.
    """
    current_user = await get_user_by_filter(db=db, api_key=current_user_api_key)
    follower = await get_user_by_filter(db=db, user_id=follower_id)
    return current_user, follower


async def get_and_formatted_user(
    db: AsyncSession, api_key: Optional[str] = None, user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get a user by their api-key or id and format their data.

    Parameters:
        db (AsyncSession): Session with the current database.
        user_id (int): The id of the desired user.
        api_key (str): The api key of the current user.

    Returns:
        Formatted user object.

    Note:
        This structure is necessary for correct display on the frontend.
    """
    user = await get_user_by_filter(db=db, api_key=api_key, user_id=user_id)
    return user.formatted_data


@app.get('/api/tweets', response_model=PostResponse)
async def read_tweets(db: AsyncSession = DEFAULT_DB):
    """
    Get all tweets for the user are sorted from the newest to the oldest.

    Parameters:
        db (AsyncSession): Session with the current database.

    Returns:
        Response object containing successful result status and tweets.
    """
    query = (
        select(Post)
        .options(joinedload(Post.user), joinedload(Post.likes))
        .order_by(Post.created_at.desc())
    )
    queried_posts = await db.execute(query)
    all_posts = queried_posts.unique().scalars().all()
    tweets = [post.formatted_data for post in all_posts]
    tweets_response = {'tweets': tweets}
    return {**SUCCESS_RESPONSE, **tweets_response}


@app.get('/api/users/me', response_model=UserResponse)
async def read_me(db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Get formatted data of the current user.

    Parameters:
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status
        and the information about current user.
    """
    if not api_key:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND, detail='API key required',
        )
    current_user = await get_and_formatted_user(db=db, api_key=api_key)
    current_user_response = {'user': current_user}
    return {**SUCCESS_RESPONSE, **current_user_response}


@app.get('/api/users/{id}', response_model=UserResponse)
async def read_user(id: int, db: AsyncSession = DEFAULT_DB):
    """
    Get formatted data of the desired user.

    Parameters:
        id (int): The id of the desired user.
        db (AsyncSession): Session with the current database.

    Returns:
        Response object containing successful result status
        and the information about desired user.
    """
    user_by_id = await get_and_formatted_user(db=db, user_id=id)
    user_by_id_response = {'user': user_by_id}
    return {**SUCCESS_RESPONSE, **user_by_id_response}


@app.post('/api/medias', response_model=MediaResponse)
async def upload_media(file: UploadFile = DEFAULT_FILE, db: AsyncSession = DEFAULT_DB):
    """
    Saving media files attached to a tweet.

    Parameters:
        file (UploadFile): Media file to be uploaded
        db (AsyncSession): Session with the current database.

    Returns:
        Response object containing successful result status
        and id of the uploaded media file.
    """
    if not os.path.exists('media'):
        os.makedirs('media')

    if file.filename:
        unique_id = str(uuid.uuid4())
        filename = unique_id + secure_filename(file.filename)
        file_path = os.path.join('media', filename)
        new_media = Media(url=file_path)
        db.add(new_media)
        await db.commit()

        with open(file_path, 'wb') as buffer:
            buffer.write(await file.read())

        new_media_response = {'media_id': new_media.id}
        return {**SUCCESS_RESPONSE, **new_media_response}


@app.post('/api/tweets', response_model=TweetResponse)
@log_function_calls(logger)
async def create_tweet(request: Request, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Post new tweet with attached media files.

    Parameters:
        request (Request): Request object containing id`s of uploaded media files.
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status
        and id of new tweet.
    """
    query = select(User).filter_by(api_key=api_key)
    user = await db.execute(query)
    current_user = user.unique().scalar_one()
    tweet_data = await request.json()

    tweet_content = tweet_data.get('tweet_data')
    attachments_ids = tweet_data.get('tweet_media_ids')
    attachments_query = select(Media).filter(Media.id.in_(attachments_ids))
    attachments = await db.execute(attachments_query)
    images = attachments.unique().scalars().all()
    images_urls = [media.url for media in images]

    new_post = Post(
        content=tweet_content, user_id=current_user.id, attachments=images_urls,
    )
    new_post.images.extend(images)
    for image in images:
        image.post = new_post
    db.add(new_post)
    await db.commit()
    new_tweet_response = {'tweet_id': new_post.id}
    return {**SUCCESS_RESPONSE, **new_tweet_response}


@app.delete('/api/tweets/{id}', response_model=SuccessfulResponse)
async def delete_tweet(id: int, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Delete desired tweet.

    Parameters:
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status.
    """
    current_user, current_tweet = await get_user_and_tweet(
        tweet_id=id, user_api_key=api_key, db=db,
    )

    if current_tweet.user_id != current_user.id:
        raise HTTPException(status_code=HTTP_STATUS_FORBIDDEN, detail='Forbidden')

    await db.delete(current_tweet)
    await db.commit()
    await db.invalidate()
    return SUCCESS_RESPONSE


@app.post('/api/tweets/{id}/likes', response_model=SuccessfulResponse)
async def like_tweet(id: int, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Post like to desired tweet by current user.

    Parameters:
        id (int): The id of the desired tweet.
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status.
    """
    current_user, current_tweet = await get_user_and_tweet(
        tweet_id=id, user_api_key=api_key, db=db,
    )
    like = Like(user_id=current_user.id, post_id=current_tweet.id)
    db.add(like)
    try:
        await db.commit()

    except IntegrityError:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail='You have already liked this tweet',
        )

    await db.invalidate()
    return SUCCESS_RESPONSE


@app.delete('/api/tweets/{id}/likes', response_model=SuccessfulResponse)
async def unlike_tweet(id: int, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Delete like to desired tweet by current user.

    Parameters:
        id (int): The id of the desired tweet.
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status.
    """
    current_user, current_tweet = await get_user_and_tweet(
        tweet_id=id, user_api_key=api_key, db=db,
    )

    query = select(Like).filter_by(user_id=current_user.id, post_id=current_tweet.id)
    like = await db.execute(query)
    current_like = like.unique().scalar_one_or_none()
    if not current_like:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail='Like not found',
        )

    await db.delete(current_like)
    await db.commit()
    await db.invalidate()
    return SUCCESS_RESPONSE


@app.post('/api/users/{id}/follow', response_model=SuccessfulResponse)
async def follow(id: int, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Create new subscription between current and desired user.

    Parameters:
        id (int): The id of the desired user.
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status.
    """
    current_user, follower = await get_followers(
        db=db, current_user_api_key=api_key, follower_id=id,
    )
    subscription = Subscription(follower_id=current_user.id, following_id=follower.id)
    db.add(subscription)
    try:
        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail='You have already subscribed to this user',
        )

    await db.invalidate()
    return SUCCESS_RESPONSE


@app.delete('/api/users/{id}/follow', response_model=SuccessfulResponse)
async def unfollow(id: int, db: AsyncSession = DEFAULT_DB, api_key: str = Depends(get_api_key)):
    """
    Delete subscription between current and desired user.

    Parameters:
        request (Request): Request object containing current user api-key.
        id (int): The id of the desired user.
        db (AsyncSession): Session with the current database.
        api_key (str): The API key of the current user.

    Returns:
        Response object containing successful result status.
    """
    current_user, follower = await get_followers(
        db=db, current_user_api_key=api_key, follower_id=id,
    )
    query = select(Subscription).filter_by(
        follower_id=current_user.id, following_id=follower.id,
    )
    subscription = await db.execute(query)
    current_subscription = subscription.unique().scalar_one_or_none()
    if not current_subscription:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail='Subscription not found',
        )

    await db.delete(current_subscription)
    await db.commit()
    await db.invalidate()
    return SUCCESS_RESPONSE
