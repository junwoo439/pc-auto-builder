from __future__ import annotations

import py_compile
import shutil
from pathlib import Path


def find_project_root() -> Path:
    candidates = [Path.cwd(), *Path.cwd().parents]

    for candidate in candidates:
        target = (
            candidate
            / "backend"
            / "app"
            / "services"
            / "danawa_spec_updater.py"
        )

        if target.exists():
            return candidate

    raise SystemExit(
        "pc-auto-builder 프로젝트 최상위 폴더에서 실행하세요. "
        "backend/app/services/danawa_spec_updater.py를 찾지 못했습니다."
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"이미 적용됨: {label}")
        return text

    if old not in text:
        raise SystemExit(
            f"패치 위치를 찾지 못했습니다: {label}\n"
            "danawa_spec_updater.py 내용이 예상 버전과 다를 수 있습니다."
        )

    print(f"적용: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    root = find_project_root()
    target = (
        root
        / "backend"
        / "app"
        / "services"
        / "danawa_spec_updater.py"
    )
    backup = target.with_suffix(
        ".py.before_gpu_parser_fix"
    )

    original = target.read_text(encoding="utf-8-sig")

    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"백업 생성: {backup}")

    text = original

    text = replace_once(
        text,
        '''        "danawa_spec_items": [\n            item.strip()\n            for item in raw.split("/")\n            if item.strip()\n        ],''',
        '''        "danawa_spec_items": [\n            item.strip()\n            for item in re.split(r"\\s+/\\s+", raw)\n            if item.strip()\n        ],''',
        "A/S가 분리되지 않도록 스펙 항목 분리 개선",
    )

    old_gpu = '''    elif category == "gpu":\n        vram = re.findall(r"(\\d+)\\s*GB", model_name, re.IGNORECASE)\n\n        if vram:\n            result["vram_gb"] = int(vram[-1])\n\n        _put(result, "recommended_psu_w", _number(r"(\\d+)W\\s*이상", raw))\n        _put(\n            result,\n            "length_mm",\n            _number(r"가로\\(길이\\):\\s*([\\d.]+)mm", raw, True),\n        )\n        _put(result, "power_w", _number(r"사용전력:\\s*(\\d+)W", raw))\n        _put(\n            result,\n            "thickness_mm",\n            _number(r"두께:\\s*([\\d.]+)mm", raw, True),\n        )\n'''

    new_gpu = '''    elif category == "gpu":\n        chipset = _match(\n            r"\\b(RTX\\s*\\d+\\s*Ti|RTX\\s*\\d+|"\n            r"RX\\s*\\d+\\s*XT|RX\\s*\\d+|"\n            r"Arc\\s*(?:Pro\\s*)?[A-Z]\\d+)\\b",\n            f"{raw} {model_name}",\n        )\n\n        if chipset:\n            result["chipset"] = _clean(chipset)\n\n        vram = re.findall(r"(\\d+)\\s*GB", model_name, re.IGNORECASE)\n\n        if vram:\n            result["vram_gb"] = int(vram[-1])\n\n        memory_type = _match(r"\\b(GDDR\\d+)\\b", raw)\n\n        if memory_type:\n            result["memory_type"] = memory_type.upper()\n\n        _put(\n            result,\n            "recommended_psu_w",\n            _number(r"(\\d+)\\s*W\\s*이상", raw),\n        )\n        _put(\n            result,\n            "power_connector",\n            _match(r"전원 포트\\s*:\\s*([^/]+)", raw),\n        )\n        _put(\n            result,\n            "length_mm",\n            _number(\n                r"가로\\(길이\\)\\s*:\\s*([\\d.]+)\\s*mm",\n                raw,\n                True,\n            ),\n        )\n        _put(\n            result,\n            "base_clock_mhz",\n            _number(\n                r"베이스클럭\\s*:\\s*([\\d.]+)(?:\\s*MHz)?",\n                raw,\n                True,\n            ),\n        )\n        _put(\n            result,\n            "boost_clock_mhz",\n            _number(\n                r"부스트클럭\\s*:\\s*([\\d.]+)\\s*MHz",\n                raw,\n                True,\n            ),\n        )\n        _put(\n            result,\n            "stream_processors",\n            _number(r"스트림 프로세서\\s*:\\s*(\\d+)", raw),\n        )\n        _put(\n            result,\n            "power_w",\n            _number(r"사용전력\\s*:\\s*(\\d+)\\s*W", raw),\n        )\n        _put(\n            result,\n            "fan_count",\n            _number(r"(?:^|\\s|/)\\s*(\\d+)\\s*팬(?:\\s|/|$)", raw),\n        )\n        _put(\n            result,\n            "thickness_mm",\n            _number(\n                r"두께\\s*:\\s*([\\d.]+)\\s*mm",\n                raw,\n                True,\n            ),\n        )\n'''

    text = replace_once(
        text,
        old_gpu,
        new_gpu,
        "GPU 상세 규격 정규화",
    )

    replacements = {
        'r"(?:PBP|TDP):\\s*(\\d+)W"': (
            'r"(?:PBP|TDP)\\s*:\\s*(\\d+)\\s*W"'
        ),
        'r"메모리 용량:\\s*최대\\s*(\\d+)GB"': (
            'r"메모리 용량\\s*:\\s*최대\\s*(\\d+)\\s*GB"'
        ),
        'r"M\\.2:\\s*(\\d+)개"': (
            'r"M\\.2\\s*:\\s*(\\d+)개"'
        ),
        'r"램개수:\\s*(\\d+)개"': (
            'r"램개수\\s*:\\s*(\\d+)개"'
        ),
        'r"지원보드규격:\\s*([^/]+)"': (
            'r"지원보드규격\\s*:\\s*([^/]+)"'
        ),
        'r"VGA 길이:\\s*([\\d.]+)mm"': (
            'r"VGA 길이\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
        'r"CPU쿨러 높이:\\s*([\\d.]+)mm"': (
            'r"CPU쿨러 높이\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
        'r"너비\\(W\\):\\s*([\\d.]+)mm"': (
            'r"너비\\(W\\)\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
        'r"높이\\(H\\):\\s*([\\d.]+)mm"': (
            'r"높이\\(H\\)\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
        'r"깊이\\(D\\):\\s*([\\d.]+)mm"': (
            'r"깊이\\(D\\)\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
        'r"케이블연결:\\s*([^/]+)"': (
            'r"케이블연결\\s*:\\s*([^/]+)"'
        ),
        'r"TDP:\\s*(\\d+)W"': (
            'r"TDP\\s*:\\s*(\\d+)\\s*W"'
        ),
        'r"라디에이터:\\s*(\\d+)열"': (
            'r"라디에이터\\s*:\\s*(\\d+)열"'
        ),
        'r"(?:전체 높이|높이):\\s*([\\d.]+)mm"': (
            'r"(?:전체 높이|높이)\\s*:\\s*([\\d.]+)\\s*mm"'
        ),
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    target.write_text(text, encoding="utf-8")

    py_compile.compile(
        str(target),
        doraise=True,
    )

    print(f"패치 완료: {target}")
    print("문법 검사 완료")
    print()
    print("다음 단계:")
    print("1. 서버를 재시작합니다.")
    print("2. 관리자 화면에서 GPU 한 개를 선택합니다.")
    print("3. '선택 부품 상세 규격 갱신'을 누릅니다.")


if __name__ == "__main__":
    main()
