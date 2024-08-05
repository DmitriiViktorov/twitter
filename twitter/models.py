from datetime import datetime
from typing import Dict, Any
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    Integer,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base

MAX_CONTENT_LENGTH = 280


class User(Base):
    """
    User model.

    Attributes:
        id (int): Unique identifier for the user.
        api_key (str): Unique API key for the user.
        name (str): Name of the user.
        created_at (datetime): Date and time when the user was created
        (default to current UTC time).
        followers (Relationship): Relationship with the subscription table,
        indicating users who are following this user.
        followings (Relationship): Relationship with the subscription table,
        indicating users whom this user is following.
        posts (Relationship): Relationship with the post table,
        indicating posts created by this user.
        likes (Relationship): Relationship with the like table,
        indicating likes given by this user.
    """

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    api_key = Column(String, unique=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    followers = relationship(
        'Subscription',
        foreign_keys='Subscription.following_id',
        back_populates='following',
    )
    followings = relationship(
        'Subscription',
        foreign_keys='Subscription.follower_id',
        back_populates='follower',
    )
    posts = relationship('Post', back_populates='user', lazy='selectin')
    likes = relationship('Like', back_populates='user', lazy='selectin')

    def to_dict(self) -> Dict[str, Any]:
        """Method for displaying class attributes and their values as a dictionary."""
        return {'id': self.id, 'name': self.name}

    @property
    def formatted_data(self) -> Dict[str, Any]:
        """
        Property method to return user data in a formatted dictionary.

        Returns:
            dict:  A dictionary that contains complete information about the user,
            including the names and IDs of the users to whom the current user is
            subscribed and the names and IDs of the users who are subscribed
            to the current user.

        Note:
            This response structure is necessary for correct display on the frontend.
        """
        user_data = self.to_dict()
        user_data['followers'] = [subscription.follower.to_dict() for subscription in self.followers]
        user_data['following'] = [subscription.following.to_dict() for subscription in self.followings]
        return user_data


class Subscription(Base):
    """
    Subscription model.

    Attributes:
        id (int): Identifier of the subscription.
        created_at (datetime): Date and time when the user was created
        (default to current UTC time).
        follower_id (int): The ID of the user who subscribed to another user
        following_id (int): The ID of the user that the other user subscribed to
        follower (Relationship): Relationship with the user table,
        indicating users who are following this user.
        following (Relationship): Relationship with the user table,
        indicating users whom this user is following.
    """

    __tablename__ = 'subscription'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    follower_id = Column(Integer, ForeignKey('user.id'))
    following_id = Column(Integer, ForeignKey('user.id'))
    follower = relationship(
        'User', foreign_keys=[follower_id], back_populates='followers', lazy='joined',
    )
    following = relationship(
        'User', foreign_keys=[following_id], back_populates='followings', lazy='joined',
    )

    __table_args__ = (
        UniqueConstraint(
            'follower_id', 'following_id', name='unique_follower_following',
        ),
    )


class Post(Base):
    """
    Post model.

    Attributes:
        id (int): Identifier of the subscription.
        created_at (datetime): Date and time when the user was created
        (default to current UTC time).
        content (str): Text content of the post.
        attachments (ARRAY): A array that contains links to attached media files
        user_id (int): The ID of the user who posted this post.
        user (Relationship): Relationship with the user table,
        indicating users who posted this post.
        likes (Relationship): Relationship with the like table,
        indicating likes given to this post.
        images (Relationship): Relationship with the media table,
        indicating media images attached to this post.
    """

    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(String(MAX_CONTENT_LENGTH))
    attachments = Column(ARRAY(String))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='posts', lazy='joined')
    likes = relationship(
        'Like', back_populates='post', lazy='joined', cascade='all, delete',
    )
    images = relationship(
        'Media', back_populates='post', lazy='joined', cascade='all, delete',
    )

    def to_dict(self) -> Dict[str, Any]:
        """Method for displaying class attributes and their values as a dictionary."""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}

    @property
    def formatted_data(self) -> Dict[str, Any]:
        """
        Property method to return post data in a formatted dictionary.

        Returns:
            dict:  A dictionary that contains complete information about the post,
            including likes given to this post, authors name and IDs of the users
            who posted this post and attached media files.

        Note:
            This response structure is necessary for correct display on the frontend.
        """
        post_data = self.to_dict()
        post_data['likes'] = [like.to_dict() for like in self.likes]
        post_data['author'] = {'id': self.user.id, 'name': self.user.name}
        post_data['attachments'] = [media.url for media in self.images]
        return post_data


class Media(Base):
    """
    Media file model.

    Attributes:
        id (int): Identifier of the media file.
        created_at (datetime): Date and time when the user was created
        (default to current UTC time).
        url (str): The URL of the media file location.
        post_id (int): The ID of the post to which this media file is attached
        post (Relationship): Relationship with the post table,
        indicating post to which this media file is attached.
    """

    __tablename__ = 'media'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    url = Column(String, unique=True, nullable=False)

    post_id = Column(Integer, ForeignKey('post.id'))
    post = relationship('Post', back_populates='images', lazy='joined')


class Like(Base):
    """
    Like model.

    Attributes:
        id (int): Identifier of the media file.
        created_at (datetime): Date and time when the user was created
        (default to current UTC time).
        user_id (int): The ID of the user who posted this like.
        user (Relationship): Relationship with the user table,
        indicating users who posted this like.
        post_id (int): The ID of the post to which this like is attached
        post (Relationship): Relationship with the post table,
        indicating post to which this like is attached.
    """

    __tablename__ = 'like'

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
        """Method for displaying class attributes and their values as a dictionary."""
        return {'user_id': self.user_id, 'name': self.user.name}
