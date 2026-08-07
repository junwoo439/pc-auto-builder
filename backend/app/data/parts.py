from app.data.database import (
    get_all_parts,
    get_part_by_id,
    initialize_database,
)


initialize_database()

PARTS: list[dict[str, object]] = get_all_parts()


def find_part_by_id(
    part_id: int,
) -> dict[str, object] | None:
    return get_part_by_id(part_id)


def refresh_parts() -> list[dict[str, object]]:
    global PARTS

    PARTS = get_all_parts()
    return PARTS
