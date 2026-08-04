from pydantic import BaseModel, Field


class SocketCompatibilityRequest(BaseModel):
    cpu_model: str = Field(min_length=1)
    cpu_socket: str = Field(min_length=1)
    motherboard_model: str = Field(min_length=1)
    motherboard_socket: str = Field(min_length=1)


class PartIdCompatibilityRequest(BaseModel):
    cpu_id: int = Field(gt=0)
    motherboard_id: int = Field(gt=0)


class MemoryCompatibilityRequest(BaseModel):
    motherboard_id: int = Field(gt=0)
    ram_id: int = Field(gt=0)


class CaseCompatibilityRequest(BaseModel):
    motherboard_id: int = Field(gt=0)
    case_id: int = Field(gt=0)


class GpuCaseCompatibilityRequest(BaseModel):
    gpu_id: int = Field(gt=0)
    case_id: int = Field(gt=0)


class PowerCompatibilityRequest(BaseModel):
    gpu_id: int = Field(gt=0)
    psu_id: int = Field(gt=0)


class FullBuildCompatibilityRequest(BaseModel):
    cpu_id: int = Field(gt=0)
    motherboard_id: int = Field(gt=0)
    ram_id: int = Field(gt=0)
    gpu_id: int = Field(gt=0)
    case_id: int = Field(gt=0)
    psu_id: int = Field(gt=0)


class CompatibilityResponse(BaseModel):
    compatible: bool
    message: str


class FullBuildCompatibilityResponse(BaseModel):
    compatible: bool
    total_price: int
    checks: list[str]
    errors: list[str]
