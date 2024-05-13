from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from contextlib import asynccontextmanager

from starlette import status

from models import Recipe, RecipeIngredient, Ingredient
from database import engine, session, Base
from schemas import RecipeOut, RecipeResponseModel, RecipeListOut, BaseRecipe, UpdateRecipeResponse

#
# @asynccontextmanager
# async def lifespan(application: FastAPI):
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield
#     await engine.dispose()
#
#
# app = FastAPI(lifespan=lifespan)


app = FastAPI()


@app.on_event("startup")
async def startup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown_db():
    await session.close()
    await engine.dispose()


@app.get("/recipe", response_model=List[RecipeListOut])
async def get_recipes():
    res = await session.execute(select(Recipe.title, Recipe.cooking_time, Recipe.views)
                                .order_by(desc(Recipe.views)).order_by(Recipe.cooking_time))
    return res.mappings().all()


@app.post("/recipe", response_model=RecipeResponseModel, status_code=status.HTTP_201_CREATED)
async def create_recipe(payload: BaseRecipe):
    recipe_data = payload.dict(exclude={"id", "ingredients"})
    new_recipe = Recipe(**recipe_data)
    session.add(new_recipe)
    await session.commit()
    query = select(Recipe).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
    ).where(Recipe.title == payload.title)
    result = await session.execute(query)
    recipe = result.unique().scalars().one()
    recipe_schema = RecipeOut.from_orm(recipe).dict()
    return recipe_schema


@app.patch("/recipe/{recipe_id}", response_model=UpdateRecipeResponse, status_code=status.HTTP_200_OK)
async def update_recipe(recipe_id: int, payload: dict):
    recipe = await session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    for k, v in payload.items():
        if hasattr(recipe, k) and k not in ["id", "released", 'views']:
            setattr(recipe, k, v)

    session.add(recipe)
    await session.commit()

    query = select(Recipe).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
    ).where(Recipe.id == recipe_id)
    result = await session.execute(query)
    recipe = result.unique().scalars().one()
    recipe_schema = RecipeOut.from_orm(recipe).dict()
    return {"status": "Recipe updated", "recipe": recipe_schema}


@app.delete("/recipe/{recipe_id}", status_code=204)
async def delete_recipe(recipe_id: int):
    recipe = await session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    await session.delete(recipe)
    await session.commit()

    return None



@app.get("/recipe/{recipe_id}", response_model_by_alias=False, response_model=RecipeResponseModel)
async def get_recipe(recipe_id: int):
    check_recipe = await session.get(Recipe, recipe_id)
    if not check_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    query = select(Recipe).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
    ).where(Recipe.id == recipe_id)

    result = await session.execute(query)
    recipe = result.unique().scalars().one()

    recipe_schema = RecipeOut.from_orm(recipe).dict()

    recipe.views += 1
    await session.commit()
    return recipe_schema

