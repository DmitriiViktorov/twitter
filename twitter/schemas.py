from pydantic import BaseModel, Field
from typing import List, Optional


class UserBase(BaseModel):
    """Base user model with required attributes."""

    id: int = Field(description='Unique ID of twitter user')
    name: str = Field(description='User name')


class PostBase(BaseModel):
    """Base post model with required attributes."""

    id: int = Field(description='Unique ID of tweet')
    content: str = Field(description='The content of the tweet')
    attachments: Optional[List[str]] = Field(
        description='Links to media files added to this tweet',
    )


class LikeBase(BaseModel):
    """Base like model with required attributes."""

    user_id: int = Field(description='The ID of the user who liked this tweet')
    name: str = Field(description='Name of the user who liked this tweet')


class PostOut(PostBase):
    """The Post model with all attributes for output endpoints."""

    author: UserBase = Field(description='Information about the author of this tweet')
    likes: Optional[List[LikeBase]] = Field(description='List of likes on this tweet')

    class ConfigDict:
        from_attributes = True
        populate_by_name = True


class PostResponse(BaseModel):
    """The Post model with all attributes in the required format for the frontend."""

    result: bool = Field(description='Successful status of the response')
    tweets: Optional[List[PostOut]] = Field(
        description='List of tweets for this user, from the most recent to the oldest',
    )


class UserOut(UserBase):
    """The User model with all attributes for output endpoints."""

    followers: Optional[List[UserBase]] = Field(
        description='List of followers of this user',
    )
    following: Optional[List[UserBase]] = Field(
        description='List of users that the user follows',
    )

    class ConfigDict:
        from_attributes = True
        populate_by_name = True


class UserResponse(BaseModel):
    """The User model with all attributes in the required format for the frontend."""

    result: bool = Field(description='Successful status of the response')
    user: UserOut = Field(description='Information about the requested user')


class SuccessfulResponse(BaseModel):
    """Base response model with only result attribute for endpoints."""

    result: bool = Field(description='Successful status of the response')


class MediaResponse(SuccessfulResponse):
    """The Media response with success response and additional media information."""

    media_id: int = Field(description='Unique ID of media file')


class TweetResponse(SuccessfulResponse):
    """The Tweet response with success response and additional tweet information."""

    tweet_id: int = Field(description='Unique ID of tweet')
