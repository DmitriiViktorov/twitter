from typing import List
from fastapi import FastAPI, Depends

from sqlalchemy import desc
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from models import Recipe, RecipeIngredient
from database import session
from schemas import RecipeOut, RecipeResponseModel, RecipeListOut



async def get_db():
    try:
        yield session
    finally:
        session.close()

app = FastAPI()


@app.get("/recipe", response_model=List[RecipeListOut])
async def get_recipes(session=Depends(get_db)):
    res = await session.execute(select(Recipe.title, Recipe.cooking_time, Recipe.views)
                                .order_by(desc(Recipe.views)).order_by(Recipe.cooking_time))
    return res.mappings().all()


@app.get("/recipe/{recipe_id}", response_model_by_alias=False, response_model=RecipeResponseModel)
async def get_recipe(recipe_id: int, session=Depends(get_db)):
    query = select(Recipe).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
    ).where(Recipe.id == recipe_id)
    result = await session.execute(query)
    recipe = result.unique().scalars().one()
    recipe_schema = RecipeOut.from_orm(recipe).dict()

    recipe.views += 1
    await session.commit()

    return recipe_schema
