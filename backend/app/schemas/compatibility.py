from pydantic import BaseModel, Field


class SocketCompatibilityRequest(BaseModel):
    cpu_model: str = Field(min_length=1)
    cpu_socket: str = Field(min_length=1)
    motherboard_model: str = Field(min_length=1)
    motherboard_socket: str = Field(min_length=1)


class PartIdCompatibilityRequest(BaseModel):
    cpu_id: int = Field(gt=0)
    motherboard_id: int = Field(gt=0)


class CompatibilityResponse(BaseModel):
    compatible: bool
    message: str
