from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from database import Base


class RecipeIngredient(Base):
    __tablename__ = 'recipe_ingredients'

    recipe_id = Column(ForeignKey('recipes.id'), primary_key=True)
    ingredient_id = Column(ForeignKey('ingredients.id'), primary_key=True)

    quantity = Column(Float, default=0)

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipes")

    ingredient_name = association_proxy(target_collection='ingredient', attr='name')
    recipe_title = association_proxy(target_collection='recipe', attr='title')


class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, unique=True)
    description = Column(Text)
    vegan = Column(Boolean, index=True, default=False)
    calories = Column(Float)
    proteins = Column(Float)
    fats = Column(Float)
    carbohydrates = Column(Float)
    cooking_time = Column(Integer)
    released = Column(DateTime)
    views = Column(Integer, default=0)

    ingredients = relationship("RecipeIngredient", back_populates="recipe")
    ingredient_quantity = association_proxy('ingredients', 'quantity')


class Ingredient(Base):
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)

    recipes = relationship("RecipeIngredient", back_populates="ingredient")


