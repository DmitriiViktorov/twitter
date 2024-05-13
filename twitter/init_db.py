from sqlalchemy.exc import IntegrityError
from models import User, Subscription, Post, Like
import random
from faker import Faker
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta

fake = Faker()


async def create_db(session):
    async with session.begin():
        result = await session.execute(select(func.count(User.id)))
        if result.scalar_one() == 0:
            insert_users = [
                User(name=fake.name(), api_key=f"test" if i == 0 else f'test-{i}') for i in range(10)
            ]

            session.add_all(insert_users)

            select_users = await session.execute(select(User))
            users = select_users.unique().scalars().all()

            for user in users:
                number_subscription = random.randint(1, 5)
                random_subscription = random.sample(range(1, 11), number_subscription)
                for sub_id in random_subscription:
                    if user.id != sub_id:
                        subscription = Subscription(follower_id=user.id, following_id=sub_id)
                        try:
                            session.add(subscription)
                        except IntegrityError:
                            await session.rollback()
                            continue

                for _ in range(random.randint(1, 5)):
                    random_created_at = datetime.now() - timedelta(seconds=random.randint(1, 5))
                    post = Post(content=fake.text(max_nb_chars=280), user_id=user.id, created_at=random_created_at)
                    session.add(post)

            query = select(Post)
            select_posts = await session.execute(query)
            all_posts = select_posts.unique().scalars().all()

            for post in all_posts:
                for i in random.sample(range(1, 11), random.randint(1, 10)):
                    like = Like(user_id=i, post_id=post.id)
                    session.add(like)
            await session.commit()

        else:
            pass
