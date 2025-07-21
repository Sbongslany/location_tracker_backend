

from pydantic import BaseModel

class Location(BaseModel):
    user_id: int
    latitude: float
    longitude: float
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 5,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timestamp": "2025-07-20T13:17:00Z"
            }
        }