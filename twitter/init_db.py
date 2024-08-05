from datetime import datetime, timedelta
import random
from typing import Sequence

from faker import Faker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from models import Like, Post, Subscription, User

fake = Faker()
INITIAL_USERS_COUNT = 10
MAX_CONTENT_LENGTH = 280


async def create_users(session: AsyncSession) -> Sequence[User]:
    """Function to fill database with fake initial users."""
    insert_users = [
        User(name=fake.name(), api_key='test' if user_id == 0 else f'test-{user_id}')
        for user_id in range(INITIAL_USERS_COUNT)
    ]

    session.add_all(insert_users)

    select_users = await session.execute(select(User))
    users = select_users.unique().scalars().all()
    return users


async def create_subscription(user: User, session: AsyncSession) -> None:
    """Function to fill database with fake initial subscriptions."""
    number_subscription = random.randint(1, 5)
    random_subscription = random.sample(range(1, 11), number_subscription)
    for sub_id in random_subscription:
        if user.id != sub_id:
            subscription = Subscription(
                follower_id=user.id,
                following_id=sub_id,
            )
            try:
                session.add(subscription)
            except IntegrityError:
                await session.rollback()
                continue


async def create_posts(user: User, session: AsyncSession) -> None:
    """Function to fill database with fake initial posts."""
    random_created_at = datetime.now() - timedelta(
        seconds=random.randint(1, 5),
    )
    post = Post(
        content=fake.text(max_nb_chars=MAX_CONTENT_LENGTH),
        user_id=user.id,
        created_at=random_created_at,
    )
    session.add(post)


async def create_likes(post: Post, session: AsyncSession) -> None:
    """Function to fill database with fake initial likes."""
    for user_id in random.sample(range(1, 11), random.randint(1, INITIAL_USERS_COUNT)):
        like = Like(user_id=user_id, post_id=post.id)
        session.add(like)


async def create_db(session: AsyncSession) -> None:
    """
    Function to fill database with fake initial users, posts, likes and subscriptions.

    Note:
        The function is triggered only if the database has been cleared and
        there is not a single row in it. The initial data can be useful for
        checking the correctness of the frontend at the debugging stage of the application.
    """
    users_in_db = await session.execute(select(func.count(User.id)))
    if users_in_db.scalar_one() == 0:

        users = await create_users(session)

        for user in users:
            await create_subscription(user, session)

            for _ in range(random.randint(1, 5)):
                await create_posts(user, session)

        select_posts = await session.execute(select(Post))
        all_posts = select_posts.unique().scalars().all()
        for post in all_posts:
            await create_likes(post, session)

    await session.commit()

