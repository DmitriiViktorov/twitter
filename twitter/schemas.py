from pydantic import BaseModel
from typing import List, Optional


class UserBase(BaseModel):
    id: int
    name: str


class PostBase(BaseModel):
    id: int
    content: str
    attachments: Optional[List] = []


class LikeBase(BaseModel):
    user_id: int
    name: str


class PostOut(PostBase):
    author: UserBase
    likes: List[LikeBase] = []

    class ConfigDict:
        from_attributes = True
        populate_by_name = True


class PostResponse(BaseModel):
    result: bool
    tweets: List[PostOut] = []


class UserOut(BaseModel):
    id: int
    name: str
    followers: List[UserBase] = []
    following: List[UserBase] = []

    class ConfigDict:
        from_attributes = True
        populate_by_name = True


class UserResponse(BaseModel):
    result: bool
    user: UserOut
