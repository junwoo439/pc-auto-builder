from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pc-auto-builder-test-") as directory:
        os.environ["PC_PARTS_DB_PATH"] = str(Path(directory) / "test.db")
        os.environ.setdefault("ADMIN_API_KEY", "self-test-key")

        from app.data.database import get_all_parts
        from app.main import app
        from app.routers.recommendations import (
            RecommendationRequest,
            cpu_cooler_included,
            has_integrated_graphics,
            recommend_build,
        )
        from app.services.product_importer import normalize_url

        async def run() -> None:
            async with app.router.lifespan_context(app):
                parts = get_all_parts()
                assert len(parts) == 100, f"시드 복원 실패: {len(parts)}개"

                result = recommend_build(
                    RecommendationRequest(
                        budget=1_500_000,
                        purpose="office",
                        selected_categories=[
                            "cpu",
                            "motherboard",
                            "ram",
                            "case",
                            "psu",
                            "storage",
                        ],
                        max_width_mm=260,
                        max_height_mm=600,
                        max_depth_mm=600,
                    )
                )
                assert result["found"], result
                cpu = next(
                    part for part in result["parts"] if part["category"] == "cpu"
                )
                assert has_integrated_graphics(cpu), cpu["model_name"]
                assert cpu_cooler_included(cpu), cpu["model_name"]
                assert result["verification_level"] == "basic_compatibility_checked"

                try:
                    normalize_url("http://127.0.0.1:8000/admin")
                except ValueError:
                    pass
                else:
                    raise AssertionError("SSRF 내부 주소 차단 실패")

                print("[OK] 시드 100개 복원")
                print(f"[OK] 무GPU 추천 CPU: {cpu['model_name']}")
                print("[OK] 내장그래픽/기본 쿨러 필터")
                print("[OK] 내부 주소 수집 차단")
                print("[OK] 자체 점검 완료")

        asyncio.run(run())


if __name__ == "__main__":
    main()
