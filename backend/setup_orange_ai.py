from __future__ import annotations

from pathlib import Path
import py_compile

BACKEND = Path.cwd()
MAIN = BACKEND / "app" / "main.py"
AI_DIR = BACKEND / "app" / "ai"
MODELS_DIR = AI_DIR / "models"
ROUTERS_DIR = BACKEND / "app" / "routers"

if not MAIN.exists():
    raise SystemExit("Run this script inside the backend folder.")

src = Path(__file__).resolve().parent
AI_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
ROUTERS_DIR.mkdir(parents=True, exist_ok=True)
(AI_DIR / "__init__.py").touch(exist_ok=True)

(AI_DIR / "compatibility_ai.py").write_text(
    (src / "compatibility_ai.py").read_text(encoding="utf-8"),
    encoding="utf-8",
)
(ROUTERS_DIR / "ai_compatibility.py").write_text(
    (src / "ai_compatibility.py").read_text(encoding="utf-8"),
    encoding="utf-8",
)

required_models = [
    "CPU_Board.pkcls",
    "Board_RAM.pkcls",
    "GPU_PSU.pkcls",
    "GPU_Case.pkcls",
    "CPU_Cooler.pkcls",
    "Final_Compatibility.pkcls",
]
missing = [x for x in required_models if not (MODELS_DIR / x).exists()]

text = MAIN.read_text(encoding="utf-8-sig")
import_line = "from app.routers import ai_compatibility"
include_line = "app.include_router(ai_compatibility.router)"

if import_line not in text:
    marker = "app = FastAPI"
    pos = text.find(marker)
    if pos == -1:
        text = import_line + "\n" + text
    else:
        text = text[:pos] + import_line + "\n\n" + text[pos:]

if include_line not in text:
    text = text.rstrip() + "\n\n# Orange Neural Network API\n" + include_line + "\n"

MAIN.write_text(text, encoding="utf-8")

for path in [
    AI_DIR / "compatibility_ai.py",
    ROUTERS_DIR / "ai_compatibility.py",
    MAIN,
]:
    py_compile.compile(str(path), doraise=True)

print("=== Orange AI integration ===")
if missing:
    print("MISSING MODELS:")
    for x in missing:
        print(" -", MODELS_DIR / x)
else:
    print("OK: all 6 .pkcls models exist")

print("OK: Python files installed")
print("OK: app/main.py patched")
print()
print("Start:")
print("  python -m uvicorn app.main:app --reload")
print()
print("Verify AI, not rule conditions:")
print("  http://127.0.0.1:8000/docs")
print("  GET /ai/proof")
print()
print("In /ai/proof check:")
print('  decision_source = "orange_saved_neural_network_models"')
print("  orange_model_class")
print("  estimator_class")
print("  hidden_layer_sizes")
print("  sha256")
