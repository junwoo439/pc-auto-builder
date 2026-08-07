from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.compatibility_ai import check_full_build, model_proof

router = APIRouter(prefix="/ai", tags=["ai"])

BACKEND_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("PC_PARTS_DB_PATH", str(BACKEND_DIR / "pc_parts.db")))

PartCategory = Literal[
    "cpu", "motherboard", "ram", "gpu", "case", "psu", "cooler", "storage"
]

class CompatibilityRequest(BaseModel):
    cpu_id: int
    motherboard_id: int
    ram_id: int
    gpu_id: int
    psu_id: int
    case_id: int
    cooler_id: int

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_part(part_id: int, expected_category: str) -> dict:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, category, manufacturer, model_name, price,
                   specifications, source_url
            FROM parts
            WHERE id = ?
            """,
            (part_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Part ID {part_id} not found.")

    if row["category"] != expected_category:
        raise HTTPException(
            status_code=400,
            detail=f"Part ID {part_id} is {row['category']}, not {expected_category}.",
        )

    try:
        specs = json.loads(row["specifications"] or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid specifications JSON for part {part_id}: {exc}",
        ) from exc

    return {
        "id": row["id"],
        "category": row["category"],
        "manufacturer": row["manufacturer"],
        "model_name": row["model_name"],
        "price": row["price"],
        "source_url": row["source_url"],
        "specifications": specs,
    }

@router.get("/health")
def ai_health():
    return {
        "status": "ok",
        "decision_engine": "Orange saved Neural Network models",
        "rule_override_enabled": False,
    }

@router.get("/proof")
def ai_proof():
    # 이걸 열면 실제 로드된 Orange/Sklearn 모델 타입, 파일 hash,
    # 입력 feature, target을 직접 확인할 수 있다.
    return model_proof()

@router.get("/parts/{category}")
def ai_parts(category: PartCategory):
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, manufacturer, model_name, price
            FROM parts
            WHERE category = ?
            ORDER BY id
            """,
            (category,),
        ).fetchall()
    return [dict(row) for row in rows]

@router.post("/compatibility")
def predict_compatibility(request: CompatibilityRequest):
    cpu = _get_part(request.cpu_id, "cpu")
    motherboard = _get_part(request.motherboard_id, "motherboard")
    ram = _get_part(request.ram_id, "ram")
    gpu = _get_part(request.gpu_id, "gpu")
    psu = _get_part(request.psu_id, "psu")
    case = _get_part(request.case_id, "case")
    cooler = _get_part(request.cooler_id, "cooler")

    try:
        result = check_full_build(
            cpu=cpu["specifications"],
            board=motherboard["specifications"],
            ram=ram["specifications"],
            gpu=gpu["specifications"],
            psu=psu["specifications"],
            case=case["specifications"],
            cooler=cooler["specifications"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Orange AI prediction failed: {type(exc).__name__}: {exc}",
        ) from exc

    selected = {
        "cpu": cpu,
        "motherboard": motherboard,
        "ram": ram,
        "gpu": gpu,
        "psu": psu,
        "case": case,
        "cooler": cooler,
    }

    selected_summary = {
        key: {
            "id": value["id"],
            "manufacturer": value["manufacturer"],
            "model_name": value["model_name"],
            "price": value["price"],
        }
        for key, value in selected.items()
    }

    return {
        "ai": "Orange Neural Network",
        "selected_parts": selected_summary,
        **result,
    }
