from fastapi import APIRouter, HTTPException

from app.data.parts import find_part_by_id
from app.schemas.compatibility import (
    CaseCompatibilityRequest,
    CompatibilityResponse,
    FullBuildCompatibilityRequest,
    FullBuildCompatibilityResponse,
    GpuCaseCompatibilityRequest,
    MemoryCompatibilityRequest,
    PartIdCompatibilityRequest,
    PowerCompatibilityRequest,
    SocketCompatibilityRequest,
)


router = APIRouter(
    prefix="/compatibility",
    tags=["compatibility"],
)


def get_part_or_404(
    part_id: int,
    part_name: str,
) -> dict[str, object]:
    part = find_part_by_id(part_id)

    if part is None:
        raise HTTPException(
            status_code=404,
            detail=f"{part_name}을 찾을 수 없습니다.",
        )

    return part


def require_category(
    part: dict[str, object],
    required_category: str,
    field_name: str,
) -> None:
    if part.get("category") != required_category:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_name}에는 "
                f"{required_category} 부품 ID를 입력해야 합니다."
            ),
        )


def get_specifications(
    part: dict[str, object],
    part_name: str,
) -> dict[str, object]:
    specifications = part.get("specifications")

    if not isinstance(specifications, dict):
        raise HTTPException(
            status_code=500,
            detail=f"{part_name} 규격 정보가 올바르지 않습니다.",
        )

    return specifications


def get_price(part: dict[str, object]) -> int:
    price = part.get("price")

    if not isinstance(price, int):
        raise HTTPException(
            status_code=500,
            detail="부품 가격 정보가 올바르지 않습니다.",
        )

    return price


def normalize(value: object) -> str:
    return str(value).strip().upper()


@router.post(
    "/socket",
    response_model=CompatibilityResponse,
)
def check_socket_compatibility(
    request: SocketCompatibilityRequest,
) -> CompatibilityResponse:
    cpu_socket = normalize(request.cpu_socket)
    motherboard_socket = normalize(request.motherboard_socket)

    compatible = cpu_socket == motherboard_socket

    if compatible:
        message = (
            f"{request.cpu_model}과 "
            f"{request.motherboard_model}은 호환됩니다."
        )
    else:
        message = (
            f"CPU 소켓은 {cpu_socket}이지만 "
            f"메인보드 소켓은 {motherboard_socket}입니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/by-id",
    response_model=CompatibilityResponse,
)
def check_cpu_motherboard_by_id(
    request: PartIdCompatibilityRequest,
) -> CompatibilityResponse:
    cpu = get_part_or_404(request.cpu_id, "CPU")
    motherboard = get_part_or_404(
        request.motherboard_id,
        "메인보드",
    )

    require_category(cpu, "cpu", "cpu_id")
    require_category(
        motherboard,
        "motherboard",
        "motherboard_id",
    )

    cpu_specs = get_specifications(cpu, "CPU")
    motherboard_specs = get_specifications(
        motherboard,
        "메인보드",
    )

    cpu_socket = normalize(cpu_specs.get("socket", ""))
    motherboard_socket = normalize(
        motherboard_specs.get("socket", "")
    )

    compatible = cpu_socket == motherboard_socket

    if compatible:
        message = (
            f"{cpu['model_name']}과 "
            f"{motherboard['model_name']}은 호환됩니다."
        )
    else:
        message = (
            f"CPU는 {cpu_socket}, 메인보드는 "
            f"{motherboard_socket} 소켓입니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/memory-by-id",
    response_model=CompatibilityResponse,
)
def check_memory_by_id(
    request: MemoryCompatibilityRequest,
) -> CompatibilityResponse:
    motherboard = get_part_or_404(
        request.motherboard_id,
        "메인보드",
    )
    ram = get_part_or_404(request.ram_id, "RAM")

    require_category(
        motherboard,
        "motherboard",
        "motherboard_id",
    )
    require_category(ram, "ram", "ram_id")

    motherboard_specs = get_specifications(
        motherboard,
        "메인보드",
    )
    ram_specs = get_specifications(ram, "RAM")

    motherboard_ram_type = normalize(
        motherboard_specs.get("ram_type", "")
    )
    ram_type = normalize(
        ram_specs.get("ram_type", "")
    )

    compatible = motherboard_ram_type == ram_type

    if compatible:
        message = (
            f"메인보드와 RAM 모두 "
            f"{ram_type} 규격입니다."
        )
    else:
        message = (
            f"메인보드는 {motherboard_ram_type}, "
            f"RAM은 {ram_type} 규격입니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/case-by-id",
    response_model=CompatibilityResponse,
)
def check_motherboard_case_by_id(
    request: CaseCompatibilityRequest,
) -> CompatibilityResponse:
    motherboard = get_part_or_404(
        request.motherboard_id,
        "메인보드",
    )
    computer_case = get_part_or_404(
        request.case_id,
        "케이스",
    )

    require_category(
        motherboard,
        "motherboard",
        "motherboard_id",
    )
    require_category(
        computer_case,
        "case",
        "case_id",
    )

    motherboard_specs = get_specifications(
        motherboard,
        "메인보드",
    )
    case_specs = get_specifications(
        computer_case,
        "케이스",
    )

    form_factor = normalize(
        motherboard_specs.get("form_factor", "")
    )

    supported = case_specs.get(
        "supported_form_factors",
        []
    )

    if not isinstance(supported, list):
        raise HTTPException(
            status_code=500,
            detail="케이스 규격 정보가 올바르지 않습니다.",
        )

    supported_normalized = [
        normalize(value)
        for value in supported
    ]

    compatible = form_factor in supported_normalized

    if compatible:
        message = (
            f"케이스가 {form_factor} 메인보드를 "
            f"지원합니다."
        )
    else:
        message = (
            f"케이스가 {form_factor} 메인보드를 "
            f"지원하지 않습니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/gpu-case-by-id",
    response_model=CompatibilityResponse,
)
def check_gpu_case_by_id(
    request: GpuCaseCompatibilityRequest,
) -> CompatibilityResponse:
    gpu = get_part_or_404(request.gpu_id, "그래픽카드")
    computer_case = get_part_or_404(
        request.case_id,
        "케이스",
    )

    require_category(gpu, "gpu", "gpu_id")
    require_category(
        computer_case,
        "case",
        "case_id",
    )

    gpu_specs = get_specifications(
        gpu,
        "그래픽카드",
    )
    case_specs = get_specifications(
        computer_case,
        "케이스",
    )

    gpu_length = gpu_specs.get("length_mm")
    max_gpu_length = case_specs.get(
        "max_gpu_length_mm"
    )

    if not isinstance(gpu_length, int):
        raise HTTPException(
            status_code=500,
            detail="그래픽카드 길이 정보가 없습니다.",
        )

    if not isinstance(max_gpu_length, int):
        raise HTTPException(
            status_code=500,
            detail="케이스의 최대 GPU 길이 정보가 없습니다.",
        )

    compatible = gpu_length <= max_gpu_length

    if compatible:
        message = (
            f"그래픽카드 길이는 {gpu_length}mm이고 "
            f"케이스는 {max_gpu_length}mm까지 지원합니다."
        )
    else:
        message = (
            f"그래픽카드 길이는 {gpu_length}mm이지만 "
            f"케이스는 {max_gpu_length}mm까지만 지원합니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/power-by-id",
    response_model=CompatibilityResponse,
)
def check_power_by_id(
    request: PowerCompatibilityRequest,
) -> CompatibilityResponse:
    gpu = get_part_or_404(request.gpu_id, "그래픽카드")
    psu = get_part_or_404(request.psu_id, "파워")

    require_category(gpu, "gpu", "gpu_id")
    require_category(psu, "psu", "psu_id")

    gpu_specs = get_specifications(
        gpu,
        "그래픽카드",
    )
    psu_specs = get_specifications(psu, "파워")

    recommended_psu = gpu_specs.get(
        "recommended_psu_w"
    )
    psu_wattage = psu_specs.get("wattage")

    if not isinstance(recommended_psu, int):
        raise HTTPException(
            status_code=500,
            detail="그래픽카드 권장 파워 정보가 없습니다.",
        )

    if not isinstance(psu_wattage, int):
        raise HTTPException(
            status_code=500,
            detail="파워 용량 정보가 없습니다.",
        )

    compatible = psu_wattage >= recommended_psu

    if compatible:
        message = (
            f"권장 파워는 {recommended_psu}W이며 "
            f"선택한 파워는 {psu_wattage}W입니다."
        )
    else:
        message = (
            f"권장 파워는 {recommended_psu}W이지만 "
            f"선택한 파워는 {psu_wattage}W입니다."
        )

    return CompatibilityResponse(
        compatible=compatible,
        message=message,
    )


@router.post(
    "/full-build",
    response_model=FullBuildCompatibilityResponse,
)
def check_full_build(
    request: FullBuildCompatibilityRequest,
) -> FullBuildCompatibilityResponse:
    cpu = get_part_or_404(request.cpu_id, "CPU")
    motherboard = get_part_or_404(
        request.motherboard_id,
        "메인보드",
    )
    ram = get_part_or_404(request.ram_id, "RAM")
    gpu = get_part_or_404(
        request.gpu_id,
        "그래픽카드",
    )
    computer_case = get_part_or_404(
        request.case_id,
        "케이스",
    )
    psu = get_part_or_404(request.psu_id, "파워")

    require_category(cpu, "cpu", "cpu_id")
    require_category(
        motherboard,
        "motherboard",
        "motherboard_id",
    )
    require_category(ram, "ram", "ram_id")
    require_category(gpu, "gpu", "gpu_id")
    require_category(
        computer_case,
        "case",
        "case_id",
    )
    require_category(psu, "psu", "psu_id")

    cpu_specs = get_specifications(cpu, "CPU")
    motherboard_specs = get_specifications(
        motherboard,
        "메인보드",
    )
    ram_specs = get_specifications(ram, "RAM")
    gpu_specs = get_specifications(
        gpu,
        "그래픽카드",
    )
    case_specs = get_specifications(
        computer_case,
        "케이스",
    )
    psu_specs = get_specifications(psu, "파워")

    checks: list[str] = []
    errors: list[str] = []

    cpu_socket = normalize(
        cpu_specs.get("socket", "")
    )
    motherboard_socket = normalize(
        motherboard_specs.get("socket", "")
    )

    if cpu_socket == motherboard_socket:
        checks.append(
            f"CPU와 메인보드 소켓 일치: {cpu_socket}"
        )
    else:
        errors.append(
            f"CPU 소켓 {cpu_socket}과 "
            f"메인보드 소켓 {motherboard_socket} 불일치"
        )

    motherboard_ram_type = normalize(
        motherboard_specs.get("ram_type", "")
    )
    ram_type = normalize(
        ram_specs.get("ram_type", "")
    )

    if motherboard_ram_type == ram_type:
        checks.append(
            f"메인보드와 RAM 규격 일치: {ram_type}"
        )
    else:
        errors.append(
            f"메인보드는 {motherboard_ram_type}, "
            f"RAM은 {ram_type}"
        )

    motherboard_form_factor = normalize(
        motherboard_specs.get("form_factor", "")
    )

    supported_form_factors = case_specs.get(
        "supported_form_factors",
        []
    )

    if not isinstance(supported_form_factors, list):
        raise HTTPException(
            status_code=500,
            detail="케이스 지원 규격 정보가 잘못되었습니다.",
        )

    normalized_supported = [
        normalize(value)
        for value in supported_form_factors
    ]

    if motherboard_form_factor in normalized_supported:
        checks.append(
            f"케이스가 {motherboard_form_factor} 메인보드 지원"
        )
    else:
        errors.append(
            f"케이스가 {motherboard_form_factor} 메인보드 미지원"
        )

    gpu_length = gpu_specs.get("length_mm")
    max_gpu_length = case_specs.get(
        "max_gpu_length_mm"
    )

    if not isinstance(gpu_length, int):
        raise HTTPException(
            status_code=500,
            detail="그래픽카드 길이 정보가 잘못되었습니다.",
        )

    if not isinstance(max_gpu_length, int):
        raise HTTPException(
            status_code=500,
            detail="케이스 GPU 길이 정보가 잘못되었습니다.",
        )

    if gpu_length <= max_gpu_length:
        checks.append(
            f"GPU 길이 사용 가능: "
            f"{gpu_length}mm / {max_gpu_length}mm"
        )
    else:
        errors.append(
            f"GPU가 케이스보다 큼: "
            f"{gpu_length}mm / {max_gpu_length}mm"
        )

    recommended_psu = gpu_specs.get(
        "recommended_psu_w"
    )
    psu_wattage = psu_specs.get("wattage")

    if not isinstance(recommended_psu, int):
        raise HTTPException(
            status_code=500,
            detail="그래픽카드 권장 파워 정보가 잘못되었습니다.",
        )

    if not isinstance(psu_wattage, int):
        raise HTTPException(
            status_code=500,
            detail="파워 용량 정보가 잘못되었습니다.",
        )

    if psu_wattage >= recommended_psu:
        checks.append(
            f"파워 용량 충분: "
            f"{psu_wattage}W / 권장 {recommended_psu}W"
        )
    else:
        errors.append(
            f"파워 용량 부족: "
            f"{psu_wattage}W / 권장 {recommended_psu}W"
        )

    selected_parts = [
        cpu,
        motherboard,
        ram,
        gpu,
        computer_case,
        psu,
    ]

    total_price = sum(
        get_price(part)
        for part in selected_parts
    )

    return FullBuildCompatibilityResponse(
        compatible=len(errors) == 0,
        total_price=total_price,
        checks=checks,
        errors=errors,
    )