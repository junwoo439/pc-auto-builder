from itertools import product
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data.database import get_all_parts


router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


class RecommendationRequest(BaseModel):
    budget: int = Field(ge=100000)
    purpose: Literal["gaming", "balanced", "office"]

    max_width_mm: int = Field(gt=0)
    max_height_mm: int = Field(gt=0)
    max_depth_mm: int = Field(gt=0)


def get_specs(
    part: dict[str, object],
) -> dict[str, object]:
    specifications = part.get("specifications")

    if isinstance(specifications, dict):
        return specifications

    return {}


def normalize(value: object) -> str:
    return str(value).strip().upper()


def case_fits_dimensions(
    computer_case: dict[str, object],
    request: RecommendationRequest,
) -> bool:
    case_specs = get_specs(computer_case)

    width = case_specs.get("width_mm")
    height = case_specs.get("height_mm")
    depth = case_specs.get("depth_mm")

    if not isinstance(width, int):
        return False

    if not isinstance(height, int):
        return False

    if not isinstance(depth, int):
        return False

    return (
        width <= request.max_width_mm
        and height <= request.max_height_mm
        and depth <= request.max_depth_mm
    )


def is_compatible(
    parts: tuple[dict[str, object], ...],
    request: RecommendationRequest,
) -> bool:
    cpu, motherboard, ram, gpu, computer_case, psu = parts

    cpu_specs = get_specs(cpu)
    motherboard_specs = get_specs(motherboard)
    ram_specs = get_specs(ram)
    gpu_specs = get_specs(gpu)
    case_specs = get_specs(computer_case)
    psu_specs = get_specs(psu)

    cpu_socket = normalize(
        cpu_specs.get("socket", "")
    )

    motherboard_socket = normalize(
        motherboard_specs.get("socket", "")
    )

    if cpu_socket != motherboard_socket:
        return False

    motherboard_ram_type = normalize(
        motherboard_specs.get("ram_type", "")
    )

    ram_type = normalize(
        ram_specs.get("ram_type", "")
    )

    if motherboard_ram_type != ram_type:
        return False

    motherboard_form_factor = normalize(
        motherboard_specs.get("form_factor", "")
    )

    supported_form_factors = case_specs.get(
        "supported_form_factors",
        [],
    )

    if not isinstance(supported_form_factors, list):
        return False

    normalized_supported = [
        normalize(value)
        for value in supported_form_factors
    ]

    if motherboard_form_factor not in normalized_supported:
        return False

    gpu_length = gpu_specs.get("length_mm")
    max_gpu_length = case_specs.get(
        "max_gpu_length_mm"
    )

    if not isinstance(gpu_length, int):
        return False

    if not isinstance(max_gpu_length, int):
        return False

    if gpu_length > max_gpu_length:
        return False

    recommended_power = gpu_specs.get(
        "recommended_psu_w"
    )

    psu_power = psu_specs.get("wattage")

    if not isinstance(recommended_power, int):
        return False

    if not isinstance(psu_power, int):
        return False

    if psu_power < recommended_power:
        return False

    return case_fits_dimensions(
        computer_case,
        request,
    )


def calculate_score(
    parts: tuple[dict[str, object], ...],
    purpose: str,
) -> int:
    cpu, _, ram, gpu, _, _ = parts

    cpu_price = int(cpu.get("price", 0))
    gpu_price = int(gpu.get("price", 0))

    ram_capacity = int(
        get_specs(ram).get("capacity_gb", 0)
    )

    total_price = sum(
        int(part.get("price", 0))
        for part in parts
    )

    if purpose == "gaming":
        return (
            gpu_price * 5
            + cpu_price * 2
            + ram_capacity * 10000
            + total_price
        )

    if purpose == "office":
        return (
            cpu_price * 4
            + ram_capacity * 15000
            - total_price // 10
        )

    return (
        gpu_price * 3
        + cpu_price * 3
        + ram_capacity * 12000
        + total_price
    )


@router.post("/auto")
def recommend_build(
    request: RecommendationRequest,
) -> dict[str, object]:
    all_parts = get_all_parts()

    category_names = [
        "cpu",
        "motherboard",
        "ram",
        "gpu",
        "case",
        "psu",
    ]

    categories = [
        [
            part
            for part in all_parts
            if part.get("category") == category
        ]
        for category in category_names
    ]

    if any(not parts for parts in categories):
        return {
            "found": False,
            "message": "추천에 필요한 부품 데이터가 부족합니다.",
            "parts": [],
        }

    candidates: list[
        tuple[
            int,
            int,
            tuple[dict[str, object], ...],
        ]
    ] = []

    for selected_parts in product(*categories):
        if not is_compatible(
            selected_parts,
            request,
        ):
            continue

        total_price = sum(
            int(part.get("price", 0))
            for part in selected_parts
        )

        if total_price > request.budget:
            continue

        score = calculate_score(
            selected_parts,
            request.purpose,
        )

        candidates.append(
            (
                score,
                total_price,
                selected_parts,
            )
        )

    if not candidates:
        return {
            "found": False,
            "message": (
                "입력한 예산과 본체 크기를 모두 만족하는 "
                "호환 견적이 없습니다."
            ),
            "budget": request.budget,
            "requested_dimensions": {
                "width_mm": request.max_width_mm,
                "height_mm": request.max_height_mm,
                "depth_mm": request.max_depth_mm,
            },
            "parts": [],
        }

    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
        ),
        reverse=True,
    )

    _, total_price, selected_parts = candidates[0]

    result_parts = [
        {
            "id": part["id"],
            "category": part["category"],
            "manufacturer": part["manufacturer"],
            "model_name": part["model_name"],
            "price": part["price"],
            "specifications": get_specs(part),
        }
        for part in selected_parts
    ]

    selected_case = selected_parts[4]
    case_specs = get_specs(selected_case)

    return {
        "found": True,
        "message": (
            "예산, 용도, 본체 크기에 맞는 "
            "호환 견적을 찾았습니다."
        ),
        "budget": request.budget,
        "purpose": request.purpose,
        "total_price": total_price,
        "remaining_budget": (
            request.budget - total_price
        ),
        "requested_dimensions": {
            "width_mm": request.max_width_mm,
            "height_mm": request.max_height_mm,
            "depth_mm": request.max_depth_mm,
        },
        "case_dimensions": {
            "width_mm": case_specs.get("width_mm"),
            "height_mm": case_specs.get("height_mm"),
            "depth_mm": case_specs.get("depth_mm"),
        },
        "parts": result_parts,
    }
