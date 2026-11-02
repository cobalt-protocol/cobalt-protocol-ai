from fastapi import APIRouter, Depends, status
from app.utils.middlewares import verify_auth_token
from app.controllers import RecomendationTeamControllers
from app.schemas.recomendation_team import TeamRecommendationResponse, TeamRecommendationByIdResponse

router = APIRouter()
recomendation_team_controller = RecomendationTeamControllers()


@router.get(
    "/recommendation-team/{competition_id}",
    status_code=status.HTTP_200_OK,
    response_model=TeamRecommendationResponse,
)
async def get_recomendation_team(
    competition_id: str,
    current_user: str = Depends(verify_auth_token),
):
    return await recomendation_team_controller.recomendation_team(
        current_user, competition_id
    )


@router.get(
    "/recommendation-team/{competition_id}/{team_id}",
    status_code=status.HTTP_200_OK,
    response_model=TeamRecommendationByIdResponse,
)
async def get_recomendation_team_by_id(
    competition_id: str,
    team_id: str,
    current_user: str = Depends(verify_auth_token),
):
    return await recomendation_team_controller.recomendation_team_by_team_id(
        current_user, competition_id, team_id
    )


