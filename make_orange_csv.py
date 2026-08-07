
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


Part = dict[str, Any]


def specs(part: Part) -> dict[str, Any]:
    value = part.get("specifications")
    return value if isinstance(value, dict) else {}


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
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


def integer(value: Any) -> int | None:
    value_number = number(value)
    return int(round(value_number)) if value_number is not None else None


def list_of_text(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [value]

    return []


def normalize_socket(value: Any) -> str:
    text = normalize_text(value).replace(" ", "")
    if text.startswith("SOCKET"):
        text = text.removeprefix("SOCKET")
    return text


def normalize_memory(value: Any) -> str:
    text = normalize_text(value)
    match = re.search(r"DDR[345]", text)
    return match.group(0) if match else text


def normalize_form_factor(value: Any) -> str:
    text = normalize_text(value)

    replacements = (
        ("MICRO ATX", "M-ATX"),
        ("MICRO-ATX", "M-ATX"),
        ("MATX", "M-ATX"),
        ("MINI ITX", "M-ITX"),
        ("MINI-ITX", "M-ITX"),
        ("MITX", "M-ITX"),
        ("EXTENDED ATX", "E-ATX"),
        ("EATX", "E-ATX"),
    )

    for before, after in replacements:
        text = text.replace(before, after)

    if text == "ITX":
        return "M-ITX"

    return text


def corrected_storage_type(part: Part) -> str:
    part_specs = specs(part)
    combined = normalize_text(
        f"{part.get('model_name', '')} "
        f"{part_specs.get('danawa_raw_spec', '')} "
        f"{part_specs.get('storage_type', '')}"
    )

    # JSON에 storage_type이 SSD로 잘못 들어가 있어도
    # 원문 또는 제품명에 HDD가 있으면 HDD로 바로잡습니다.
    if re.search(r"\bHDD\b", combined):
        return "hdd"

    if (
        re.search(r"\bSSD\b", combined)
        or "NVME" in combined
        or "M.2" in combined
    ):
        return "ssd"

    return str(part_specs.get("storage_type", "")).strip().lower()


def cpu_socket(part: Part) -> str:
    return normalize_socket(specs(part).get("socket", ""))


def cpu_memory_types(part: Part) -> list[str]:
    return sorted(
        {
            normalize_memory(value)
            for value in list_of_text(
                specs(part).get("memory_types", [])
            )
            if normalize_memory(value)
        }
    )


def cpu_power_w(part: Part) -> int | None:
    part_specs = specs(part)
    return (
        integer(part_specs.get("max_power_w"))
        or integer(part_specs.get("tdp_w"))
    )


def board_socket(part: Part) -> str:
    return normalize_socket(specs(part).get("socket", ""))


def board_memory_type(part: Part) -> str:
    part_specs = specs(part)
    return normalize_memory(
        part_specs.get("memory_type")
        or part_specs.get("ram_type")
        or ""
    )


def board_form_factor(part: Part) -> str:
    return normalize_form_factor(
        specs(part).get("form_factor", "")
    )


def board_m2_slots(part: Part) -> int | None:
    return integer(specs(part).get("m2_slots"))


def board_sata_ports(part: Part) -> int | None:
    part_specs = specs(part)
    explicit = integer(part_specs.get("sata_ports"))

    if explicit is not None:
        return explicit

    raw = str(part_specs.get("danawa_raw_spec", ""))
    match = re.search(
        r"SATA3\s*:\s*(\d+)개",
        raw,
        re.IGNORECASE,
    )

    return int(match.group(1)) if match else None


def ram_memory_type(part: Part) -> str:
    part_specs = specs(part)
    return normalize_memory(
        part_specs.get("memory_type")
        or part_specs.get("ram_type")
        or ""
    )


def case_supported_form_factors(part: Part) -> list[str]:
    part_specs = specs(part)
    values = (
        part_specs.get("supported_form_factors")
        or part_specs.get("motherboard_form_factors")
        or []
    )

    return sorted(
        {
            normalize_form_factor(value)
            for value in list_of_text(values)
            if normalize_form_factor(value)
        }
    )


def cooler_supported_sockets(part: Part) -> list[str]:
    return sorted(
        {
            normalize_socket(value)
            for value in list_of_text(
                specs(part).get("supported_sockets", [])
            )
            if normalize_socket(value)
        }
    )


def cooler_capacity_w(part: Part) -> int | None:
    part_specs = specs(part)
    explicit = integer(part_specs.get("max_tdp_w"))

    if explicit is not None:
        return explicit

    radiator = integer(part_specs.get("radiator_size_mm"))

    if radiator is None:
        raw = str(part_specs.get("danawa_raw_spec", ""))
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


def spec_valid(part: Part) -> bool:
    category = str(part.get("category", "")).lower()
    part_specs = specs(part)

    if category == "cpu":
        return bool(cpu_socket(part))

    if category == "motherboard":
        return bool(
            board_socket(part)
            and board_memory_type(part)
            and board_form_factor(part)
        )

    if category == "ram":
        return bool(
            ram_memory_type(part)
            and integer(part_specs.get("capacity_gb"))
        )

    if category == "gpu":
        return bool(
            number(part_specs.get("length_mm")) is not None
            and integer(part_specs.get("recommended_psu_w"))
        )

    if category == "case":
        return bool(
            case_supported_form_factors(part)
            and all(
                number(part_specs.get(key)) is not None
                for key in ("width_mm", "height_mm", "depth_mm")
            )
            and number(part_specs.get("max_gpu_length_mm")) is not None
        )

    if category == "psu":
        return integer(part_specs.get("wattage")) is not None

    if category == "storage":
        return integer(part_specs.get("capacity_gb")) is not None

    if category == "cooler":
        return bool(
            cooler_supported_sockets(part)
            and cooler_capacity_w(part)
        )

    return False


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def write_csv(
    output_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        print(f"[건너뜀] {output_path.name}: 행이 없습니다.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys())

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=headers,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    target_name = (
        "spec_valid"
        if "spec_valid" in headers
        else "compatible"
    )
    target_counts = Counter(
        row[target_name]
        for row in rows
        if target_name in row
    )

    print(
        f"[생성] {output_path.name}: "
        f"{len(rows)}행, 정답 분포={dict(target_counts)}"
    )

    if len(target_counts) < 2:
        print(
            f"  주의: {target_name} 값이 한 종류뿐이라 "
            "이 파일만으로는 yes/no 분류 학습을 할 수 없습니다."
        )


def make_spec_rows(parts: list[Part]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for part in parts:
        part_specs = specs(part)
        memory_value = (
            part_specs.get("memory_type")
            or part_specs.get("ram_type")
            or part_specs.get("memory_types")
            or ""
        )

        rows.append(
            {
                "id": part.get("id"),
                "category": part.get("category"),
                "manufacturer": part.get("manufacturer"),
                "model_name": part.get("model_name"),
                "price": part.get("price"),
                "storage_type_corrected": (
                    corrected_storage_type(part)
                    if part.get("category") == "storage"
                    else ""
                ),
                "has_socket": int(
                    bool(
                        normalize_socket(
                            part_specs.get("socket", "")
                        )
                    )
                ),
                "has_memory_type": int(
                    bool(
                        normalize_memory(memory_value)
                    )
                ),
                "has_form_factor": int(
                    bool(
                        normalize_form_factor(
                            part_specs.get("form_factor", "")
                        )
                        or case_supported_form_factors(part)
                    )
                ),
                "has_dimensions": int(
                    all(
                        number(part_specs.get(key)) is not None
                        for key in (
                            "width_mm",
                            "height_mm",
                            "depth_mm",
                        )
                    )
                ),
                "has_gpu_length": int(
                    number(part_specs.get("length_mm")) is not None
                    or number(
                        part_specs.get("max_gpu_length_mm")
                    )
                    is not None
                ),
                "has_psu_requirement": int(
                    integer(
                        part_specs.get("recommended_psu_w")
                    )
                    is not None
                ),
                "has_wattage": int(
                    integer(part_specs.get("wattage"))
                    is not None
                ),
                "has_capacity": int(
                    integer(part_specs.get("capacity_gb"))
                    is not None
                ),
                "has_supported_sockets": int(
                    bool(cooler_supported_sockets(part))
                ),
                "has_cooling_capacity": int(
                    cooler_capacity_w(part) is not None
                ),
                "spec_count": len(part_specs),
                "spec_valid": yes_no(spec_valid(part)),
            }
        )

    return rows


def base_pair_row(
    pair_type: str,
    left: Part,
    right: Part,
) -> dict[str, Any]:
    return {
        "pair_type": pair_type,
        "left_id": left.get("id"),
        "left_name": left.get("model_name"),
        "right_id": right.get("id"),
        "right_name": right.get("model_name"),
    }


def make_cpu_motherboard_rows(
    cpus: list[Part],
    boards: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for cpu in cpus:
        for board in boards:
            cpu_socket_value = cpu_socket(cpu)
            board_socket_value = board_socket(board)
            cpu_memory_values = cpu_memory_types(cpu)
            board_memory_value = board_memory_type(board)

            if not (
                cpu_socket_value
                and board_socket_value
                and board_memory_value
            ):
                continue

            compatible = (
                cpu_socket_value == board_socket_value
                and (
                    not cpu_memory_values
                    or board_memory_value in cpu_memory_values
                )
            )

            rows.append(
                {
                    **base_pair_row(
                        "cpu_motherboard",
                        cpu,
                        board,
                    ),
                    "cpu_socket": cpu_socket_value,
                    "cpu_memory_types": "|".join(
                        cpu_memory_values
                    ),
                    "board_socket": board_socket_value,
                    "board_memory_type": board_memory_value,
                    "board_form_factor": board_form_factor(
                        board
                    ),
                    "compatible": yes_no(compatible),
                }
            )

    return rows


def make_motherboard_ram_rows(
    boards: list[Part],
    ram_parts: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for board in boards:
        for ram in ram_parts:
            board_memory_value = board_memory_type(board)
            ram_memory_value = ram_memory_type(ram)

            if not board_memory_value or not ram_memory_value:
                continue

            rows.append(
                {
                    **base_pair_row(
                        "motherboard_ram",
                        board,
                        ram,
                    ),
                    "board_memory_type": board_memory_value,
                    "ram_memory_type": ram_memory_value,
                    "ram_capacity_gb": integer(
                        specs(ram).get("capacity_gb")
                    ),
                    "compatible": yes_no(
                        board_memory_value
                        == ram_memory_value
                    ),
                }
            )

    return rows


def make_gpu_psu_rows(
    gpus: list[Part],
    psus: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for gpu in gpus:
        for psu in psus:
            required = integer(
                specs(gpu).get("recommended_psu_w")
            )
            available = integer(
                specs(psu).get("wattage")
            )

            if required is None or available is None:
                continue

            rows.append(
                {
                    **base_pair_row(
                        "gpu_psu",
                        gpu,
                        psu,
                    ),
                    "gpu_required_psu_w": required,
                    "gpu_power_w": integer(
                        specs(gpu).get("power_w")
                    ),
                    "psu_wattage": available,
                    "compatible": yes_no(
                        available >= required
                    ),
                }
            )

    return rows


def make_cpu_cooler_rows(
    cpus: list[Part],
    coolers: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for cpu in cpus:
        for cooler in coolers:
            cpu_socket_value = cpu_socket(cpu)
            supported = cooler_supported_sockets(cooler)

            if not cpu_socket_value or not supported:
                continue

            required_power = cpu_power_w(cpu)
            capacity = cooler_capacity_w(cooler)

            compatible = cpu_socket_value in supported

            if required_power is not None:
                compatible = bool(
                    compatible
                    and capacity is not None
                    and capacity >= required_power
                )

            rows.append(
                {
                    **base_pair_row(
                        "cpu_cooler",
                        cpu,
                        cooler,
                    ),
                    "cpu_socket": cpu_socket_value,
                    "cpu_power_w": required_power,
                    "cooler_supported_sockets": "|".join(
                        supported
                    ),
                    "cooler_capacity_w": capacity,
                    "cooler_type": normalize_text(
                        specs(cooler).get(
                            "cooler_type",
                            "",
                        )
                    ),
                    "compatible": yes_no(compatible),
                }
            )

    return rows


def make_gpu_case_rows(
    gpus: list[Part],
    cases: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for gpu in gpus:
        for computer_case in cases:
            gpu_length = number(
                specs(gpu).get("length_mm")
            )
            case_limit = number(
                specs(computer_case).get(
                    "max_gpu_length_mm"
                )
            )

            if gpu_length is None or case_limit is None:
                continue

            rows.append(
                {
                    **base_pair_row(
                        "gpu_case",
                        gpu,
                        computer_case,
                    ),
                    "gpu_length_mm": gpu_length,
                    "case_max_gpu_length_mm": case_limit,
                    "compatible": yes_no(
                        gpu_length <= case_limit
                    ),
                }
            )

    return rows


def make_motherboard_case_rows(
    boards: list[Part],
    cases: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for board in boards:
        for computer_case in cases:
            factor = board_form_factor(board)
            supported = case_supported_form_factors(
                computer_case
            )

            if not factor or not supported:
                continue

            rows.append(
                {
                    **base_pair_row(
                        "motherboard_case",
                        board,
                        computer_case,
                    ),
                    "board_form_factor": factor,
                    "case_supports_e_atx": int(
                        "E-ATX" in supported
                    ),
                    "case_supports_atx": int(
                        "ATX" in supported
                    ),
                    "case_supports_m_atx": int(
                        "M-ATX" in supported
                    ),
                    "case_supports_m_itx": int(
                        "M-ITX" in supported
                    ),
                    "compatible": yes_no(
                        factor in supported
                    ),
                }
            )

    return rows


def make_motherboard_storage_rows(
    boards: list[Part],
    storage_parts: list[Part],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for board in boards:
        for storage in storage_parts:
            storage_specs = specs(storage)
            storage_type = corrected_storage_type(storage)
            form_factor = normalize_text(
                storage_specs.get("form_factor", "")
            )
            interface = normalize_text(
                storage_specs.get("interface", "")
            )

            is_m2 = (
                "M.2" in form_factor
                or "NVME" in interface
            )
            m2_slots = board_m2_slots(board)
            sata_ports = board_sata_ports(board)

            if is_m2:
                if m2_slots is None:
                    continue
                compatible = m2_slots >= 1
            elif (
                storage_type == "hdd"
                or "SATA" in interface
            ):
                # 원래 추천 코드와 마찬가지로 SATA 포트 수를
                # 찾지 못한 보드는 일단 호환으로 처리합니다.
                compatible = (
                    True
                    if sata_ports is None
                    else sata_ports >= 1
                )
            else:
                continue

            rows.append(
                {
                    **base_pair_row(
                        "motherboard_storage",
                        board,
                        storage,
                    ),
                    "storage_type_corrected": storage_type,
                    "storage_form_factor": form_factor,
                    "storage_interface": interface,
                    "board_m2_slots": m2_slots,
                    "board_sata_ports": sata_ports,
                    "compatible": yes_no(compatible),
                }
            )

    return rows


def save_corrected_json(
    source_data: dict[str, Any],
    output_path: Path,
) -> int:
    copied = json.loads(
        json.dumps(
            source_data,
            ensure_ascii=False,
        )
    )

    changed = 0

    for part in copied.get("parts", []):
        if part.get("category") != "storage":
            continue

        new_type = corrected_storage_type(part)
        part_specs = part.get("specifications")

        if not isinstance(part_specs, dict):
            continue

        old_type = str(
            part_specs.get("storage_type", "")
        ).lower()

        if new_type and new_type != old_type:
            part_specs["storage_type"] = new_type
            changed += 1

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            copied,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "pc-auto-builder JSON을 Orange 학습용 CSV로 변환합니다."
        )
    )
    parser.add_argument(
        "input_json",
        type=Path,
        help="부품 백업 JSON 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("orange_data"),
        help="CSV 출력 폴더",
    )
    args = parser.parse_args()

    if not args.input_json.exists():
        raise FileNotFoundError(
            f"입력 파일을 찾을 수 없습니다: {args.input_json}"
        )

    source_data = json.loads(
        args.input_json.read_text(
            encoding="utf-8-sig"
        )
    )
    parts = source_data.get("parts", [])

    if not isinstance(parts, list):
        raise ValueError(
            "JSON의 parts 값이 목록이 아닙니다."
        )

    categories: dict[str, list[Part]] = {}

    for part in parts:
        category = str(
            part.get("category", "")
        ).lower()
        categories.setdefault(
            category,
            [],
        ).append(part)

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    corrected_count = save_corrected_json(
        source_data,
        args.output / "parts_corrected.json",
    )
    print(
        f"[생성] parts_corrected.json: "
        f"HDD/SSD 분류 {corrected_count}건 수정"
    )

    write_csv(
        args.output / "orange_spec_valid.csv",
        make_spec_rows(parts),
    )
    write_csv(
        args.output / "orange_cpu_motherboard.csv",
        make_cpu_motherboard_rows(
            categories.get("cpu", []),
            categories.get("motherboard", []),
        ),
    )
    write_csv(
        args.output / "orange_motherboard_ram.csv",
        make_motherboard_ram_rows(
            categories.get("motherboard", []),
            categories.get("ram", []),
        ),
    )
    write_csv(
        args.output / "orange_gpu_psu.csv",
        make_gpu_psu_rows(
            categories.get("gpu", []),
            categories.get("psu", []),
        ),
    )
    write_csv(
        args.output / "orange_cpu_cooler.csv",
        make_cpu_cooler_rows(
            categories.get("cpu", []),
            categories.get("cooler", []),
        ),
    )
    write_csv(
        args.output / "orange_gpu_case.csv",
        make_gpu_case_rows(
            categories.get("gpu", []),
            categories.get("case", []),
        ),
    )
    write_csv(
        args.output / "orange_motherboard_case.csv",
        make_motherboard_case_rows(
            categories.get("motherboard", []),
            categories.get("case", []),
        ),
    )
    write_csv(
        args.output / "orange_motherboard_storage.csv",
        make_motherboard_storage_rows(
            categories.get("motherboard", []),
            categories.get("storage", []),
        ),
    )

    print()
    print("Orange 설정:")
    print("  1) File 위젯에서 CSV 선택")
    print("  2) Select Columns에서 compatible 또는 spec_valid를 Target으로 이동")
    print("  3) id와 제품명 열은 Meta Attributes로 이동")
    print("  4) 나머지 규격 열은 Features로 유지")


if __name__ == "__main__":
    main()
