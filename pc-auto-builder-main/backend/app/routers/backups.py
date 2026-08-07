from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routers.parts import verify_admin_key
from app.services.part_backup import (
    export_parts_payload,
    get_backup_status,
    import_parts_payload,
    save_seed_file,
)


router = APIRouter(
    prefix="/backups",
    tags=["backups"],
)


class BackupImportRequest(BaseModel):
    payload: (
        dict[str, object]
        | list[dict[str, object]]
    )

    replace_existing: bool = False


@router.get(
    "/status",
    dependencies=[Depends(verify_admin_key)],
)
def backup_status() -> dict[str, object]:
    return get_backup_status()


@router.get(
    "/export",
    dependencies=[Depends(verify_admin_key)],
)
def export_backup() -> JSONResponse:
    payload = export_parts_payload()

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    filename = (
        f"pc-parts-backup-{timestamp}.json"
    )

    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


@router.post(
    "/save-seed",
    dependencies=[Depends(verify_admin_key)],
)
def save_seed() -> dict[str, object]:
    try:
        file_path = save_seed_file()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    payload = export_parts_payload()

    return {
        "message": (
            "현재 등록된 부품을 "
            "코드용 시드 파일로 저장했습니다."
        ),
        "file": str(file_path),
        "count": payload["count"],
    }


@router.post(
    "/import",
    dependencies=[Depends(verify_admin_key)],
)
def import_backup(
    request: BackupImportRequest,
) -> dict[str, object]:
    try:
        return import_parts_payload(
            payload=request.payload,
            replace_existing=(
                request.replace_existing
            ),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
