from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal

Region = Literal["north", "south", "east", "west"]
PreferenceType = Literal["dietary", "cuisine", "cooking_time", "none"]

class Preferences(BaseModel):
    number_of_people: int = Field(..., ge=1, le=20)
    spice_level: int = Field(..., ge=0, le=10)
    region_preference: Region
    preference_type: PreferenceType
    allergies: Optional[List[str]] = []
    dislikes: Optional[List[str]] = []

    @validator("allergies", "dislikes", pre=True)
    def ensure_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip().lower() for s in v.split(",") if s.strip()]
        return v
