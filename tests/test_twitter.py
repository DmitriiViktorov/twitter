import pytest
from sqlalchemy import func
from sqlalchemy.future import select
from models import User, Post
from app import get_user_and_tweet, get_user_by_filter
from fastapi import HTTPException
from typing import Tuple
from .conftest import correct_response


@pytest.mark.asyncio
async def test_get_tweets(async_app_client):
    response = await async_app_client.get("/api/tweets")
    correct_response(response)
    assert 'tweets' in response.json() and isinstance(response.json()['tweets'], list)
    required_keys = ['id', 'content', 'attachments', 'author', 'likes']
    for tweet in response.json()['tweets']:
        assert all(key in tweet for key in required_keys)


@pytest.mark.asyncio
async def test_get_current_user(async_app_client):
    header = {'api-key': "test"}

    response = await async_app_client.get("/api/users/me", headers=header)

    correct_response(response)
    assert 'user' in response.json()
    user_data = response.json()['user']
    assert 'id' in user_data and user_data['id'] == 1
    assert 'name' in user_data and isinstance(user_data['name'], str)
    assert 'followers' in user_data and isinstance(user_data['followers'], list)
    assert 'following' in user_data and isinstance(user_data['following'], list)


@pytest.mark.asyncio
async def test_fail_get_unauthorized_user(async_app_client):
    header = {'api-key': ""}
    response = await async_app_client.get("/api/users/me", headers=header)
    assert response.status_code == 404
    assert 'detail' in response.json() and response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_get_another_user(async_app_client):
    header = {'api-key': "test"}
    another_user_id = 2
    response = await async_app_client.get(f"/api/users/{another_user_id}", headers=header)
    correct_response(response)
    assert 'user' in response.json()
    user_data = response.json()['user']
    assert 'id' in user_data and user_data['id'] == 2
    assert 'name' in user_data and isinstance(user_data['name'], str)
    assert 'followers' in user_data and isinstance(user_data['followers'], list)
    assert 'following' in user_data and isinstance(user_data['following'], list)


@pytest.mark.asyncio
async def test_fail_get_missing_user(async_app_client):
    header = {'api-key': "test"}
    another_user_id = 999
    response = await async_app_client.get(f"/api/users/{another_user_id}", headers=header)
    assert response.status_code == 404
    assert 'detail' in response.json() and response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_save_media(async_app_client):
    get_cat = await async_app_client.get("https://cataas.com/cat")
    cat_image = get_cat.read()
    files = {'file': ('cat.jpg', cat_image, 'image/jpeg')}
    response = await async_app_client.post('/api/medias', files=files)
    correct_response(response)
    assert 'media_id' in response.json() and response.json()['media_id'] == 1


@pytest.mark.asyncio
async def test_post_tweet_without_media(async_app_client):
    header = {'api-key': 'test'}
    tweet_data = {'tweet_data': 'new test tweet', 'tweet_media_ids': []}
    response = await async_app_client.post('/api/tweets', json=tweet_data, headers=header)
    correct_response(response)
    assert 'tweet_id' in response.json() and isinstance(response.json()['tweet_id'], int)


@pytest.mark.asyncio
async def test_post_tweet_with_media(async_app_client, db_session):
    header = {'api-key': 'test'}
    post_request = await db_session.execute(select(func.count(Post.id)))
    post_count = post_request.scalar_one()
    get_cat = await async_app_client.get("https://cataas.com/cat")
    cat_image = get_cat.read()
    files = {'file': ('cat.jpg', cat_image, 'image/jpeg')}
    media_response = await async_app_client.post('/api/medias', files=files)
    media_id = media_response.json()['media_id']
    tweet_data = {'tweet_data': 'new test tweet', 'tweet_media_ids': [media_id]}
    response = await async_app_client.post('/api/tweets', json=tweet_data, headers=header)
    correct_response(response)
    assert 'tweet_id' in response.json() and isinstance(response.json()['tweet_id'], int)
    new_post_request = await db_session.execute(select(func.count(Post.id)))
    assert new_post_request.scalar_one() == post_count + 1


@pytest.mark.asyncio
async def test_delete_tweet(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    delete_tweet = await async_app_client.delete(f"/api/tweets/{tweet_id}", headers=header)
    correct_response(delete_tweet)


@pytest.mark.asyncio
async def test_wrong_user_delete_tweet(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    wrong_header = {'api-key': 'test-1'}
    delete_tweet = await async_app_client.delete(f"/api/tweets/{tweet_id}", headers=wrong_header)
    assert delete_tweet.status_code == 403
    assert 'detail' in delete_tweet.json() and delete_tweet.json()['detail'] == 'Forbidden'


@pytest.mark.asyncio
async def test_missing_user_delete_tweet(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    wrong_header = {'api-key': 'test-999'}
    delete_tweet = await async_app_client.delete(f"/api/tweets/{tweet_id}", headers=wrong_header)
    assert delete_tweet.status_code == 404
    assert 'detail' in delete_tweet.json() and delete_tweet.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_missing_tweet_delete_tweet(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    delete_tweet = await async_app_client.delete(f"/api/tweets/{tweet_id + 1}", headers=header)
    assert delete_tweet.status_code == 404
    assert 'detail' in delete_tweet.json() and delete_tweet.json()['detail'] == 'Tweet not found'


@pytest.mark.asyncio
async def test_post_like(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    post_like = await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    correct_response(post_like)


@pytest.mark.asyncio
async def test_repeated_post_like(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    post_second_like = await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    assert post_second_like.status_code == 404
    assert 'detail' in post_second_like.json()
    assert post_second_like.json()['detail'] == 'You have already liked this tweet'


@pytest.mark.asyncio
async def test_delete_like(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    delete_like = await async_app_client.delete(f"/api/tweets/{tweet_id}/likes", headers=header)
    correct_response(delete_like)


@pytest.mark.asyncio
async def test_delete_like_wrong_user(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    wrong_header = {'api-key': 'test-1'}
    delete_like = await async_app_client.delete(f"/api/tweets/{tweet_id}/likes", headers=wrong_header)
    assert delete_like.status_code == 404
    assert 'detail' in delete_like.json() and delete_like.json()['detail'] == 'Like not found'


@pytest.mark.asyncio
async def test_delete_like_missing_user(async_app_client, user_post_tweet):
    tweet_id, header = user_post_tweet
    await async_app_client.post(f"/api/tweets/{tweet_id}/likes", headers=header)
    wrong_header = {'api-key': 'test-999'}
    delete_like = await async_app_client.delete(f"/api/tweets/{tweet_id}/likes", headers=wrong_header)
    assert delete_like.status_code == 404
    assert 'detail' in delete_like.json() and delete_like.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_follow_user(async_app_client, db_session, add_new_user):
    header, new_user_id = add_new_user
    new_follower = await async_app_client.post(f"/api/users/{new_user_id}/follow", headers=header)
    correct_response(new_follower)


@pytest.mark.asyncio
async def test_repeated_follow_user(async_app_client, db_session, add_new_user):
    header, new_user_id = add_new_user
    await async_app_client.post(f"/api/users/{new_user_id}/follow", headers=header)
    new_repeated_follower = await async_app_client.post(f"/api/users/{new_user_id}/follow", headers=header)
    assert new_repeated_follower.status_code == 400
    assert 'detail' in new_repeated_follower.json()
    assert new_repeated_follower.json()['detail'] == 'You have already subscribed to this user'


@pytest.mark.asyncio
async def test_delete_follow_user(async_app_client, db_session, add_new_user):
    header, new_user_id = add_new_user
    await async_app_client.post(f"/api/users/{new_user_id}/follow", headers=header)
    delete_follower = await async_app_client.delete(f"/api/users/{new_user_id}/follow", headers=header)
    correct_response(delete_follower)


@pytest.mark.asyncio
async def test_delete_follow_user(async_app_client, db_session, add_new_user):
    header, new_user_id = add_new_user
    delete_follower = await async_app_client.delete(f"/api/users/{new_user_id}/follow", headers=header)
    assert delete_follower.status_code == 404
    assert 'detail' in delete_follower.json()
    assert delete_follower.json()['detail'] == 'Subscription not found'


@pytest.mark.app_func
async def test_app_get_user_by_api_key(db_session):
    user = await get_user_by_filter(db=db_session, api_key='test')
    assert isinstance(user, User) and user.id == 1


@pytest.mark.app_func
async def test_app_get_user_by_id(db_session):
    user = await get_user_by_filter(db=db_session, user_id=2)
    assert isinstance(user, User) and user.api_key == 'test-1'


@pytest.mark.app_func
async def test_app_get_user_by_wrong_api_key(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await get_user_by_filter(db=db_session, api_key='test-999')
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.app_func
async def test_app_get_user_by_wrong_id(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await get_user_by_filter(db=db_session, user_id=11)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.app_func
async def test_get_user_and_tweet(db_session):
    data = await get_user_and_tweet(tweet_id=1, user_api_key='test', db=db_session)
    assert isinstance(data, Tuple)
    assert isinstance(data[0], User) and data[0].id == 1
    assert isinstance(data[1], Post) and data[1].user_id == 1


@pytest.mark.app_func
async def test_get_user_and_missing_tweet(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await get_user_and_tweet(tweet_id=100, user_api_key='test', db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tweet not found"
