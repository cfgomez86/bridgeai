from abc import ABC, abstractmethod

from app.domain.ticket_integration import TicketResult
from app.domain.user_story import UserStory


class TicketProvider(ABC):
    @abstractmethod
    def create_ticket(
        self,
        story: UserStory,
        project_key: str,
        issue_type: str,
    ) -> TicketResult:
        ...

    @abstractmethod
    def get_ticket(self, external_id: str) -> TicketResult:
        ...

    @abstractmethod
    def validate_connection(self) -> bool:
        ...

    def build_payload(
        self, story: UserStory, project_key: str, issue_type: str
    ) -> dict | None:
        """Return the request payload that will be sent to the provider, for audit purposes.
        Override in concrete providers. Returns None by default."""
        return None
