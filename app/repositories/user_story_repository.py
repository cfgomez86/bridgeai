from typing import Optional
from sqlalchemy.orm import Session
from app.models.user_story import UserStory


class UserStoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, story: UserStory) -> UserStory:
        self._db.add(story)
        self._db.commit()
        self._db.refresh(story)
        return story

    def find_by_id(self, story_id: str) -> Optional[UserStory]:
        return self._db.get(UserStory, story_id)

    def find_by_requirement_and_analysis(
        self, requirement_id: str, analysis_id: str
    ) -> Optional[UserStory]:
        return (
            self._db.query(UserStory)
            .filter(
                UserStory.requirement_id == requirement_id,
                UserStory.impact_analysis_id == analysis_id,
            )
            .first()
        )
