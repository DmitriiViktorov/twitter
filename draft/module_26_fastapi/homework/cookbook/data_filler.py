from models import Recipe, Ingredient, RecipeIngredient
from schemas import BaseRecipe, BaseIngredient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


engine = create_engine('sqlite:///./recipe.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


def add_sample_data(session: Session):
    sample_recipes = [
        BaseRecipe(title="Oatmeal", description="Healthy breakfast", calories=300, proteins=10, fats=5, carbohydrates=50, cooking_time=15, vegan=True),
        BaseRecipe(title="Scrambled eggs", description="Quick breakfast", calories=200, proteins=15, fats=15, carbohydrates=1, cooking_time=10, vegan=False),
        BaseRecipe(title="Spaghetti Bolognese", description="Classic dinner", calories=500, proteins=20, fats=20, carbohydrates=70, cooking_time=30, vegan=False),
    ]

    sample_ingredients = [
        BaseIngredient(name="oats"),
        BaseIngredient(name="milk"),
        BaseIngredient(name="eggs"),
        BaseIngredient(name="butter"),
        BaseIngredient(name="spaghetti"),
        BaseIngredient(name="beef"),
        BaseIngredient(name="tomato sauce"),
    ]

    for recipe in sample_recipes:
        session.add(Recipe(**recipe.dict()))

    for ingredient in sample_ingredients:
        session.add(Ingredient(**ingredient.dict()))

    session.commit()


def add_recipe_ingredients_rel(session: Session):
    recipe_1 = session.query(Recipe).filter(Recipe.title == "Oatmeal").first()
    ingredient_1 = session.query(Ingredient).filter(Ingredient.name == "oats").first()
    ingredient_2 = session.query(Ingredient).filter(Ingredient.name == "milk").first()

    recipe_ingredient_1 = RecipeIngredient(recipe_id=recipe_1.id, ingredient_id=ingredient_1.id, quantity=100.0)
    recipe_ingredient_2 = RecipeIngredient(recipe_id=recipe_1.id, ingredient_id=ingredient_2.id, quantity=400.0)
    session.add(recipe_ingredient_1)
    session.add(recipe_ingredient_2)

    session.commit()


if __name__ == "__main__":
    add_sample_data(session)
    add_recipe_ingredients_rel(session)
