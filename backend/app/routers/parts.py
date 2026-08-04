from fastapi import APIRouter


router = APIRouter(
    prefix="/parts",
    tags=["parts"],
)


@router.get("/")
def get_parts() -> list[dict[str, object]]:
    return [
        {
            "id": 1,
            "category": "cpu",
            "manufacturer": "AMD",
            "model_name": "Ryzen 5 7600",
            "price": 230000,
        },
        {
            "id": 2,
            "category": "gpu",
            "manufacturer": "MSI",
            "model_name": "GeForce RTX 4060",
            "price": 430000,
        },
    ]


@router.get("/{part_id}")
def get_part(part_id: int) -> dict[str, object]:
    return {
        "id": part_id,
        "message": f"{part_id}번 부품 조회 테스트",
    }