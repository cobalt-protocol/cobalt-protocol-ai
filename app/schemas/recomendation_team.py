from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class TeamItem(BaseModel):
    # ===== Team =====
    team_id: str
    team_name: str
    visibility: bool
    team_description: Optional[str] = None
    tx_hash: Optional[str] = None
    team_created_at: datetime
    team_updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # ===== Competition =====
    competition_id: Optional[str] = None
    competition_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    requirement: Optional[str] = None
    formation: Optional[str] = None
    format: Optional[str] = None
    registration_window: Optional[datetime] = None
    competition_window: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    judging_review: Optional[datetime] = None
    result_announcement: Optional[datetime] = None
    pirze_certificate_claim: Optional[datetime] = None
    certificate_cid: Optional[str] = None
    guidebook_cid: Optional[str] = None
    fee: Optional[int] = None
    fee_token_address: Optional[str] = None
    price_competition_id: Optional[str] = None
    indexer_state_id: Optional[str] = None

    persentage: str

    class Config:
        from_attributes = True


class TeamRecommendationResponse(BaseModel):
    data: List[TeamItem]
    message: str
    errors: Optional[Any] = None
