from fastapi import APIRouter
from ai.models.xgboost_model import XGBoostModel
import json

router = APIRouter()

@router.get("/api/brain/feature_importance")
async def get_feature_importance():
    model = XGBoostModel()
    importance = model.get_feature_importance()
    return {"features": importance}
