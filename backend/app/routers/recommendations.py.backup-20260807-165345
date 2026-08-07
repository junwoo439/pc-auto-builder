from __future__ import annotations

import math
import re
from collections import Counter
from typing import Literal, TypeAlias

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data.database import get_all_parts


router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


Part: TypeAlias = dict[str, object]
PartialBuild: TypeAlias = dict[str, object]

CategoryName = Literal[
    "cpu",
    "motherboard",
    "ram",
    "gpu",
    "case",
    "psu",
    "storage",
    "cooler",
]

ALL_CATEGORIES: tuple[CategoryName, ...] = (
    "cpu",
    "motherboard",
    "ram",
    "gpu",
    "case",
    "psu",
    "storage",
    "cooler",
)

BEAM_WIDTH = 900


class RecommendationRequest(BaseModel):
    budget: int = Field(ge=10000)
    purpose: Literal["gaming", "balanced", "office"]

    selected_categories: list[CategoryName] = Field(
        default_factory=lambda: [
            "cpu",
            "motherboard",
            "ram",
            "gpu",
            "case",
            "psu",
        ],
        min_length=1,
        max_length=8,
    )

    max_width_mm: float | None = Field(
        default=None,
        gt=0,
    )
    max_height_mm: float | None = Field(
        default=None,
        gt=0,
    )
    max_depth_mm: float | None = Field(
        default=None,
        gt=0,
    )

    allow_used: bool = False

    def selected_set(self) -> set[str]:
        return set(self.selected_categories)


def get_specs(part: Part | None) -> dict[str, object]:
    if part is None:
        return {}

    specifications = part.get("specifications")

    if isinstance(specifications, dict):
        return specifications

    return {}


def number(value: object) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()

        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def integer(value: object) -> int | None:
    numeric = number(value)

    if numeric is None:
        return None

    return int(round(numeric))


def normalize_text(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value).strip().upper(),
    )


def normalize_socket(value: object) -> str:
    text = normalize_text(value).replace(" ", "")

    if text.startswith("SOCKET"):
        text = text.removeprefix("SOCKET")

    return text


def normalize_memory_type(value: object) -> str:
    text = normalize_text(value)
    match = re.search(r"DDR[345]", text)
    return match.group(0) if match else text


def normalize_form_factor(value: object) -> str:
    text = normalize_text(value)
    text = text.replace("MICRO ATX", "M-ATX")
    text = text.replace("MICRO-ATX", "M-ATX")
    text = text.replace("MATX", "M-ATX")
    text = text.replace("MINI ITX", "M-ITX")
    text = text.replace("MINI-ITX", "M-ITX")
    text = text.replace("MITX", "M-ITX")
    text = text.replace("EXTENDED ATX", "E-ATX")
    text = text.replace("EATX", "E-ATX")
    return text


def list_of_text(value: object) -> list[str]:
    if isinstance(value, list):
        return [
            str(item)
            for item in value
            if str(item).strip()
        ]

    if isinstance(value, tuple):
        return [
            str(item)
            for item in value
            if str(item).strip()
        ]

    if isinstance(value, str) and value.strip():
        return [value]

    return []


def part_price(part: Part | None) -> int:
    if part is None:
        return 0

    value = integer(part.get("price"))
    return max(value or 0, 0)


def model_name(part: Part | None) -> str:
    if part is None:
        return ""

    return str(part.get("model_name", ""))


def is_used(part: Part) -> bool:
    specs = get_specs(part)

    if specs.get("used") is True:
        return True

    return "중고" in model_name(part)


def is_bulk(part: Part) -> bool:
    return "벌크" in model_name(part)


def has_integrated_graphics(cpu: Part) -> bool:
    specs = get_specs(cpu)
    explicit = specs.get("integrated_graphics")

    if isinstance(explicit, bool):
        return explicit

    raw = normalize_text(
        specs.get("danawa_raw_spec", "")
    )
    name = normalize_text(model_name(cpu))
    manufacturer = normalize_text(
        cpu.get("manufacturer", "")
    )

    if "미탑재" in raw and "그래픽" in raw:
        return False

    if re.search(
        r"\b(?:\d{4,5}|ULTRA\s*\d+)KF?\b",
        name,
    ):
        # Intel의 F/KF 접미사는 내장 그래픽이 없는 모델입니다.
        token_match = re.search(
            r"\b(?:\d{4,5}|ULTRA\s*\d+)(KF|F)\b",
            name,
        )

        if token_match:
            return False

    if any(
        keyword in raw
        for keyword in (
            "인텔 그래픽스",
            "UHD 그래픽",
            "RADEON GRAPHICS",
            "라데온 그래픽",
        )
    ):
        return True

    if "INTEL" in manufacturer or "인텔" in manufacturer:
        return not bool(
            re.search(r"\b\d{4,5}(?:KF|F)\b", name)
        )

    if "AMD" in manufacturer:
        return bool(
            re.search(r"\b\d{4,5}G\b", name)
        )

    return False


def cpu_cooler_included(cpu: Part) -> bool:
    specs = get_specs(cpu)
    explicit = specs.get("cooler_included")

    if isinstance(explicit, bool):
        return explicit

    name = normalize_text(model_name(cpu))
    raw = normalize_text(specs.get("danawa_raw_spec", ""))
    manufacturer = normalize_text(cpu.get("manufacturer", ""))

    if (
        "쿨러 : 미포함" in raw
        or "쿨러: 미포함" in raw
        or "COOLER NOT INCLUDED" in raw
    ):
        return False

    if (
        "+ 쿨러" in name
        or "쿨러 포함" in name
        or "COOLER INCLUDED" in name
    ):
        return True

    if "벌크" in name or "TRAY" in name:
        return False

    # Intel K/KF 및 Core Ultra K는 기본 쿨러가 포함되지 않습니다.
    if re.search(r"\b\d{4,5}(?:K|KF)\b", name):
        return False
    if "ULTRA" in name and re.search(r"\b\d{3}K\b", name):
        return False

    # AMD X/X3D 계열은 일반적으로 기본 쿨러가 포함되지 않습니다.
    if "AMD" in manufacturer and re.search(r"\b\d{4,5}(?:X|X3D)\b", name):
        return False

    if "정품" in name or "BOX" in name:
        return True

    return False


def cpu_power(cpu: Part) -> int | None:
    specs = get_specs(cpu)

    return (
        integer(specs.get("max_power_w"))
        or integer(specs.get("tdp_w"))
    )


def cpu_socket(cpu: Part) -> str:
    return normalize_socket(
        get_specs(cpu).get("socket", "")
    )


def board_socket(board: Part) -> str:
    return normalize_socket(
        get_specs(board).get("socket", "")
    )


def cpu_memory_types(cpu: Part) -> list[str]:
    values = get_specs(cpu).get(
        "memory_types",
        [],
    )

    return [
        normalize_memory_type(value)
        for value in list_of_text(values)
        if normalize_memory_type(value)
    ]


def board_memory_type(board: Part) -> str:
    specs = get_specs(board)

    return normalize_memory_type(
        specs.get("memory_type")
        or specs.get("ram_type")
        or ""
    )


def ram_memory_type(ram: Part) -> str:
    specs = get_specs(ram)

    return normalize_memory_type(
        specs.get("memory_type")
        or specs.get("ram_type")
        or ""
    )


def board_form_factor(board: Part) -> str:
    return normalize_form_factor(
        get_specs(board).get("form_factor", "")
    )


def case_supported_form_factors(
    computer_case: Part,
) -> list[str]:
    specs = get_specs(computer_case)
    values = (
        specs.get("supported_form_factors")
        or specs.get("motherboard_form_factors")
        or []
    )

    return [
        normalize_form_factor(value)
        for value in list_of_text(values)
    ]


def case_fits_dimensions(
    computer_case: Part,
    request: RecommendationRequest,
) -> bool:
    if "case" not in request.selected_set():
        return True

    limits = (
        request.max_width_mm,
        request.max_height_mm,
        request.max_depth_mm,
    )

    if any(value is None for value in limits):
        return False

    specs = get_specs(computer_case)

    width = number(specs.get("width_mm"))
    height = number(specs.get("height_mm"))
    depth = number(specs.get("depth_mm"))

    if None in (width, height, depth):
        return False

    return bool(
        width <= request.max_width_mm
        and height <= request.max_height_mm
        and depth <= request.max_depth_mm
    )


def gpu_length(gpu: Part | None) -> float | None:
    if gpu is None:
        return 0.0

    return number(
        get_specs(gpu).get("length_mm")
    )


def gpu_recommended_psu(
    gpu: Part | None,
) -> int | None:
    if gpu is None:
        return 0

    return integer(
        get_specs(gpu).get(
            "recommended_psu_w"
        )
    )


def case_max_gpu_length(
    computer_case: Part,
) -> float | None:
    return number(
        get_specs(computer_case).get(
            "max_gpu_length_mm"
        )
    )


def psu_wattage(psu: Part) -> int | None:
    return integer(
        get_specs(psu).get("wattage")
    )


def storage_is_m2(storage: Part) -> bool:
    specs = get_specs(storage)
    text = normalize_text(
        f"{specs.get('form_factor', '')} "
        f"{specs.get('interface', '')} "
        f"{specs.get('danawa_raw_spec', '')} "
        f"{model_name(storage)}"
    )

    return "M.2" in text or "NVME" in text


def storage_compatible(
    board: Part,
    storage: Part,
) -> bool:
    board_specs = get_specs(board)

    if storage_is_m2(storage):
        m2_slots = integer(
            board_specs.get("m2_slots")
        )

        return bool(
            m2_slots is not None
            and m2_slots >= 1
        )

    sata_ports = integer(
        board_specs.get("sata_ports")
    )

    if sata_ports is not None:
        return sata_ports >= 1

    # SATA 포트 수가 수집되지 않은 경우에도 현대 데스크톱 보드는
    # 일반적으로 SATA 저장장치를 지원하므로 경고와 함께 허용합니다.
    return True


def cooler_supported_sockets(
    cooler: Part,
) -> list[str]:
    values = get_specs(cooler).get(
        "supported_sockets",
        [],
    )

    return [
        normalize_socket(value)
        for value in list_of_text(values)
    ]


def cooler_capacity_w(cooler: Part) -> int | None:
    specs = get_specs(cooler)
    explicit = integer(
        specs.get("max_tdp_w")
    )

    if explicit is not None:
        return explicit

    radiator = integer(
        specs.get("radiator_size_mm")
    )

    if radiator is None:
        raw = str(
            specs.get("danawa_raw_spec", "")
        )
        rows = re.search(
            r"라디에이터\s*:\s*(\d+)열",
            raw,
            re.IGNORECASE,
        )

        if rows:
            radiator = int(rows.group(1)) * 120

    if radiator is not None:
        if radiator >= 360:
            return 280
        if radiator >= 280:
            return 240
        if radiator >= 240:
            return 190
        if radiator >= 120:
            return 125

    return None


def cooler_radiator_size(cooler: Part) -> int | None:
    specs = get_specs(cooler)
    size = integer(
        specs.get("radiator_size_mm")
    )

    if size is not None:
        return size

    raw = str(
        specs.get("danawa_raw_spec", "")
    )
    rows = re.search(
        r"라디에이터\s*:\s*(\d+)열",
        raw,
        re.IGNORECASE,
    )

    if rows:
        return int(rows.group(1)) * 120

    return None


def case_supported_radiator_sizes(
    computer_case: Part,
) -> list[int]:
    specs = get_specs(computer_case)
    explicit = specs.get(
        "supported_radiator_sizes_mm"
    )

    values: set[int] = set()

    if isinstance(explicit, list):
        for item in explicit:
            parsed = integer(item)

            if parsed:
                values.add(parsed)

    raw = str(
        specs.get("danawa_raw_spec", "")
    )

    for match in re.finditer(
        r"(?:라디에이터|수랭쿨러)[^/]{0,90}",
        raw,
        re.IGNORECASE,
    ):
        for value in re.findall(
            r"(?:120|140|240|280|360|420)\s*mm",
            match.group(0),
            re.IGNORECASE,
        ):
            values.add(
                int(re.sub(r"\D", "", value))
            )

    return sorted(values)


def cooler_compatible(
    cpu: Part,
    computer_case: Part,
    cooler: Part,
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    socket = cpu_socket(cpu)
    supported = cooler_supported_sockets(cooler)

    if not socket or not supported:
        return False, warnings

    if socket not in supported:
        return False, warnings

    required_power = cpu_power(cpu)
    capacity = cooler_capacity_w(cooler)

    if required_power is not None:
        if capacity is None:
            return False, warnings

        if capacity < required_power:
            return False, warnings

    cooler_specs = get_specs(cooler)
    cooler_type = normalize_text(
        cooler_specs.get("cooler_type", "")
    )

    if cooler_type == "AIR":
        cooler_height = number(
            cooler_specs.get("height_mm")
        )
        max_height = number(
            get_specs(computer_case).get(
                "max_cooler_height_mm"
            )
        )

        if (
            cooler_height is None
            or max_height is None
        ):
            return False, warnings

        if cooler_height > max_height:
            return False, warnings

    elif cooler_type == "LIQUID":
        radiator = cooler_radiator_size(cooler)
        supported_sizes = (
            case_supported_radiator_sizes(
                computer_case
            )
        )

        if radiator is None:
            return False, warnings

        if supported_sizes:
            if radiator not in supported_sizes:
                return False, warnings
        else:
            warnings.append(
                "케이스의 라디에이터 장착 위치는 원문에서 "
                "확인하지 못해 최종 조립 전에 확인이 필요합니다."
            )

    else:
        return False, warnings

    return True, warnings


def motherboard_case_compatible(
    board: Part,
    computer_case: Part,
) -> bool:
    factor = board_form_factor(board)
    supported = case_supported_form_factors(
        computer_case
    )

    return bool(
        factor
        and supported
        and factor in supported
    )


def gpu_case_compatible(
    gpu: Part | None,
    computer_case: Part,
) -> bool:
    if gpu is None:
        return True

    length = gpu_length(gpu)
    maximum = case_max_gpu_length(
        computer_case
    )

    return bool(
        length is not None
        and maximum is not None
        and length <= maximum
    )


def required_psu_wattage(
    cpu: Part | None,
    gpu: Part | None,
) -> int:
    gpu_requirement = gpu_recommended_psu(gpu)

    if gpu_requirement:
        return gpu_requirement

    if cpu is None:
        return 450

    cpu_requirement = cpu_power(cpu) or 100
    estimated = cpu_requirement + 180

    return max(
        450,
        int(math.ceil(estimated / 50) * 50),
    )


def psu_compatible(
    cpu: Part | None,
    gpu: Part | None,
    psu: Part,
) -> bool:
    wattage = psu_wattage(psu)

    if wattage is None:
        return False

    return wattage >= required_psu_wattage(
        cpu,
        gpu,
    )


def cpu_score(cpu: Part) -> float:
    specs = get_specs(cpu)
    cores = number(specs.get("cores")) or 0
    threads = number(specs.get("threads")) or 0
    boost = number(
        specs.get("boost_clock_ghz")
    ) or 0
    name = normalize_text(model_name(cpu))

    tier = 0

    tier_patterns = (
        (
            r"ULTRA\s*9|울트라\s*9|"
            r"CORE\s*I9|코어\s*I9|RYZEN\s*9",
            250,
        ),
        (
            r"ULTRA\s*7|울트라\s*7|"
            r"CORE\s*I7|코어\s*I7|RYZEN\s*7",
            190,
        ),
        (
            r"ULTRA\s*5|울트라\s*5|"
            r"CORE\s*I5|코어\s*I5|RYZEN\s*5",
            130,
        ),
        (
            r"CORE\s*I3|코어\s*I3|RYZEN\s*3",
            70,
        ),
    )

    for pattern, value in tier_patterns:
        if re.search(pattern, name):
            tier = value
            break

    generation_bonus = 0
    generation = re.search(
        r"(?:CORE|코어)\s*I[3579]-(\d{2})세대",
        name,
    )

    if generation:
        generation_bonus = (
            int(generation.group(1)) - 10
        ) * 18

    return (
        cores * 24
        + threads * 7
        + boost * 35
        + tier
        + generation_bonus
    )


def gpu_score(gpu: Part | None) -> float:
    if gpu is None:
        return 0

    specs = get_specs(gpu)
    text = normalize_text(
        specs.get("chipset")
        or model_name(gpu)
    )

    rank_patterns = (
        (r"RTX\s*5090", 1350),
        (r"RTX\s*5080", 1120),
        (r"RX\s*9070\s*XT", 930),
        (r"RTX\s*5070\s*TI", 900),
        (r"RX\s*9070", 820),
        (r"RX\s*9060\s*XT", 650),
        (r"RTX\s*5060\s*TI", 630),
        (r"RTX\s*5060", 520),
        (r"ARC\s*B580", 470),
        (r"RX\s*7600", 400),
        (r"ARC\s*PRO\s*B70", 380),
    )

    base = 200

    for pattern, value in rank_patterns:
        if re.search(pattern, text):
            base = value
            break

    vram = number(specs.get("vram_gb")) or 0
    stream = number(
        specs.get("stream_processors")
    ) or 0

    return base + vram * 10 + min(
        stream / 40,
        120,
    )


def ram_score(ram: Part) -> float:
    specs = get_specs(ram)
    capacity = number(
        specs.get("capacity_gb")
    ) or 0
    speed = number(specs.get("speed_mhz")) or 0
    modules = number(
        specs.get("module_count")
    ) or 1

    dual_channel_bonus = 35 if modules >= 2 else 0

    return (
        capacity * 16
        + speed / 22
        + dual_channel_bonus
    )


def storage_score(storage: Part | None) -> float:
    if storage is None:
        return 0

    specs = get_specs(storage)
    capacity = number(
        specs.get("capacity_gb")
    ) or 0
    storage_type = normalize_text(
        specs.get("storage_type", "")
    )
    interface = normalize_text(
        specs.get("interface", "")
    )
    read_speed = number(
        specs.get("sequential_read_mbps")
    ) or 0

    if storage_type == "SSD":
        type_score = 260
    else:
        type_score = 80

    if "PCIE5" in interface:
        interface_score = 160
    elif "PCIE4" in interface:
        interface_score = 125
    elif "PCIE3" in interface:
        interface_score = 90
    elif "SATA" in interface:
        interface_score = 45
    else:
        interface_score = 30

    return (
        type_score
        + interface_score
        + capacity * 0.18
        + min(read_speed / 20, 150)
    )


def motherboard_score(board: Part) -> float:
    specs = get_specs(board)
    name = normalize_text(model_name(board))
    m2_slots = number(specs.get("m2_slots")) or 0
    max_memory = number(
        specs.get("max_memory_gb")
    ) or 0

    chipset_score = 60

    if re.search(r"\bZ\d{3}\b|\bX\d{3}\b", name):
        chipset_score = 180
    elif re.search(r"\bB\d{3}\b", name):
        chipset_score = 130
    elif re.search(r"\bH\d{3}\b|\bA\d{3}\b", name):
        chipset_score = 80

    wifi_bonus = 35 if specs.get("wifi") else 0

    return (
        chipset_score
        + m2_slots * 24
        + max_memory * 0.3
        + wifi_bonus
    )


def case_score(
    computer_case: Part,
    gpu: Part | None,
) -> float:
    specs = get_specs(computer_case)
    maximum = number(
        specs.get("max_gpu_length_mm")
    ) or 0
    length = gpu_length(gpu) or 0
    margin = max(maximum - length, 0)

    return 80 + min(margin, 100) * 0.5


def psu_score(
    psu: Part,
    required_wattage: int,
) -> float:
    specs = get_specs(psu)
    wattage = psu_wattage(psu) or 0
    headroom = max(wattage - required_wattage, 0)
    efficiency = normalize_text(
        f"{specs.get('efficiency_rating', '')} "
        f"{specs.get('efficiency', '')} "
        f"{model_name(psu)}"
    )

    efficiency_bonus = 0

    if "TITANIUM" in efficiency or "티타늄" in efficiency:
        efficiency_bonus = 100
    elif "PLATINUM" in efficiency or "플래티넘" in efficiency:
        efficiency_bonus = 85
    elif "GOLD" in efficiency or "골드" in efficiency:
        efficiency_bonus = 65
    elif "SILVER" in efficiency or "실버" in efficiency:
        efficiency_bonus = 45
    elif "BRONZE" in efficiency or "브론즈" in efficiency:
        efficiency_bonus = 30

    return 80 + min(headroom, 300) * 0.25 + efficiency_bonus


def cooler_score(cooler: Part | None) -> float:
    if cooler is None:
        return 40

    capacity = cooler_capacity_w(cooler) or 0
    return 70 + capacity * 0.35


def weighted_component_score(
    category: str,
    part: Part | None,
    purpose: str,
    context: PartialBuild,
) -> float:
    cpu = context.get("cpu")
    gpu = context.get("gpu")

    cpu_part = cpu if isinstance(cpu, dict) else None
    gpu_part = gpu if isinstance(gpu, dict) else None

    weights = {
        "gaming": {
            "cpu": 0.22,
            "motherboard": 0.05,
            "ram": 0.10,
            "gpu": 0.48,
            "case": 0.03,
            "psu": 0.04,
            "storage": 0.06,
            "cooler": 0.02,
        },
        "balanced": {
            "cpu": 0.30,
            "motherboard": 0.07,
            "ram": 0.13,
            "gpu": 0.28,
            "case": 0.04,
            "psu": 0.05,
            "storage": 0.10,
            "cooler": 0.03,
        },
        "office": {
            "cpu": 0.38,
            "motherboard": 0.10,
            "ram": 0.20,
            "gpu": 0.03,
            "case": 0.06,
            "psu": 0.07,
            "storage": 0.14,
            "cooler": 0.02,
        },
    }

    weight = weights[purpose][category]

    if category == "cpu" and part is not None:
        raw = cpu_score(part)
    elif category == "motherboard" and part is not None:
        raw = motherboard_score(part)
    elif category == "ram" and part is not None:
        raw = ram_score(part)
    elif category == "gpu":
        raw = gpu_score(part)
    elif category == "case" and part is not None:
        raw = case_score(part, gpu_part)
    elif category == "psu" and part is not None:
        raw = psu_score(
            part,
            required_psu_wattage(
                cpu_part,
                gpu_part,
            ),
        )
    elif category == "storage":
        raw = storage_score(part)
    elif category == "cooler":
        raw = cooler_score(part)
    else:
        raw = 0

    return raw * weight


def empty_partial() -> PartialBuild:
    return {
        "parts": [],
        "total_price": 0,
        "score": 0.0,
        "checks": [],
        "warnings": [],
    }


def add_part(
    partial: PartialBuild,
    category: str,
    part: Part | None,
    purpose: str,
    checks: list[str] | None = None,
    warnings: list[str] | None = None,
) -> PartialBuild:
    result: PartialBuild = {
        **partial,
        "parts": list(partial["parts"]),
        "checks": list(partial["checks"]),
        "warnings": list(partial["warnings"]),
    }

    result[category] = part

    if part is not None:
        result["parts"].append(part)
        result["total_price"] = (
            int(result["total_price"])
            + part_price(part)
        )

    result["score"] = (
        float(result["score"])
        + weighted_component_score(
            category,
            part,
            purpose,
            result,
        )
    )

    if checks:
        result["checks"].extend(checks)

    if warnings:
        result["warnings"].extend(warnings)

    if part is not None and is_bulk(part):
        result["warnings"].append(
            f"{model_name(part)}은(는) 벌크 상품이므로 "
            "보증과 구성품을 확인해야 합니다."
        )

    return result


def beam_rank(
    partial: PartialBuild,
    request: RecommendationRequest,
) -> float:
    score = float(partial["score"])
    total = int(partial["total_price"])
    remaining_ratio = max(
        request.budget - total,
        0,
    ) / request.budget

    affordability_weight = (
        210
        if request.purpose == "office"
        else 95
    )

    return (
        score
        + remaining_ratio * affordability_weight
        - len(partial["warnings"]) * 8
    )


def keep_best(
    partials: list[PartialBuild],
    request: RecommendationRequest,
    limit: int = BEAM_WIDTH,
) -> list[PartialBuild]:
    valid = [
        partial
        for partial in partials
        if int(partial["total_price"])
        <= request.budget
    ]

    valid.sort(
        key=lambda partial: beam_rank(
            partial,
            request,
        ),
        reverse=True,
    )

    return valid[:limit]


def ready_cpu(part: Part) -> bool:
    return bool(cpu_socket(part))


def ready_board(part: Part) -> bool:
    return bool(
        board_socket(part)
        and board_memory_type(part)
        and board_form_factor(part)
    )


def ready_ram(part: Part) -> bool:
    return bool(
        ram_memory_type(part)
        and integer(
            get_specs(part).get("capacity_gb")
        )
    )


def ready_gpu(part: Part) -> bool:
    return bool(
        gpu_length(part) is not None
        and gpu_recommended_psu(part)
    )


def ready_case(part: Part) -> bool:
    specs = get_specs(part)

    return bool(
        case_supported_form_factors(part)
        and number(specs.get("width_mm"))
        is not None
        and number(specs.get("height_mm"))
        is not None
        and number(specs.get("depth_mm"))
        is not None
        and case_max_gpu_length(part)
        is not None
    )


def ready_psu(part: Part) -> bool:
    return psu_wattage(part) is not None


def ready_storage(part: Part) -> bool:
    return bool(
        integer(
            get_specs(part).get("capacity_gb")
        )
    )


def ready_cooler(part: Part) -> bool:
    return bool(
        cooler_supported_sockets(part)
        and cooler_capacity_w(part)
    )


def ready_for_request(
    category: str,
    part: Part,
    request: RecommendationRequest,
) -> bool:
    selected = request.selected_set()

    if category == "cpu":
        if not ready_cpu(part):
            return False

        selected = request.selected_set()
        if "gpu" not in selected and not has_integrated_graphics(part):
            return False

        if "cooler" not in selected and not cpu_cooler_included(part):
            return False

        return True

    if category == "motherboard":
        return ready_board(part)

    if category == "ram":
        return ready_ram(part)

    if category == "gpu":
        if "case" in selected and gpu_length(part) is None:
            return False

        if (
            "psu" in selected
            and not gpu_recommended_psu(part)
        ):
            return False

        return bool(
            get_specs(part).get("chipset")
            or get_specs(part).get("vram_gb")
            or model_name(part)
        )

    if category == "case":
        specs = get_specs(part)

        if (
            number(specs.get("width_mm")) is None
            or number(specs.get("height_mm")) is None
            or number(specs.get("depth_mm")) is None
        ):
            return False

        if (
            "motherboard" in selected
            and not case_supported_form_factors(part)
        ):
            return False

        if (
            "gpu" in selected
            and case_max_gpu_length(part) is None
        ):
            return False

        return True

    if category == "psu":
        return ready_psu(part)

    if category == "storage":
        return ready_storage(part)

    if category == "cooler":
        return ready_cooler(part)

    return False


def category_data_status(
    categories: dict[str, list[Part]],
    request: RecommendationRequest,
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}

    for category in request.selected_categories:
        parts = categories.get(category, [])

        result[category] = {
            "total": len(parts),
            "ready": sum(
                1
                for part in parts
                if ready_for_request(
                    category,
                    part,
                    request,
                )
            ),
        }

    return result


def prepare_categories(
    all_parts: list[Part],
    request: RecommendationRequest,
) -> dict[str, list[Part]]:
    categories = {
        category: []
        for category in ALL_CATEGORIES
    }

    for part in all_parts:
        category = str(
            part.get("category", "")
        ).lower()

        if category not in categories:
            continue

        if (
            not request.allow_used
            and is_used(part)
        ):
            continue

        categories[category].append(part)

    return {
        category: [
            part
            for part in parts
            if ready_for_request(
                category,
                part,
                request,
            )
        ]
        for category, parts in categories.items()
    }


def cooler_compatible_without_case(
    cpu: Part,
    cooler: Part,
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    socket = cpu_socket(cpu)
    supported = cooler_supported_sockets(
        cooler
    )

    if (
        not socket
        or not supported
        or socket not in supported
    ):
        return False, warnings

    required_power = cpu_power(cpu)
    capacity = cooler_capacity_w(cooler)

    if required_power is not None:
        if capacity is None:
            return False, warnings

        if capacity < required_power:
            return False, warnings

    warnings.append(
        "케이스를 선택하지 않아 쿨러 높이 또는 "
        "라디에이터 장착 가능 여부는 검사하지 않았습니다."
    )

    return True, warnings


def candidate_compatibility(
    category: str,
    part: Part,
    partial: PartialBuild,
    request: RecommendationRequest,
) -> tuple[bool, list[str], list[str]]:
    checks: list[str] = []
    warnings: list[str] = []

    cpu_value = partial.get("cpu")
    board_value = partial.get("motherboard")
    ram_value = partial.get("ram")
    gpu_value = partial.get("gpu")
    case_value = partial.get("case")

    cpu = (
        cpu_value
        if isinstance(cpu_value, dict)
        else None
    )
    board = (
        board_value
        if isinstance(board_value, dict)
        else None
    )
    ram = (
        ram_value
        if isinstance(ram_value, dict)
        else None
    )
    gpu = (
        gpu_value
        if isinstance(gpu_value, dict)
        else None
    )
    computer_case = (
        case_value
        if isinstance(case_value, dict)
        else None
    )

    if category == "cpu":
        selected = request.selected_set()

        if "gpu" not in selected:
            if not has_integrated_graphics(part):
                return False, checks, warnings
            checks.append("그래픽카드 미선택 구성: CPU 내장그래픽 탑재 확인")

        if "cooler" not in selected:
            if not cpu_cooler_included(part):
                return False, checks, warnings
            checks.append("별도 쿨러 미선택 구성: CPU 기본 쿨러 포함 확인")

        return True, checks, warnings

    if category == "motherboard":
        if cpu is not None:
            if cpu_socket(cpu) != board_socket(part):
                return False, checks, warnings

            checks.append(
                "CPU와 메인보드 소켓 일치: "
                f"{cpu_socket(cpu)}"
            )

            supported_memory = cpu_memory_types(cpu)
            board_memory = board_memory_type(part)

            if (
                supported_memory
                and board_memory not in supported_memory
            ):
                return False, checks, warnings

            if supported_memory:
                checks.append(
                    "CPU와 메인보드 메모리 규격 호환: "
                    f"{board_memory}"
                )
        else:
            warnings.append(
                "CPU를 선택하지 않아 메인보드 소켓 "
                "호환성은 검사하지 않았습니다."
            )

        return True, checks, warnings

    if category == "ram":
        if board is not None:
            if (
                board_memory_type(board)
                != ram_memory_type(part)
            ):
                return False, checks, warnings

            checks.append(
                "메인보드와 RAM 규격 일치: "
                f"{ram_memory_type(part)}"
            )
        else:
            warnings.append(
                "메인보드를 선택하지 않아 RAM 규격 "
                "호환성은 검사하지 않았습니다."
            )

        return True, checks, warnings

    if category == "gpu":
        return True, checks, warnings

    if category == "case":
        if not case_fits_dimensions(
            part,
            request,
        ):
            return False, checks, warnings

        checks.append(
            "케이스 외형 크기가 입력한 설치 공간 이내입니다."
        )

        if board is not None:
            if not motherboard_case_compatible(
                board,
                part,
            ):
                return False, checks, warnings

            checks.append(
                "메인보드 폼팩터와 케이스 호환: "
                f"{board_form_factor(board)}"
            )

        if gpu is not None:
            if not gpu_case_compatible(
                gpu,
                part,
            ):
                return False, checks, warnings

            checks.append(
                "그래픽카드 길이 호환: "
                f"{gpu_length(gpu):g}mm ≤ "
                f"{case_max_gpu_length(part):g}mm"
            )

        return True, checks, warnings

    if category == "psu":
        if not psu_compatible(
            cpu,
            gpu,
            part,
        ):
            return False, checks, warnings

        required = required_psu_wattage(
            cpu,
            gpu,
        )

        checks.append(
            "파워 용량 충족: "
            f"{psu_wattage(part)}W ≥ "
            f"{required}W"
        )

        if cpu is None and gpu is None:
            warnings.append(
                "CPU와 그래픽카드를 선택하지 않아 "
                "파워 필요 용량은 기본 450W 기준으로 계산했습니다."
            )

        return True, checks, warnings

    if category == "storage":
        if board is not None:
            if not storage_compatible(
                board,
                part,
            ):
                return False, checks, warnings

            checks.append(
                "메인보드와 저장장치 연결 규격을 확인했습니다."
            )
        else:
            warnings.append(
                "메인보드를 선택하지 않아 저장장치 연결 "
                "규격은 검사하지 않았습니다."
            )

        return True, checks, warnings

    if category == "cooler":
        if cpu is None:
            warnings.append(
                "CPU를 선택하지 않아 쿨러 소켓과 "
                "냉각 용량은 검사하지 않았습니다."
            )
            return True, checks, warnings

        if computer_case is not None:
            compatible, cooler_warnings = (
                cooler_compatible(
                    cpu,
                    computer_case,
                    part,
                )
            )
        else:
            compatible, cooler_warnings = (
                cooler_compatible_without_case(
                    cpu,
                    part,
                )
            )

        if not compatible:
            return False, checks, warnings

        checks.extend(
            [
                "CPU 소켓과 쿨러 호환: "
                f"{cpu_socket(cpu)}",
                "CPU 발열과 쿨러 냉각 용량을 확인했습니다.",
            ]
        )
        warnings.extend(cooler_warnings)

        return True, checks, warnings

    return True, checks, warnings


def validate_complete_build(
    build: PartialBuild,
    request: RecommendationRequest,
) -> tuple[bool, list[str], list[str]]:
    checks: list[str] = []
    warnings: list[str] = []
    selected = request.selected_set()

    cpu_value = build.get("cpu")
    gpu_value = build.get("gpu")
    cooler_value = build.get("cooler")
    cpu = cpu_value if isinstance(cpu_value, dict) else None
    gpu = gpu_value if isinstance(gpu_value, dict) else None
    cooler = cooler_value if isinstance(cooler_value, dict) else None

    if cpu is not None and "gpu" not in selected and gpu is None:
        if not has_integrated_graphics(cpu):
            return False, checks, warnings
        checks.append("화면 출력용 CPU 내장그래픽을 최종 확인했습니다.")

    if cpu is not None and "cooler" not in selected and cooler is None:
        if not cpu_cooler_included(cpu):
            return False, checks, warnings
        checks.append("CPU 기본 쿨러 포함 여부를 최종 확인했습니다.")

    if cpu is not None and "motherboard" in selected:
        warnings.append(
            "메인보드 BIOS 버전의 해당 CPU 지원 여부는 제조사 CPU 지원 목록에서 최종 확인하세요."
        )

    if "gpu" in selected and gpu is not None:
        warnings.append(
            "그래픽카드 보조전원 커넥터 종류와 케이스 슬롯 두께는 상품 상세페이지에서 최종 확인하세요."
        )

    return True, checks, warnings


def verification_notes(request: RecommendationRequest) -> list[str]:
    notes = [
        "이 결과는 등록된 소켓, 메모리 규격, 길이, 냉각 용량, 정격 출력 등 기본 규격 데이터 기준입니다.",
        "실구매 전 제조사 호환 목록, BIOS 버전, 전원 커넥터, 케이블 공간을 확인해야 합니다.",
    ]
    if "case" in request.selected_set():
        notes.append(
            "3D 화면은 규격 기반 참고 시각화이며 실제 나사 위치·케이블·라디에이터 간섭을 보증하지 않습니다."
        )
    return notes


def build_candidates(
    categories: dict[str, list[Part]],
    request: RecommendationRequest,
) -> list[PartialBuild]:
    partials: list[PartialBuild] = [
        empty_partial()
    ]

    for category in ALL_CATEGORIES:
        if category not in request.selected_set():
            continue

        options = categories.get(category, [])

        if not options:
            return []

        next_partials: list[PartialBuild] = []

        for partial in partials:
            for part in options:
                compatible, checks, warnings = (
                    candidate_compatibility(
                        category,
                        part,
                        partial,
                        request,
                    )
                )

                if not compatible:
                    continue

                next_partials.append(
                    add_part(
                        partial,
                        category,
                        part,
                        request.purpose,
                        checks=checks,
                        warnings=warnings,
                    )
                )

        partials = keep_best(
            next_partials,
            request,
        )

        if not partials:
            return []

    complete_builds: list[PartialBuild] = []
    for partial in partials:
        valid, checks, warnings = validate_complete_build(partial, request)
        if not valid:
            continue

        completed = {
            **partial,
            "checks": list(partial["checks"]) + checks,
            "warnings": list(partial["warnings"]) + warnings,
        }
        complete_builds.append(completed)

    return complete_builds


def final_score(
    build: PartialBuild,
    request: RecommendationRequest,
) -> float:
    score = float(build["score"])
    total = int(build["total_price"])
    utilization = total / request.budget

    if request.purpose == "office":
        budget_bonus = (
            1 - utilization
        ) * 160
    else:
        ideal = 0.93
        distance = abs(utilization - ideal)
        budget_bonus = max(
            0,
            140 - distance * 300,
        )

    return (
        score
        + budget_bonus
        - len(build["warnings"]) * 12
    )


def build_failure_message(
    data_status: dict[str, dict[str, int]],
    request: RecommendationRequest,
) -> tuple[str, list[str]]:
    suggestions: list[str] = []

    labels = {
        "cpu": "CPU",
        "motherboard": "메인보드",
        "ram": "RAM",
        "gpu": "그래픽카드",
        "case": "케이스",
        "psu": "파워",
        "storage": "저장장치",
        "cooler": "쿨러",
    }

    for category in request.selected_categories:
        status = data_status.get(
            category,
            {"total": 0, "ready": 0},
        )

        if status["ready"] == 0:
            suggestions.append(
                f"{labels[category]} 상세 규격이 있는 제품을 "
                "1개 이상 등록하거나 상세 규격 갱신을 실행하세요."
            )

    if "cpu" in request.selected_set() and "gpu" not in request.selected_set():
        suggestions.append(
            "그래픽카드를 선택하지 않았다면 내장그래픽이 탑재된 CPU 데이터가 필요합니다."
        )

    if "cpu" in request.selected_set() and "cooler" not in request.selected_set():
        suggestions.append(
            "별도 쿨러를 선택하지 않았다면 기본 쿨러 포함 CPU만 사용할 수 있습니다."
        )

    if not suggestions:
        suggestions.extend(
            [
                "예산을 높이거나 선택한 장비 수를 줄여 다시 시도하세요.",
                "케이스를 선택했다면 최대 설치 공간을 넓혀 보세요.",
                "서로 연결되는 장비의 소켓·DDR 규격·길이·파워 용량을 확인하세요.",
            ]
        )

    selected_names = ", ".join(
        labels[category]
        for category in request.selected_categories
    )

    return (
        f"선택한 장비({selected_names})를 모두 만족하는 "
        "검증 가능한 조합을 찾지 못했습니다.",
        suggestions,
    )


def serialize_part(part: Part) -> Part:
    return {
        "id": part.get("id"),
        "category": part.get("category"),
        "manufacturer": part.get("manufacturer"),
        "model_name": part.get("model_name"),
        "price": part.get("price"),
        "specifications": get_specs(part),
    }


def build_summary(build: PartialBuild) -> dict[str, object]:
    cpu = build.get("cpu")
    board = build.get("motherboard")
    ram = build.get("ram")
    gpu = build.get("gpu")
    computer_case = build.get("case")
    psu = build.get("psu")
    storage = build.get("storage")
    cooler = build.get("cooler")

    return {
        "cpu_socket": (
            cpu_socket(cpu)
            if isinstance(cpu, dict)
            else None
        ),
        "memory_type": (
            board_memory_type(board)
            if isinstance(board, dict)
            else None
        ),
        "ram_capacity_gb": (
            integer(
                get_specs(ram).get(
                    "capacity_gb"
                )
            )
            if isinstance(ram, dict)
            else None
        ),
        "gpu_length_mm": (
            gpu_length(gpu)
            if isinstance(gpu, dict)
            else None
        ),
        "case_max_gpu_length_mm": (
            case_max_gpu_length(
                computer_case
            )
            if isinstance(computer_case, dict)
            else None
        ),
        "psu_wattage": (
            psu_wattage(psu)
            if isinstance(psu, dict)
            else None
        ),
        "required_psu_wattage": (
            required_psu_wattage(
                cpu if isinstance(cpu, dict) else None,
                gpu if isinstance(gpu, dict) else None,
            )
            if (
                isinstance(cpu, dict)
                or isinstance(gpu, dict)
            )
            else None
        ),
        "storage_capacity_gb": (
            integer(
                get_specs(storage).get(
                    "capacity_gb"
                )
            )
            if isinstance(storage, dict)
            else None
        ),
        "cooler_included_separately": (
            isinstance(cooler, dict)
        ),
    }


@router.post("/auto")
def recommend_build(
    request: RecommendationRequest,
) -> dict[str, object]:
    selected_categories = list(
        dict.fromkeys(
            request.selected_categories
        )
    )
    request.selected_categories = (
        selected_categories
    )

    if (
        "case" in request.selected_set()
        and any(
            value is None
            for value in (
                request.max_width_mm,
                request.max_height_mm,
                request.max_depth_mm,
            )
        )
    ):
        return {
            "found": False,
            "message": (
                "케이스를 추천하려면 최대 가로·높이·깊이를 "
                "모두 입력해야 합니다."
            ),
            "budget": request.budget,
            "selected_categories": selected_categories,
            "parts": [],
            "data_status": {},
            "suggestions": [
                "케이스 체크를 해제하거나 설치 공간 크기를 입력하세요."
            ],
        }

    all_parts = get_all_parts()

    raw_categories: dict[str, list[Part]] = {
        category: [
            part
            for part in all_parts
            if str(
                part.get("category", "")
            ).lower() == category
            and (
                request.allow_used
                or not is_used(part)
            )
        ]
        for category in ALL_CATEGORIES
    }

    data_status = category_data_status(
        raw_categories,
        request,
    )

    categories = prepare_categories(
        all_parts,
        request,
    )

    candidates = build_candidates(
        categories,
        request,
    )

    requested_dimensions = {
        "width_mm": request.max_width_mm,
        "height_mm": request.max_height_mm,
        "depth_mm": request.max_depth_mm,
    }

    if not candidates:
        message, suggestions = (
            build_failure_message(
                data_status,
                request,
            )
        )

        return {
            "found": False,
            "message": message,
            "budget": request.budget,
            "selected_categories": selected_categories,
            "requested_dimensions": requested_dimensions,
            "parts": [],
            "data_status": data_status,
            "suggestions": suggestions,
        }

    candidates.sort(
        key=lambda build: final_score(
            build,
            request,
        ),
        reverse=True,
    )

    selected = candidates[0]
    selected_parts = [
        serialize_part(part)
        for part in selected["parts"]
        if isinstance(part, dict)
    ]

    selected_case = selected.get("case")
    case_specs = (
        get_specs(selected_case)
        if isinstance(selected_case, dict)
        else {}
    )

    warnings = list(
        dict.fromkeys(
            str(value)
            for value in selected["warnings"]
        )
    )
    checks = list(
        dict.fromkeys(
            str(value)
            for value in selected["checks"]
        )
    )

    total_price = int(
        selected["total_price"]
    )

    category_counter = Counter(
        str(part.get("category"))
        for part in selected_parts
    )

    return {
        "found": True,
        "message": (
            "선택한 장비를 대상으로 등록된 기본 규격을 검사해 "
            "예산에 맞는 조합을 찾았습니다. 구매 전 최종 확인 항목도 함께 확인하세요."
        ),
        "budget": request.budget,
        "purpose": request.purpose,
        "selected_categories": selected_categories,
        "total_price": total_price,
        "remaining_budget": (
            request.budget - total_price
        ),
        "requested_dimensions": requested_dimensions,
        "case_dimensions": {
            "width_mm": case_specs.get("width_mm"),
            "height_mm": case_specs.get("height_mm"),
            "depth_mm": case_specs.get("depth_mm"),
        },
        "parts": selected_parts,
        "compatibility_checks": checks,
        "warnings": warnings,
        "verification_level": "basic_compatibility_checked",
        "verification_notes": verification_notes(request),
        "build_summary": build_summary(selected),
        "included_categories": dict(
            category_counter
        ),
        "evaluated_candidates": len(candidates),
        "data_status": data_status,
    }
