import json
import os
import sqlite3
from pathlib import Path


_DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[2]
    / "pc_parts.db"
)

DATABASE_PATH = Path(
    os.getenv(
        "PC_PARTS_DB_PATH",
        str(_DEFAULT_DATABASE_PATH),
    )
).expanduser()

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

INITIAL_PARTS: list[dict[str, object]] = [
    {
        "id": 1,
        "category": "cpu",
        "manufacturer": "AMD",
        "model_name": "Ryzen 5 7600",
        "price": 230000,
        "specifications": {
            "socket": "AM5",
            "cores": 6,
            "threads": 12,
        },
    },
    {
        "id": 2,
        "category": "motherboard",
        "manufacturer": "MSI",
        "model_name": "PRO B650M-A WIFI",
        "price": 190000,
        "specifications": {
            "socket": "AM5",
            "ram_type": "DDR5",
            "form_factor": "Micro-ATX",
        },
    },
    {
        "id": 3,
        "category": "motherboard",
        "manufacturer": "ASUS",
        "model_name": "PRIME B450M-A",
        "price": 90000,
        "specifications": {
            "socket": "AM4",
            "ram_type": "DDR4",
            "form_factor": "Micro-ATX",
        },
    },
    {
        "id": 4,
        "category": "gpu",
        "manufacturer": "MSI",
        "model_name": "GeForce RTX 4060 VENTUS 2X",
        "price": 430000,
        "specifications": {
            "vram_gb": 8,
            "length_mm": 199,
            "recommended_psu_w": 550,
        },
    },
    {
        "id": 5,
        "category": "ram",
        "manufacturer": "Samsung",
        "model_name": "DDR5 16GB 5600MHz",
        "price": 60000,
        "specifications": {
            "ram_type": "DDR5",
            "capacity_gb": 16,
            "speed_mhz": 5600,
        },
    },
    {
        "id": 6,
        "category": "ram",
        "manufacturer": "Samsung",
        "model_name": "DDR4 16GB 3200MHz",
        "price": 45000,
        "specifications": {
            "ram_type": "DDR4",
            "capacity_gb": 16,
            "speed_mhz": 3200,
        },
    },
    {
        "id": 7,
        "category": "case",
        "manufacturer": "Example",
        "model_name": "Standard M-ATX Case",
        "price": 55000,
        "specifications": {
            "supported_form_factors": [
                "ATX",
                "Micro-ATX",
                "Mini-ITX",
            ],
            "max_gpu_length_mm": 330,
            "max_cooler_height_mm": 160,
            "width_mm": 210,
            "height_mm": 400,
            "depth_mm": 420,
        },
    },
    {
        "id": 8,
        "category": "case",
        "manufacturer": "Example",
        "model_name": "Compact Mini-ITX Case",
        "price": 70000,
        "specifications": {
            "supported_form_factors": [
                "Mini-ITX",
            ],
            "max_gpu_length_mm": 180,
            "max_cooler_height_mm": 70,
            "width_mm": 170,
            "height_mm": 300,
            "depth_mm": 350,
        },
    },
    {
        "id": 9,
        "category": "psu",
        "manufacturer": "Example",
        "model_name": "600W 80PLUS Bronze",
        "price": 70000,
        "specifications": {
            "wattage": 600,
            "efficiency": "80PLUS Bronze",
            "form_factor": "ATX",
        },
    },
    {
        "id": 10,
        "category": "psu",
        "manufacturer": "Example",
        "model_name": "450W Standard PSU",
        "price": 45000,
        "specifications": {
            "wattage": 450,
            "efficiency": "Standard",
            "form_factor": "ATX",
        },
    },
    {
        "id": 11,
        "category": "case",
        "manufacturer": "Example",
        "model_name": "Compact M-ATX Case",
        "price": 65000,
        "specifications": {
            "supported_form_factors": [
                "Micro-ATX",
                "Mini-ITX",
            ],
            "max_gpu_length_mm": 280,
            "max_cooler_height_mm": 145,
            "width_mm": 185,
            "height_mm": 360,
            "depth_mm": 390,
        },
    },
]


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                model_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                specifications TEXT NOT NULL
            )
            """
        )

        part_count = connection.execute(
            "SELECT COUNT(*) FROM parts"
        ).fetchone()[0]

        if part_count > 0:
            return

        for part in INITIAL_PARTS:
            connection.execute(
                """
                INSERT INTO parts (
                    id,
                    category,
                    manufacturer,
                    model_name,
                    price,
                    specifications
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    part["id"],
                    part["category"],
                    part["manufacturer"],
                    part["model_name"],
                    part["price"],
                    json.dumps(
                        part["specifications"],
                        ensure_ascii=False,
                    ),
                ),
            )

        connection.commit()


def convert_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "id": row["id"],
        "category": row["category"],
        "manufacturer": row["manufacturer"],
        "model_name": row["model_name"],
        "price": row["price"],
        "specifications": json.loads(
            row["specifications"]
        ),
    }


def get_all_parts() -> list[dict[str, object]]:
    with connect_database() as connection:
        rows = connection.execute(
            "SELECT * FROM parts ORDER BY id"
        ).fetchall()

    return [
        convert_row(row)
        for row in rows
    ]


def get_part_by_id(
    part_id: int,
) -> dict[str, object] | None:
    with connect_database() as connection:
        row = connection.execute(
            "SELECT * FROM parts WHERE id = ?",
            (part_id,),
        ).fetchone()

    if row is None:
        return None

    return convert_row(row)
