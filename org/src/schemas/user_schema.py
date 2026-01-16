from pydantic import BaseModel
from enum import Enum
import uuid

class UserRole(str, Enum):
    ADMIN = "admin"
    REGIONAL_MANAGER = "regional_manager"
    CDC = "cdc"
    THERAPIST = "therapist"
    STAFF = "staff"

    @property
    def priority(self) -> int:
        priorities = {
            "admin": 100,
            "regional_manager": 50,
            "cdc": 40,
            "therapist": 30,
            "staff": 20,
        }
        return priorities.get(self.value, 0)


class UserPayload(BaseModel):
    id: uuid.UUID
    role: UserRole
