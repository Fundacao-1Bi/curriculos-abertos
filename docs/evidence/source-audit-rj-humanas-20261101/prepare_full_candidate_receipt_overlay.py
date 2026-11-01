#!/usr/bin/env python3
"""Copy the existing private receipt overlay and add RJ Humanas."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_OVERLAY = ROOT / "docs/evidence/source-audit-rj-linguagens-20261101/full-candidate-receipt-overlays"
OUT = ROOT / "docs/evidence/source-audit-rj-humanas-20261101/full-candidate-receipt-overlays-v2"
NEW_RECEIPT = ROOT / "docs/evidence/source-audit-rj-humanas-20261101/rj-em-lab-humanas-2025-whole-source-receipt.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to replace existing overlay folder: {OUT}")
    old_inventory = json.loads((SOURCE_OVERLAY / "overlay-inventory.json").read_text())
    OUT.mkdir(parents=True)
    entries = []
    for item in old_inventory["receipts"]:
        old_path = ROOT / item["path"]
        if sha(old_path) != item["sha256"]:
            raise SystemExit(f"existing overlay receipt hash changed: {old_path}")
        target = OUT / old_path.name
        shutil.copyfile(old_path, target)
        entries.append({
            "source_id": item["source_id"],
            "path": str(target.relative_to(ROOT)),
            "sha256": sha(target),
        })
    new_data = json.loads(NEW_RECEIPT.read_text())
    new_path = OUT / f"{new_data['source_id']}.json"
    shutil.copyfile(NEW_RECEIPT, new_path)
    entries.append({
        "source_id": new_data["source_id"],
        "path": str(new_path.relative_to(ROOT)),
        "sha256": sha(new_path),
    })
    entries.sort(key=lambda item: item["source_id"])
    inventory = {
        "candidate_only": True,
        "base_candidate": "ca-44350ccb5a3d8b75f72d",
        "evaluated_composition_candidate": "ca-b57fa07a470476258cad",
        "receipts": entries,
        "note": "Thirteen verified overlays from the prior private full candidate, plus the independently reconciled RJ Humanas receipt. No receipt is installed in the active directory.",
    }
    (OUT / "overlay-inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "candidate_only": True,
        "receipt_count": len(entries),
        "inventory_sha256": sha(OUT / "overlay-inventory.json"),
        "receipt_ids": [entry["source_id"] for entry in entries],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
