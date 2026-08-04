PARTS: list[dict[str, object]] = [
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
]


def find_part_by_id(part_id: int) -> dict[str, object] | None:
    for part in PARTS:
        if part["id"] == part_id:
            return part

    return None