from pathlib import Path
import pickle

MODEL_DIR = Path(__file__).parent / "app" / "ai" / "models"

MODEL_FILES = [
    "CPU_Board.pkcls",
    "Board_RAM.pkcls",
    "GPU_PSU.pkcls",
    "GPU_Case.pkcls",
    "CPU_Cooler.pkcls",
    "Final_Compatibility.pkcls",
]

print("Orange model test")
print("Model directory:", MODEL_DIR)
print()

for filename in MODEL_FILES:
    path = MODEL_DIR / filename

    print("=" * 60)
    print("Model:", filename)

    if not path.exists():
        print("ERROR: File not found")
        print("Path:", path)
        continue

    try:
        with open(path, "rb") as f:
            model = pickle.load(f)

        print("OK: Model loaded")
        print("Type:", type(model))

        print("Features:")

        for variable in model.domain.attributes:
            print(
                " -",
                variable.name,
                "(" + type(variable).__name__ + ")",
            )

        print("Target:")

        if model.domain.class_var is not None:
            target = model.domain.class_var

            print(
                " -",
                target.name,
                "(" + type(target).__name__ + ")",
            )

            if hasattr(target, "values"):
                print(
                    " - Values:",
                    list(target.values),
                )
        else:
            print(" - None")

    except Exception as e:
        print("ERROR: Could not load model")
        print(type(e).__name__ + ":", e)

print()
print("=" * 60)
print("Done")