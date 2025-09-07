from pathlib import Path

def load_qss(theme="dark"):
    root = Path(__file__).parent / "styles"
    parts = [
        (root / "base.qss").read_text(),
        (root / f"{theme}.qss").read_text(),
        (root / "components" / "inputs.qss").read_text(),
    ]
    return "\n".join(p.read_text(encoding="utf-8") for p in parts if p.exists())
