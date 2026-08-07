
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from app.data.database import connect_database
from app.services.part_backup import save_seed_file
from app.services.product_importer import robots_allows


REQUEST_DELAY_SECONDS = 1.0
TIMEOUT_SECONDS = 20

CATE_MAP = {
    "1131480": "gpu", "1131521": "gpu", "11347368": "gpu",
    "11354785": "cpu", "11351504": "cpu", "11345419": "cpu",
    "11354784": "motherboard", "11353758": "motherboard",
    "11341201": "ram", "1131326": "ram",
    "11352133": "storage", "11338854": "storage",
    "11352132": "storage", "1131401": "storage",
    "113979": "case", "113971": "case",
    "1131496": "psu",
    "11336856": "cooler",
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _match(pattern: str, text: str) -> str | None:
    found = re.search(pattern, text, re.IGNORECASE)
    return found.group(1).strip() if found else None


def _number(pattern: str, text: str, decimal: bool = False):
    value = _match(pattern, text)

    if value is None:
        return None

    value = value.replace(",", "")

    try:
        return float(value) if decimal else int(value)
    except ValueError:
        return None


def _put(target: dict[str, object], key: str, value: object) -> None:
    if value is not None:
        target[key] = value


def _capacity_gb(model_name: str) -> int | None:
    values = re.findall(
        r"(\d+(?:\.\d+)?)\s*(TB|GB)",
        model_name,
        re.IGNORECASE,
    )

    if not values:
        return None

    amount, unit = values[-1]
    value = float(amount)
    return round(value * 1024 if unit.upper() == "TB" else value)


def _socket(text: str) -> str | None:
    intel = _match(r"\(소켓\s*(\d{4})\)", text)

    if intel:
        return f"LGA{intel}"

    value = _match(
        r"\b(LGA\s*\d{4}|LGA115x|AM[345]|FM[12]\+?|TR4|sTRX4|sWRX8)\b",
        text,
    )

    return value.replace(" ", "").upper() if value else None


def _extract_raw_spec(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for selector in (
        ".prod_spec_set .spec_list",
        ".summary_info .spec_list",
        ".spec_list",
        ".prod_spec",
    ):
        for element in soup.select(selector):
            text = _clean(element.get_text(" ", strip=True))

            if len(text) >= 20 and "/" in text and "가격비교" not in text:
                return text

    page_text = soup.get_text("\n", strip=True)

    found = re.search(
        r"(?:^|\n)상세 스펙\s*\n+(.+?)\n+(?:관심|공유)(?:\n|$)",
        page_text,
        re.DOTALL,
    )

    return _clean(found.group(1)) if found else ""


def _infer_category(source_url: str, current: str, raw: str) -> str:
    cate = parse_qs(urlparse(source_url).query).get("cate", [""])[0]

    if cate in CATE_MAP:
        return CATE_MAP[cate]

    lowered = raw.lower()

    if "cpu 쿨러" in lowered or "라디에이터" in lowered:
        return "cooler"
    if "atx 파워" in lowered or "80 plus" in lowered:
        return "psu"
    if "지원보드규격:" in lowered:
        return "case"
    if "가로(길이):" in lowered:
        return "gpu"
    if "메모리 용량: 최대" in lowered:
        return "motherboard"
    if "램개수:" in lowered:
        return "ram"
    if "순차읽기:" in lowered or "7200/" in lowered or "5400/" in lowered:
        return "storage"
    if "스레드" in lowered:
        return "cpu"

    return current


def _parse(category: str, raw: str, model_name: str) -> dict[str, object]:
    result: dict[str, object] = {
        "danawa_raw_spec": raw,
        "danawa_spec_items": [
            item.strip()
            for item in re.split(r"\s+/\s+", raw)
            if item.strip()
        ],
    }

    if category == "cpu":
        _put(result, "socket", _socket(raw))

        hybrid = re.search(r"P(\d+)\+E(\d+)코어", raw, re.IGNORECASE)

        if hybrid:
            p_cores = int(hybrid.group(1))
            e_cores = int(hybrid.group(2))
            result.update({
                "performance_cores": p_cores,
                "efficiency_cores": e_cores,
                "cores": p_cores + e_cores,
            })
        else:
            _put(result, "cores", _number(r"(\d+)코어", raw))

        _put(result, "threads", _number(r"(\d+)스레드", raw))

        power_range = re.search(
            r"(?:PBP-MTP|TDP)[^0-9]*(\d+)\s*-\s*(\d+)W",
            raw,
            re.IGNORECASE,
        )

        if power_range:
            result["tdp_w"] = int(power_range.group(1))
            result["max_power_w"] = int(power_range.group(2))
        else:
            _put(result, "tdp_w", _number(r"(?:PBP|TDP)\s*:\s*(\d+)\s*W", raw))

        memory_types = sorted(set(
            value.upper()
            for value in re.findall(r"\bDDR[345]\b", raw, re.IGNORECASE)
        ))

        if memory_types:
            result["memory_types"] = memory_types

    elif category == "motherboard":
        _put(result, "socket", _socket(raw))

        ram_type = _match(r"\b(DDR[345])\b", raw)

        if ram_type:
            result["ram_type"] = ram_type.upper()
            result["memory_type"] = ram_type.upper()

        form = re.search(
            r"\b(E-?ATX|M-ATX|M-ITX|ATX)\s*\(([\d.]+)x([\d.]+)cm\)",
            raw,
            re.IGNORECASE,
        )

        if form:
            result["form_factor"] = form.group(1).upper()
            result["width_mm"] = round(float(form.group(2)) * 10, 1)
            result["height_mm"] = round(float(form.group(3)) * 10, 1)

        _put(
            result,
            "max_memory_gb",
            _number(r"메모리 용량\s*:\s*최대\s*(\d+)\s*GB", raw),
        )
        _put(result, "m2_slots", _number(r"M\.2\s*:\s*(\d+)개", raw))

    elif category == "ram":
        ram_type = _match(r"\b(DDR[345])\b", raw)

        if ram_type:
            result["ram_type"] = ram_type.upper()
            result["memory_type"] = ram_type.upper()

        _put(result, "speed_mhz", _number(r"\b(\d{4,5})MHz\b", raw))
        _put(result, "capacity_gb", _capacity_gb(model_name))
        _put(result, "module_count", _number(r"램개수\s*:\s*(\d+)개", raw))

    elif category == "gpu":
        chipset = _match(
            r"\b(RTX\s*\d+\s*Ti|RTX\s*\d+|"
            r"RX\s*\d+\s*XT|RX\s*\d+|"
            r"Arc\s*(?:Pro\s*)?[A-Z]\d+)\b",
            f"{raw} {model_name}",
        )

        if chipset:
            result["chipset"] = _clean(chipset)

        vram = re.findall(r"(\d+)\s*GB", model_name, re.IGNORECASE)

        if vram:
            result["vram_gb"] = int(vram[-1])

        memory_type = _match(r"\b(GDDR\d+)\b", raw)

        if memory_type:
            result["memory_type"] = memory_type.upper()

        _put(
            result,
            "recommended_psu_w",
            _number(r"(\d+)\s*W\s*이상", raw),
        )
        _put(
            result,
            "power_connector",
            _match(r"전원 포트\s*:\s*([^/]+)", raw),
        )
        _put(
            result,
            "length_mm",
            _number(
                r"가로\(길이\)\s*:\s*([\d.]+)\s*mm",
                raw,
                True,
            ),
        )
        _put(
            result,
            "base_clock_mhz",
            _number(
                r"베이스클럭\s*:\s*([\d.]+)(?:\s*MHz)?",
                raw,
                True,
            ),
        )
        _put(
            result,
            "boost_clock_mhz",
            _number(
                r"부스트클럭\s*:\s*([\d.]+)\s*MHz",
                raw,
                True,
            ),
        )
        _put(
            result,
            "stream_processors",
            _number(r"스트림 프로세서\s*:\s*(\d+)", raw),
        )
        _put(
            result,
            "power_w",
            _number(r"사용전력\s*:\s*(\d+)\s*W", raw),
        )
        _put(
            result,
            "fan_count",
            _number(r"(?:^|\s|/)\s*(\d+)\s*팬(?:\s|/|$)", raw),
        )
        _put(
            result,
            "thickness_mm",
            _number(
                r"두께\s*:\s*([\d.]+)\s*mm",
                raw,
                True,
            ),
        )

    elif category == "case":
        supported = _match(r"지원보드규격\s*:\s*([^/]+)", raw)

        if supported:
            forms = list(dict.fromkeys(
                value.upper()
                for value in re.findall(
                    r"E-?ATX|M-ATX|M-ITX|ATX",
                    supported,
                    re.IGNORECASE,
                )
            ))
            result["supported_form_factors"] = forms
            result["motherboard_form_factors"] = forms

        mappings = {
            "max_gpu_length_mm": r"VGA 길이\s*:\s*([\d.]+)\s*mm",
            "max_cooler_height_mm": r"CPU쿨러 높이\s*:\s*([\d.]+)\s*mm",
            "width_mm": r"너비\(W\)\s*:\s*([\d.]+)\s*mm",
            "height_mm": r"높이\(H\)\s*:\s*([\d.]+)\s*mm",
            "depth_mm": r"깊이\(D\)\s*:\s*([\d.]+)\s*mm",
        }

        for key, pattern in mappings.items():
            _put(result, key, _number(pattern, raw, True))

    elif category == "psu":
        wattage = _number(r"(?:^|/)\s*(\d{3,4})W(?:\s|/)", raw)

        if wattage is None:
            wattage = _number(r"\b(\d{3,4})W\b", model_name)

        _put(result, "wattage", wattage)

        if raw.startswith("ATX 파워"):
            result["form_factor"] = "ATX"
        elif raw.startswith("M-ATX 파워"):
            result["form_factor"] = "M-ATX"

        _put(result, "modular_type", _match(r"케이블연결\s*:\s*([^/]+)", raw))

    elif category == "cooler":
        if "수랭" in raw:
            result["cooler_type"] = "liquid"
        elif "공랭" in raw:
            result["cooler_type"] = "air"

        _put(result, "max_tdp_w", _number(r"TDP\s*:\s*(\d+)\s*W", raw))

        sockets = list(dict.fromkeys(
            value.upper()
            for value in re.findall(
                r"\b(LGA\d{4}|LGA115x|AM[345]|FM[12]\+?|TR4|sTRX4|sWRX8)\b",
                raw,
                re.IGNORECASE,
            )
        ))

        if sockets:
            result["supported_sockets"] = sockets

        rows = _number(r"라디에이터\s*:\s*(\d+)열", raw)

        if rows:
            result["radiator_size_mm"] = int(rows) * 120

        _put(
            result,
            "height_mm",
            _number(r"(?:전체 높이|높이)\s*:\s*([\d.]+)\s*mm", raw, True),
        )

    elif category == "storage":
        _put(result, "capacity_gb", _capacity_gb(model_name))

        result["storage_type"] = (
            "hdd"
            if "7200/" in raw or "5400/" in raw
            else "ssd"
        )

        _put(
            result,
            "form_factor",
            _match(r"^(M\.2\s*\(\d+\)|\d\.\d인치|\d\.\d형)", raw),
        )
        _put(
            result,
            "interface",
            _match(r"\b(PCIe\d\.\dx\d|SATA3|SATA)\b", raw),
        )

    return result


def _load_part(part_id: int) -> dict[str, object] | None:
    with connect_database() as connection:
        row = connection.execute(
            '''
            SELECT
                id,
                category,
                model_name,
                specifications
            FROM parts
            WHERE id = ?
            ''',
            (part_id,),
        ).fetchone()

    if row is None:
        return None

    try:
        specifications = json.loads(row["specifications"])
    except (TypeError, json.JSONDecodeError):
        specifications = {}

    return {
        "id": int(row["id"]),
        "category": str(row["category"]),
        "model_name": str(row["model_name"]),
        "specifications": specifications,
    }


def list_part_ids() -> list[int]:
    with connect_database() as connection:
        rows = connection.execute(
            "SELECT id FROM parts ORDER BY id"
        ).fetchall()

    return [int(row["id"]) for row in rows]


def update_parts(part_ids: list[int]) -> dict[str, object]:
    ids = sorted({
        int(part_id)
        for part_id in part_ids
        if int(part_id) > 0
    })

    session = requests.Session()
    session.headers.update({
        "User-Agent": "PC-Auto-Builder/1.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })

    robots_checked = False
    updated = 0
    failed = 0
    errors: list[dict[str, object]] = []

    for index, part_id in enumerate(ids, start=1):
        try:
            part = _load_part(part_id)

            if part is None:
                raise ValueError("부품을 찾을 수 없습니다.")

            old_specs = part["specifications"]

            if not isinstance(old_specs, dict):
                old_specs = {}

            source_url = (
                old_specs.get("source_url")
                or old_specs.get("spec_source_url")
            )

            if not source_url:
                raise ValueError("출처 링크가 없습니다.")

            source_url = str(source_url)

            if urlparse(source_url).netloc.lower() != "prod.danawa.com":
                raise ValueError("현재는 다나와 출처만 지원합니다.")

            if not robots_checked:
                allowed, reason = robots_allows(source_url)

                if not allowed:
                    raise ValueError(reason)

                robots_checked = True

            response = session.get(source_url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()

            raw = _extract_raw_spec(response.text)

            if not raw:
                raise ValueError("상세 스펙을 찾지 못했습니다.")

            category = _infer_category(
                source_url,
                str(part["category"]),
                raw,
            )

            parsed = _parse(
                category,
                raw,
                str(part["model_name"]),
            )

            parsed.update({
                "spec_source_url": source_url,
                "spec_source_name": "prod.danawa.com",
                "spec_updated_at": datetime.now(timezone.utc).isoformat(),
                "spec_parse_status": "success",
            })

            merged = {**old_specs, **parsed}

            with connect_database() as connection:
                connection.execute(
                    '''
                    UPDATE parts
                    SET
                        category = ?,
                        specifications = ?
                    WHERE id = ?
                    ''',
                    (
                        category,
                        json.dumps(merged, ensure_ascii=False),
                        part_id,
                    ),
                )
                connection.commit()

            updated += 1

        except Exception as error:
            failed += 1
            errors.append({
                "part_id": part_id,
                "message": str(error),
            })

        if index < len(ids):
            time.sleep(REQUEST_DELAY_SECONDS)

    seed_saved = False
    seed_error = None

    try:
        save_seed_file()
        seed_saved = True
    except Exception as error:
        seed_error = str(error)

    return {
        "total": len(ids),
        "updated": updated,
        "failed": failed,
        "seed_saved": seed_saved,
        "seed_error": seed_error,
        "errors": errors,
    }
