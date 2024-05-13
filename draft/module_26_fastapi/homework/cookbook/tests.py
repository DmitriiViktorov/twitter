from fastapi.testclient import TestClient
import pytest
import asyncio
from main import app

RECIPE_LIST_KEYS = ["title", "cooking_time", "views"]
SINGLE_RECIPE_KEYS = ['title', 'cooking_time', 'views', 'description', 'vegan', 'calories',
                      'proteins', 'fats', 'carbohydrates', 'released', 'id', 'ingredients']

@pytest.fixture(scope='session')
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


client = TestClient(app)


def test_recipe_list():
    """
    Тест для проверки получения списка рецептов
    Проверка успешного получения списка рецептов из базы данных
    Проверка наличия установленных заголовков в ответе
    """
    response = client.get("/recipe/")
    assert response.status_code == 200
    assert all(key in response.json()[0] for key in RECIPE_LIST_KEYS)


def test_recipe_detail():
    """
    Тест для проверки получения рецепта по id
    Проверка успешного получения рецепта из базы данных по id
    Проверка наличия установленных заголовков в ответе
    Проверка увеличения атрибута 'views' в результате предыдущего запроса
    """
    response = client.get("/recipe/1/")
    current_views = int(response.json()["views"])
    assert response.status_code == 200
    assert all(key in response.json() for key in SINGLE_RECIPE_KEYS)
    next_response = client.get("/recipe/1/")
    assert next_response.json()['views'] == current_views + 1


def test_post_and_delete_recipe():
    """
    Тест для проверки сразу нескольких эндпоинтов.
    В данном тесте выполняется следующий алгоритм:
    1) Инициализация данных для создания нового рецепта
    2) Создание нового рецепта с помощью обращения к эндпоинту /recipe с методом POST в котором передаются данные для
    создания новой записи в базе данных
    3) Присваивание переменной значения id только что добавленного рецепта
    4) Получение нового рецепта из базы данных с помощью обращения к эндпоинту /recipe/{recipe_id} с методом GET
    5) Сравнение название тестового рецепта и названия рецепта, полученного из базы данных по id нового рецепта
    6) Обращение к эндпоинту /recipe с методом GET для получения списка всех рецептов
    7) Проверка наличия названия нового рецепта в списке всех рецептов
    8) Удаление рецепта из базы данных
    9) Проверка статус кода, полученного от эндпоинта
    10) Проверка отсутствия в базе данных рецепта с полученным ранее id
    """
    test_recipe = {
            "title": "Test Recipe",
            "cooking_time": 0,
            "views": 0,
            "description": "Test Description",
            "vegan": False,
            "calories": 0,
            "proteins": 0,
            "fats": 0,
            "carbohydrates": 0
        }
    post_new_recipe = client.post("/recipe/", json=test_recipe)
    assert post_new_recipe.status_code == 201

    new_recipe_id = int(post_new_recipe.json()["id"])
    get_new_recipe = client.get(f"/recipe/{new_recipe_id}")
    assert get_new_recipe.json()["title"] == test_recipe["title"]

    get_updated_recipe_list = client.get('/recipe/')
    recipe_titles = [recipe['title'] for recipe in get_updated_recipe_list.json()]
    assert test_recipe["title"] in recipe_titles

    delete_recipe = client.delete(f"/recipe/{new_recipe_id}")
    assert delete_recipe.status_code == 204
    get_new_recipe_again = client.get(f"/recipe/{new_recipe_id}")
    assert get_new_recipe_again.status_code == 404


def test_post_and_patch_recipe():
    """
    Тест для проверки сразу нескольких эндпоинтов.
    В данном тесте выполняется следующий алгоритм:
    1) Инициализация данных для создания нового рецепта
    2) Создание нового рецепта с помощью обращения к эндпоинту /recipe с методом POST в котором передаются данные для
    создания новой записи в базе данных
    3) Присваивание переменной значения id только что добавленного рецепта
    4) Получение нового рецепта из базы данных с помощью обращения к эндпоинту /recipe/{recipe_id} с методом GET
    5) Сравнение название тестового рецепта и названия рецепта, полученного из базы данных по id нового рецепта
    6) Обновление названия нового рецепта с помощью обращения к эндпоинту /recipe с методом PATCH
    7) Проверка успешности выполнения обновления названия и проверка получения сообщения в ответе
    8) Получение обновленного рецепта из базы данных с помощью обращения к эндпоинту /recipe/{recipe_id} с методом GET
    9) Проверка обновления названия рецепта
    10) Удаление рецепта из базы данных
    """
    test_recipe = {
            "title": "New Test Recipe",
            "cooking_time": 0,
            "views": 0,
            "description": "Test Description",
            "vegan": False,
            "calories": 0,
            "proteins": 0,
            "fats": 0,
            "carbohydrates": 0
        }
    post_new_recipe = client.post("/recipe/", json=test_recipe)
    assert post_new_recipe.status_code == 201

    new_recipe_id = int(post_new_recipe.json()["id"])

    get_new_recipe = client.get(f"/recipe/{new_recipe_id}")
    assert get_new_recipe.json()["title"] == test_recipe["title"]

    new_recipe_title = {'title': "Updated Test Recipe"}
    patch_new_recipe = client.patch(f"/recipe/{new_recipe_id}", json=new_recipe_title)
    assert patch_new_recipe.status_code == 200
    assert patch_new_recipe.json()['status'] == "Recipe updated"

    get_new_recipe = client.get(f"/recipe/{new_recipe_id}")
    assert get_new_recipe.json()["title"] == new_recipe_title["title"]

    client.delete(f"/recipe/{new_recipe_id}")






