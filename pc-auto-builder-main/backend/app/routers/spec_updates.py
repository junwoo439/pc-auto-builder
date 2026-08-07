
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, Field

from app.routers.parts import verify_admin_key
from app.services.danawa_spec_updater import (
    list_part_ids,
    update_parts,
)


router = APIRouter(
    prefix="/spec-updates",
    tags=["spec-updates"],
)


class SelectedSpecUpdateRequest(BaseModel):
    part_ids: list[int] = Field(
        min_length=1,
        max_length=5000,
    )


@router.post(
    "/selected",
    dependencies=[Depends(verify_admin_key)],
)
def update_selected_specs(
    request: SelectedSpecUpdateRequest,
) -> dict[str, object]:
    return update_parts(request.part_ids)


@router.post(
    "/all",
    dependencies=[Depends(verify_admin_key)],
)
def update_all_specs() -> dict[str, object]:
    part_ids = list_part_ids()

    if not part_ids:
        raise HTTPException(
            status_code=404,
            detail="갱신할 부품이 없습니다.",
        )

    return update_parts(part_ids)
