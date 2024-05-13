from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    api_key = Column(String, unique=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    followers = relationship('Subscription',
                             foreign_keys='Subscription.following_id',
                             back_populates='following'
                             )
    followings = relationship('Subscription',
                              foreign_keys='Subscription.follower_id',
                              back_populates='follower'
                              )
    posts = relationship('Post', back_populates='user', lazy='selectin')
    likes = relationship('Like', back_populates='user', lazy='selectin')

    @property
    def formatted_data(self):
        user_data = self.to_dict()
        user_data['followers'] = [subscription.follower.to_dict() for subscription in self.followers]
        user_data['following'] = [subscription.following.to_dict() for subscription in self.followings]
        return user_data

    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class Subscription(Base):
    __tablename__ = "subscription"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    follower_id = Column(Integer, ForeignKey('user.id'))
    following_id = Column(Integer, ForeignKey('user.id'))
    follower = relationship('User', foreign_keys=[follower_id], back_populates='followers', lazy='joined')
    following = relationship('User', foreign_keys=[following_id], back_populates='followings', lazy='joined')

    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follower_following'),
    )


class Post(Base):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(String(280))
    attachments = Column(ARRAY(String))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='posts', lazy='joined')
    likes = relationship('Like', back_populates='post', lazy='joined', cascade="all, delete")
    images = relationship('Media', back_populates='post', lazy='joined', cascade="all, delete")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def formatted_data(self):
        post_data = self.to_dict()
        post_data['likes'] = [like.to_dict() for like in self.likes]
        post_data['author'] = {'id': self.user.id, 'name': self.user.name}
        post_data['attachments'] = [media.url for media in self.images]
        return post_data


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    url = Column(String, unique=True, nullable=False)

    post_id = Column(Integer, ForeignKey('post.id'))
    post = relationship('Post', back_populates='images', lazy='joined')


class Like(Base):
    __tablename__ = "like"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='likes', lazy='joined')
    post_id = Column(Integer, ForeignKey('post.id'))
    post = relationship('Post', back_populates='likes', lazy='joined')

    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='unique_user_post'),
    )

    def to_dict(self):
        return {'user_id': self.user_id, 'name': self.user.name}
