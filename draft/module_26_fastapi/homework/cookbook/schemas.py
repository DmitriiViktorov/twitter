from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BaseIngredient(BaseModel):
    name: str


class IngredientOut(BaseIngredient):
    id: int

    class Config:
        from_attributes = True


class RecipeIngredientSchema(BaseModel):
    quantity: int = Field(description="Amount of the ingredient in the definite recipe")

    class Config:
        from_attributes = True


class RecipeIngredientInner(RecipeIngredientSchema):
    ingredient: Optional[IngredientOut]


class RecipeIngredientOut(RecipeIngredientSchema):
    name: str = Field(..., description="Title of the ingredient")

    @classmethod
    def from_dict(cls, ingredient_dict: Dict[str, Any]):
        return cls(name=ingredient_dict['ingredient']['name'])


class RecipeListOut(BaseModel):
    title: str = Field(..., description="Title of the recipe")
    cooking_time: int = Field(..., description="The cooking time, an integer value, "
                                               "shows how many minutes it takes to cook a dish")
    views: int = Field(default=0, description="Number of views")


class BaseRecipe(RecipeListOut):
    description: str = Field(..., description="A brief description of the essence of the recipe")
    vegan: bool = Field(..., description="Is this a vegan or not (1/True is for vegan, 0/False is for non-vegan)")
    calories: float = Field(..., description="Calorie content")
    proteins: float = Field(..., description="Protein content")
    fats: float = Field(..., description="Fat content")
    carbohydrates: float = Field(..., description="Carbohydrate content")
    released: datetime = Field(default_factory=datetime.now, description="The timestamp of the recipe "
                                                                         "publication on the website")


class RecipeOut(BaseRecipe):
    id: int = Field(..., description="ID of recipe in DB")
    ingredients: List[RecipeIngredientInner]

    class Config:
        from_attributes = True
        populate_by_name = True

    def dict(self, **kwargs):
        data = super(BaseRecipe, self).dict(**kwargs)

        for a in data['ingredients']:
            a['name'] = a['ingredient']['name']
            del a['ingredient']

        return data


class RecipeResponseModel(BaseRecipe):
    id: int
    ingredients: List[RecipeIngredientOut] = Field(..., description="A list of ingredients that you need to "
                                                                    "purchase to prepare this dish")


class UpdateRecipeResponse(BaseModel):
    status: str
    recipe: RecipeResponseModel
