from dataclasses import dataclass
from typing import Literal


AppMode = Literal["Individual", "Industry"]
AppRole = Literal["user", "developer"]


@dataclass(frozen=True)
class AppSession:
    user_id: int
    full_name: str
    email: str
    location: str
    mode: AppMode
    role: AppRole


