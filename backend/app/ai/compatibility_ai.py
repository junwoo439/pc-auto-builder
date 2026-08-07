from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import pickle
import re

from Orange.base import Model
from Orange.data import Domain, Table

MODEL_DIR = Path(__file__).resolve().parent / "models"

MODEL_FILES = {
    "CPU_Board": "CPU_Board.pkcls",
    "Board_RAM": "Board_RAM.pkcls",
    "GPU_PSU": "GPU_PSU.pkcls",
    "GPU_Case": "GPU_Case.pkcls",
    "CPU_Cooler": "CPU_Cooler.pkcls",
    "Final_Compatibility": "Final_Compatibility.pkcls",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_model(filename: str):
    path = MODEL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Orange model not found: {path}")
    with path.open("rb") as f:
        model = pickle.load(f)
    return model


MODELS = {name: _load_model(filename) for name, filename in MODEL_FILES.items()}


def _first(specs: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = specs.get(key)
        if value not in (None, "", [], {}, ()):
            return value
    return None


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    return [x.strip() for x in re.split(r"[|,/]+", text) if x.strip()]


def _normal_string(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(x).strip() for x in value if str(x).strip())
    return str(value).strip()


def _coerce_for_variable(variable, value: Any):
    # 아래 조건문들은 "AI 판단"이 아니라 Orange 입력 형식 변환용이다.
    if value is None or value == "":
        return "?", f"{variable.name}: missing"

    if variable.is_continuous:
        try:
            return float(value), None
        except (TypeError, ValueError):
            return "?", f"{variable.name}: expected numeric, got {value!r}"

    if variable.is_discrete:
        raw = _normal_string(value)

        if raw in variable.values:
            return raw, None

        input_items = _items(value)
        if input_items:
            in_set = {x.upper() for x in input_items}
            for allowed in variable.values:
                allowed_items = _items(allowed)
                if allowed_items and {x.upper() for x in allowed_items} == in_set:
                    return allowed, None

        for allowed in variable.values:
            if allowed.upper() == raw.upper():
                return allowed, None

        return "?", (
            f"{variable.name}: unseen category {raw!r}; "
            f"allowed={list(variable.values)!r}"
        )

    return _normal_string(value), None


def _original_input_domain(model) -> Domain:
    original = getattr(model, "original_domain", None)
    if original is None:
        raise RuntimeError("Orange model has no original_domain.")
    return Domain(original.attributes)


def _estimator_info(model) -> dict[str, Any]:
    """
    Orange 래퍼 안에 들어 있는 sklearn MLPClassifier 정보를 가능한 범위에서 추출.
    Orange 버전에 따라 내부 속성명이 다를 수 있어 후보를 순서대로 확인한다.
    """
    candidates = [
        getattr(model, "skl_model", None),
        getattr(model, "model", None),
        getattr(model, "estimator", None),
        getattr(model, "clf", None),
    ]
    estimator = next((x for x in candidates if x is not None), None)

    info = {
        "orange_model_class": f"{type(model).__module__}.{type(model).__name__}",
        "estimator_class": None,
        "hidden_layer_sizes": None,
        "activation": None,
        "solver": None,
        "n_layers_": None,
        "n_outputs_": None,
    }

    if estimator is None:
        return info

    info["estimator_class"] = f"{type(estimator).__module__}.{type(estimator).__name__}"

    for attr in [
        "hidden_layer_sizes",
        "activation",
        "solver",
        "n_layers_",
        "n_outputs_",
    ]:
        if hasattr(estimator, attr):
            value = getattr(estimator, attr)
            if isinstance(value, tuple):
                value = list(value)
            info[attr] = value

    return info


def model_proof() -> dict[str, Any]:
    """
    이 API는 '조건문 판정기'가 아니라 실제 저장된 Orange 모델을
    로드해 사용 중임을 확인하기 위한 진단 정보다.
    """
    result = {}

    for name, filename in MODEL_FILES.items():
        path = MODEL_DIR / filename
        model = MODELS[name]
        original = getattr(model, "original_domain", None)
        target = model.domain.class_var

        result[name] = {
            "file": filename,
            "sha256": _sha256(path),
            "features_before_encoding": (
                [v.name for v in original.attributes]
                if original is not None
                else []
            ),
            "features_model_domain": [v.name for v in model.domain.attributes],
            "target": target.name if target is not None else None,
            "target_values": list(target.values) if target is not None and hasattr(target, "values") else [],
            **_estimator_info(model),
        }

    return {
        "decision_source": "orange_saved_neural_network_models",
        "rule_override_enabled": False,
        "note": (
            "호환 yes/no 최종 판정은 if문으로 직접 정하지 않고 "
            "6개의 Orange 저장 모델의 model(..., ret=ValueProbs) 출력으로 정합니다."
        ),
        "models": result,
    }


def predict_model(model_name: str, feature_values: dict[str, Any]) -> dict[str, Any]:
    """
    핵심 AI 추론 함수.
    여기서 model(...)을 실제 호출하여 Orange/MLP 모델의 예측값과 확률을 받는다.
    """
    model = MODELS[model_name]
    input_domain = _original_input_domain(model)

    row = []
    warnings = []
    used_input = {}

    for variable in input_domain.attributes:
        raw_value = feature_values.get(variable.name)
        converted, warning = _coerce_for_variable(variable, raw_value)
        row.append(converted)
        used_input[variable.name] = raw_value
        if warning:
            warnings.append(warning)

    table = Table.from_list(input_domain, [row])

    # ★ 실제 AI 추론 호출
    values, probabilities = model(table, ret=Model.ValueProbs)

    target = model.domain.class_var
    classes = list(target.values)

    prediction = classes[int(values[0])]
    probs = {
        class_name: float(probabilities[0][i])
        for i, class_name in enumerate(classes)
    }

    return {
        "engine": "Orange saved Neural Network model",
        "model": model_name,
        "prediction": prediction,
        "probabilities": probs,
        "warnings": warnings,
        "input": used_input,
    }


def check_cpu_board(cpu, board):
    return predict_model("CPU_Board", {
        "cpu_socket": _first(cpu, "socket", "cpu_socket"),
        "cpu_memory_types": _first(cpu, "memory_types", "memory_type"),
        "board_socket": _first(board, "socket", "board_socket"),
        "board_memory_type": _first(board, "memory_type", "ram_type"),
        "board_form_factor": _first(board, "form_factor", "board_form_factor"),
    })


def check_board_ram(board, ram):
    return predict_model("Board_RAM", {
        "board_memory_type": _first(board, "memory_type", "ram_type"),
        "ram_memory_type": _first(ram, "memory_type", "ram_type"),
        "ram_capacity_gb": _first(ram, "capacity_gb", "memory_capacity_gb"),
    })


def check_gpu_psu(gpu, psu):
    return predict_model("GPU_PSU", {
        "gpu_required_psu_w": _first(gpu, "recommended_psu_w", "required_psu_w"),
        "gpu_power_w": _first(gpu, "power_w", "tdp_w"),
        "psu_wattage": _first(psu, "wattage", "rated_power_w", "capacity_w", "power_w"),
    })


def check_gpu_case(gpu, case):
    return predict_model("GPU_Case", {
        "gpu_length_mm": _first(gpu, "length_mm", "gpu_length_mm"),
        "case_max_gpu_length_mm": _first(
            case,
            "max_gpu_length_mm",
            "gpu_max_length_mm",
            "vga_max_length_mm",
        ),
    })


def check_cpu_cooler(cpu, cooler):
    return predict_model("CPU_Cooler", {
        "cpu_socket": _first(cpu, "socket", "cpu_socket"),
        "cpu_power_w": _first(cpu, "max_power_w", "tdp_w", "power_w"),
        "cooler_supported_sockets": _first(
            cooler,
            "supported_sockets",
            "socket_support",
            "sockets",
        ),
        "cooler_capacity_w": _first(
            cooler,
            "capacity_w",
            "max_tdp_w",
            "tdp_capacity_w",
        ),
        "cooler_type": _first(cooler, "cooler_type", "type"),
    })


def check_final(cpu_board, board_ram, gpu_psu, gpu_case, cpu_cooler):
    return predict_model("Final_Compatibility", {
        "CPU_Board": cpu_board,
        "Board_RAM": board_ram,
        "GPU_PSU": gpu_psu,
        "GPU_Case": gpu_case,
        "CPU_Cooler": cpu_cooler,
    })


def check_full_build(cpu, board, ram, gpu, psu, case, cooler):
    # 각 결과는 조건문이 아니라 각각의 Orange 모델 추론 결과다.
    checks = {
        "cpu_motherboard": check_cpu_board(cpu, board),
        "motherboard_ram": check_board_ram(board, ram),
        "gpu_psu": check_gpu_psu(gpu, psu),
        "gpu_case": check_gpu_case(gpu, case),
        "cpu_cooler": check_cpu_cooler(cpu, cooler),
    }

    final = check_final(
        checks["cpu_motherboard"]["prediction"],
        checks["motherboard_ram"]["prediction"],
        checks["gpu_psu"]["prediction"],
        checks["gpu_case"]["prediction"],
        checks["cpu_cooler"]["prediction"],
    )

    warnings = []
    for relation, result in checks.items():
        warnings.extend(f"{relation}: {w}" for w in result["warnings"])
    warnings.extend(f"final: {w}" for w in final["warnings"])

    return {
        "decision_source": "Final_Compatibility.pkcls",
        "rule_override_enabled": False,
        "compatible": final["prediction"] == "yes",
        "prediction": final["prediction"],
        "probabilities": final["probabilities"],
        "checks": checks,
        "final_model": final,
        "warnings": warnings,
    }
