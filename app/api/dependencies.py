from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth0_auth import verify_auth0_jwt, _extract_bearer_token
from app.core.config import Settings, get_settings
from app.core.context import current_tenant_id, current_user_id
from app.database.session import get_db
from app.models.user import User
from app.repositories.incoherent_requirement_repository import IncoherentRequirementRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.ai_provider import get_ai_provider
from app.services.ai_requirement_parser import AIRequirementParser
from app.services.requirement_coherence_validator import get_coherence_validator
from app.services.requirement_understanding_service import RequirementUnderstandingService


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(request)
    payload = verify_auth0_jwt(token)

    auth0_user_id = payload.get("sub")
    if not auth0_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    user = db.query(User).filter_by(auth0_user_id=auth0_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned. Call POST /api/v1/auth/provision first.",
        )

    current_tenant_id.set(user.tenant_id)
    current_user_id.set(user.id)
    return user


def get_understanding_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RequirementUnderstandingService:
    repo = RequirementRepository(db)
    parser = AIRequirementParser(get_ai_provider(settings))
    validator = get_coherence_validator(settings)
    incoherent_repo = IncoherentRequirementRepository(db)
    return RequirementUnderstandingService(parser, repo, settings, validator, incoherent_repo)


def get_incoherent_requirement_repo(
    db: Session = Depends(get_db),
) -> IncoherentRequirementRepository:
    return IncoherentRequirementRepository(db)


def get_source_connection_repo(
    db: Session = Depends(get_db),
) -> SourceConnectionRepository:
    return SourceConnectionRepository(db)
