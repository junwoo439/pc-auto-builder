from fastapi import APIRouter, HTTPException

from app.data.parts import find_part_by_id
from app.schemas.compatibility import (
    CompatibilityResponse,
    PartIdCompatibilityRequest,
    SocketCompatibilityRequest,
)


router = APIRouter(
    prefix="/compatibility",
    tags=["compatibility"],
)


@router.post(
    "/socket",
    response_model=CompatibilityResponse,
)
def check_socket_compatibility(
    request: SocketCompatibilityRequest,
) -> CompatibilityResponse:
    """사용자가 입력한 CPU와 메인보드 소켓을 비교한다."""

    cpu_socket = request.cpu_socket.strip().upper()
    motherboard_socket = request.motherboard_socket.strip().upper()

    if cpu_socket == motherboard_socket:
        return CompatibilityResponse(
            compatible=True,
            message=(
                f"{request.cpu_model}과 "
                f"{request.motherboard_model}은 호환됩니다. "
                f"두 부품 모두 {cpu_socket} 소켓을 사용합니다."
            ),
        )

    return CompatibilityResponse(
        compatible=False,
        message=(
            f"{request.cpu_model}의 소켓은 {cpu_socket}이지만, "
            f"{request.motherboard_model}의 소켓은 "
            f"{motherboard_socket}입니다."
        ),
    )


@router.post(
    "/by-id",
    response_model=CompatibilityResponse,
)
def check_compatibility_by_id(
    request: PartIdCompatibilityRequest,
) -> CompatibilityResponse:
    """부품 ID로 CPU와 메인보드의 소켓 호환성을 검사한다."""

    cpu = find_part_by_id(request.cpu_id)

    if cpu is None:
        raise HTTPException(
            status_code=404,
            detail="CPU를 찾을 수 없습니다.",
        )

    motherboard = find_part_by_id(request.motherboard_id)

    if motherboard is None:
        raise HTTPException(
            status_code=404,
            detail="메인보드를 찾을 수 없습니다.",
        )

    if cpu["category"] != "cpu":
        raise HTTPException(
            status_code=400,
            detail="cpu_id에는 CPU 부품의 ID를 입력해야 합니다.",
        )

    if motherboard["category"] != "motherboard":
        raise HTTPException(
            status_code=400,
            detail=(
                "motherboard_id에는 메인보드 부품의 "
                "ID를 입력해야 합니다."
            ),
        )

    cpu_specifications = cpu.get("specifications")
    motherboard_specifications = motherboard.get("specifications")

    if not isinstance(cpu_specifications, dict):
        raise HTTPException(
            status_code=500,
            detail="CPU 규격 정보가 올바르지 않습니다.",
        )

    if not isinstance(motherboard_specifications, dict):
        raise HTTPException(
            status_code=500,
            detail="메인보드 규격 정보가 올바르지 않습니다.",
        )

    cpu_socket = str(
        cpu_specifications.get("socket", "")
    ).strip().upper()

    motherboard_socket = str(
        motherboard_specifications.get("socket", "")
    ).strip().upper()

    if not cpu_socket:
        raise HTTPException(
            status_code=400,
            detail="CPU의 소켓 정보가 없습니다.",
        )

    if not motherboard_socket:
        raise HTTPException(
            status_code=400,
            detail="메인보드의 소켓 정보가 없습니다.",
        )

    cpu_name = str(cpu["model_name"])
    motherboard_name = str(motherboard["model_name"])

    if cpu_socket == motherboard_socket:
        return CompatibilityResponse(
            compatible=True,
            message=(
                f"{cpu_name}과 {motherboard_name}은 호환됩니다. "
                f"두 부품 모두 {cpu_socket} 소켓입니다."
            ),
        )

    return CompatibilityResponse(
        compatible=False,
        message=(
            f"{cpu_name}의 소켓은 {cpu_socket}이지만, "
            f"{motherboard_name}의 소켓은 "
            f"{motherboard_socket}입니다."
        ),
    )