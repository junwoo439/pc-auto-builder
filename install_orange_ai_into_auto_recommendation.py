from __future__ import annotations

from pathlib import Path
import shutil
import sys
from datetime import datetime

AI_HELPERS = '# ============================================================\n# Orange AI integration for automatic recommendation\n# 기존 규칙 엔진은 명백한 비호환 후보를 제거하고,\n# 실제 Orange Neural Network는 남은 후보의 최종 순위를 결정합니다.\n# ============================================================\n\nORANGE_AI_MAX_CANDIDATES = 120\nORANGE_AI_REQUIRED_CATEGORIES = (\n    "cpu",\n    "motherboard",\n    "ram",\n    "gpu",\n    "psu",\n    "case",\n    "cooler",\n)\n\n\ndef _orange_ai_has_full_build(build: PartialBuild) -> bool:\n    return all(\n        isinstance(build.get(category), dict)\n        for category in ORANGE_AI_REQUIRED_CATEGORIES\n    )\n\n\ndef _orange_ai_evaluate_build(\n    build: PartialBuild,\n) -> dict[str, object]:\n    from app.ai.compatibility_ai import check_full_build\n\n    cpu = build["cpu"]\n    board = build["motherboard"]\n    ram = build["ram"]\n    gpu = build["gpu"]\n    psu = build["psu"]\n    computer_case = build["case"]\n    cooler = build["cooler"]\n\n    return check_full_build(\n        cpu=get_specs(cpu),\n        board=get_specs(board),\n        ram=get_specs(ram),\n        gpu=get_specs(gpu),\n        psu=get_specs(psu),\n        case=get_specs(computer_case),\n        cooler=get_specs(cooler),\n    )\n\n\ndef _orange_yes_probability(\n    result: dict[str, object] | None,\n) -> float:\n    if not result:\n        return 0.0\n\n    probabilities = result.get("probabilities")\n    if not isinstance(probabilities, dict):\n        return 0.0\n\n    try:\n        return float(probabilities.get("yes", 0.0))\n    except (TypeError, ValueError):\n        return 0.0'
OLD_SORT = '    candidates.sort(\n        key=lambda build: final_score(\n            build,\n            request,\n        ),\n        reverse=True,\n    )\n\n    selected = candidates[0]\n'
NEW_SORT = '    # 1차: 기존 규칙 기반 점수로 후보를 정렬합니다.\n    candidates.sort(\n        key=lambda build: final_score(\n            build,\n            request,\n        ),\n        reverse=True,\n    )\n\n    # 2차: 실제 Orange Neural Network로 상위 후보를 평가합니다.\n    ai_eligible_candidates = [\n        build\n        for build in candidates\n        if _orange_ai_has_full_build(build)\n    ]\n\n    ai_attempt_pool = ai_eligible_candidates[\n        :ORANGE_AI_MAX_CANDIDATES\n    ]\n\n    ai_attempted = 0\n    ai_successful = 0\n    ai_failed = 0\n    ai_errors: list[str] = []\n    ai_successful_builds: list[PartialBuild] = []\n\n    for build in ai_attempt_pool:\n        ai_attempted += 1\n\n        try:\n            ai_result = _orange_ai_evaluate_build(\n                build\n            )\n\n            build["_orange_ai"] = ai_result\n            ai_successful += 1\n            ai_successful_builds.append(build)\n\n        except Exception as error:\n            ai_failed += 1\n            build["_orange_ai_error"] = (\n                f"{type(error).__name__}: {error}"\n            )\n\n            if len(ai_errors) < 5:\n                ai_errors.append(\n                    str(build["_orange_ai_error"])\n                )\n\n    # 3차: AI 성공 후보가 있으면 AI 판정/확률을 최종 순위에 실제 반영합니다.\n    ai_used_in_ranking = bool(\n        ai_successful_builds\n    )\n\n    if ai_successful_builds:\n        ai_successful_builds.sort(\n            key=lambda build: (\n                (\n                    1\n                    if isinstance(\n                        build.get("_orange_ai"),\n                        dict,\n                    )\n                    and build["_orange_ai"].get(\n                        "prediction"\n                    ) == "yes"\n                    else 0\n                ),\n                _orange_yes_probability(\n                    build.get("_orange_ai")\n                    if isinstance(\n                        build.get("_orange_ai"),\n                        dict,\n                    )\n                    else None\n                ),\n                final_score(\n                    build,\n                    request,\n                ),\n            ),\n            reverse=True,\n        )\n\n        selected = ai_successful_builds[0]\n    else:\n        selected = candidates[0]\n\n    selected_ai = (\n        selected.get("_orange_ai")\n        if isinstance(\n            selected.get("_orange_ai"),\n            dict,\n        )\n        else None\n    )\n\n    selected_ai_probability = (\n        _orange_yes_probability(\n            selected_ai\n        )\n        if selected_ai\n        else None\n    )\n\n    ai_execution_success_rate = (\n        round(\n            ai_successful\n            / ai_attempted\n            * 100,\n            1,\n        )\n        if ai_attempted\n        else 0.0\n    )\n\n    ai_coverage_rate = (\n        round(\n            ai_attempted\n            / len(candidates)\n            * 100,\n            1,\n        )\n        if candidates\n        else 0.0\n    )\n\n    ai_eligible_coverage_rate = (\n        round(\n            ai_attempted\n            / len(ai_eligible_candidates)\n            * 100,\n            1,\n        )\n        if ai_eligible_candidates\n        else 0.0\n    )\n\n    ai_summary = {\n        "enabled": True,\n        "engine": (\n            "Orange Neural Network "\n            "(5 partial models + Final_Compatibility)"\n        ),\n        "used_in_ranking": ai_used_in_ranking,\n        "required_categories": list(\n            ORANGE_AI_REQUIRED_CATEGORIES\n        ),\n        "evaluated_candidates": len(candidates),\n        "eligible_candidates": len(\n            ai_eligible_candidates\n        ),\n        "attempted_candidates": ai_attempted,\n        "successful_candidates": ai_successful,\n        "failed_candidates": ai_failed,\n        "coverage_rate_percent": (\n            ai_coverage_rate\n        ),\n        "eligible_coverage_rate_percent": (\n            ai_eligible_coverage_rate\n        ),\n        "execution_success_rate_percent": (\n            ai_execution_success_rate\n        ),\n        "selected_prediction": (\n            selected_ai.get("prediction")\n            if selected_ai\n            else None\n        ),\n        "selected_yes_probability_percent": (\n            round(\n                selected_ai_probability\n                * 100,\n                1,\n            )\n            if selected_ai_probability\n            is not None\n            else None\n        ),\n        "errors": ai_errors,\n    }\n\n    if not ai_eligible_candidates:\n        ai_summary["reason"] = (\n            "최종 Orange AI는 CPU, 메인보드, RAM, GPU, PSU, "\n            "케이스, 쿨러가 모두 포함된 추천에서 실행됩니다."\n        )\n'
OLD_CHECKS = '    checks = list(\n        dict.fromkeys(\n            str(value)\n            for value in selected["checks"]\n        )\n    )\n'
NEW_CHECKS = '    checks = list(\n        dict.fromkeys(\n            str(value)\n            for value in selected["checks"]\n        )\n    )\n\n    # 기존 화면이 compatibility_checks를 표시한다면 프론트 수정 없이도 보입니다.\n    if ai_used_in_ranking:\n        checks.insert(\n            0,\n            (\n                "Orange AI 자동 추천 적용: 사용됨 | "\n                f"AI 실행 성공률 "\n                f"{ai_execution_success_rate:.1f}% "\n                f"({ai_successful}/{ai_attempted}) | "\n                f"전체 후보 AI 적용률 "\n                f"{ai_coverage_rate:.1f}% "\n                f"({ai_attempted}/{len(candidates)})"\n            ),\n        )\n\n        if selected_ai_probability is not None:\n            checks.insert(\n                1,\n                (\n                    "선택 조합 Orange AI 호환 확률: "\n                    f"{selected_ai_probability * 100:.1f}% "\n                    f"| 판정: "\n                    f"{selected_ai.get(\'prediction\')}"\n                ),\n            )\n    else:\n        checks.insert(\n            0,\n            (\n                "Orange AI 자동 추천 적용: 미사용 | "\n                f"실행 시도 {ai_attempted}건, "\n                f"성공 {ai_successful}건"\n            ),\n        )\n'
OLD_RETURN_FIELD = '        "compatibility_checks": checks,\n'
NEW_RETURN_FIELD = '        "ai": ai_summary,\n        "compatibility_checks": checks,\n'


def locate_recommendations() -> Path:
    cwd = Path.cwd()
    candidates = [
        cwd / "app" / "routers" / "recommendations.py",
        cwd / "backend" / "app" / "routers" / "recommendations.py",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise SystemExit(
        "recommendations.py를 찾을 수 없습니다. "
        "프로젝트 루트 또는 backend 폴더에서 실행하세요."
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        raise SystemExit(
            f"[실패] {label} 위치를 찾지 못했습니다. "
            "recommendations.py가 제공된 코드와 다른 버전일 수 있습니다."
        )
    if count > 1:
        raise SystemExit(
            f"[실패] {label} 위치가 {count}개 발견되었습니다."
        )
    return text.replace(old, new, 1)


def main() -> None:
    path = locate_recommendations()
    print("대상:", path)

    text = path.read_text(encoding="utf-8-sig")

    if "ORANGE_AI_MAX_CANDIDATES = 120" in text:
        print("이미 Orange AI 자동추천 패치가 적용되어 있습니다.")
        return

    if '@router.post("/auto")' not in text:
        raise SystemExit('[실패] @router.post("/auto")를 찾지 못했습니다.')

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"recommendations.py.backup-{timestamp}")
    shutil.copy2(path, backup)
    print("백업:", backup)

    text = text.replace(
        '@router.post("/auto")',
        AI_HELPERS + '\n\n@router.post("/auto")',
        1,
    )

    text = replace_once(text, OLD_SORT, NEW_SORT, "후보 정렬/선택 블록")
    text = replace_once(text, OLD_CHECKS, NEW_CHECKS, "compatibility_checks 생성 블록")
    text = replace_once(text, OLD_RETURN_FIELD, NEW_RETURN_FIELD, "최종 응답 블록")

    path.write_text(text, encoding="utf-8")
    print("수정 완료:", path)

    import py_compile
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        print("문법 검사 실패. 백업을 복구합니다.")
        shutil.copy2(backup, path)
        raise

    print("문법 검사: OK")

    backend_dir = path.parent.parent.parent
    sys.path.insert(0, str(backend_dir))

    try:
        from app.ai.compatibility_ai import check_full_build
        if not callable(check_full_build):
            raise RuntimeError("check_full_build is not callable")
        print("Orange AI 모듈 로드: OK")
    except Exception as error:
        print("주의: Orange AI 로드 검사 오류")
        print(f"{type(error).__name__}: {error}")

    print()
    print("완료.")
    print("서버: python -m uvicorn app.main:app --reload")
    print()
    print("확인할 응답 필드:")
    print("  ai.used_in_ranking")
    print("  ai.execution_success_rate_percent")
    print("  ai.coverage_rate_percent")
    print("  ai.selected_yes_probability_percent")


if __name__ == "__main__":
    main()
