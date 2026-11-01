#!/usr/bin/env python3
"""Refresh three fully reconciled source caches and emit a private receipt overlay.

The active receipts, bundle, publication, and latest pointer are never modified.
Old caches are copied to a timestamped /tmp preimage directory before atomic swap.
"""
from __future__ import annotations
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_CACHE_DIR = Path("/var/folders/f5/wl08x13j71g9fwy5tgshcdwh0000gp/T/ing03-replay-ocr-20261101-dit__6pn")
BASELINE = {
    "df-competencias-digitais-vol2": {
        "old_cache": "b03e773925d83f1c29ec6ad72129053e6eb717553b216d93138ef6f62e63d2c2",
        "new_cache": "021a8cf02eb66d190fce3db560ecfb954f593b43ad6b6b2b8c354fbde26b0e49",
        "old_receipt": "bddca4d1b8df14887e0972265de9a895b9239f64a5996da740f4bc9cbf2edffd",
        "source": "61ce27903cc1e113a8b9e282c207cce6de6a275847dc935adc052b8417b744c7",
        "config": "cabb76abb66dbaf0fc81b202f50254b48f587f54b21e919f25f4f8d8275ef7aa",
        "items": 74,
        "v2_items": 626,
    },
    "df-competencias-digitais-vol3": {
        "old_cache": "1fa9297b7e186b3df0a2ad396fc5406a94e17d708822e9f9b8cc7a3b6fd1e68e",
        "new_cache": "1fff826b6eae324dfcf4c7deee156476c878248135e4a67780403ac1178df0cb",
        "old_receipt": "1fcb112ea63784ae9265c8d1daf791b30a429e2b800092746cd155586cbe7f2d",
        "source": "39e5f657705d0db6866e8966302ca00cc2eea697e40715d5aac209b9aed7aedd",
        "config": "e47b94bad4537ce62333764ba4850d48a95d5ee6245f59eafcfc01b4d6e053e7",
        "items": 137,
        "v2_items": 1321,
    },
    "sc-lingua-inglesa-ai": {
        "old_cache": "15fbded49c600467990dff6a34964fac0c786de83f135dabb508158e1c650c34",
        "new_cache": "bcc82b4c6c9a59ab19f24387de039c584b3c58d8d0aa30acb6bcf7cc639b0722",
        "old_receipt": "34f45c0e504be9ad241ef746b45baac05d58ca0748658fbc23a4503061b21cb1",
        "source": "3d9c5785a8ab77e944d4ceb3377a0465978d8e92a42bcaa06ea3cd47dfbad2c0",
        "config": "7fdac0cdbca09ff9ef958659c6fc5be040e113124d6a9f570e6b3e2556f47fd6",
        "items": 24,
        "v2_items": 362,
    },
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except Exception:
        try: os.unlink(temp)
        except FileNotFoundError: pass
        raise

def main() -> None:
    sys.path.insert(0, str(ROOT / "pipeline"))
    import ingest
    import ocr as ingest_ocr
    if not CANDIDATE_CACHE_DIR.is_dir():
        raise SystemExit(f"Candidate cache directory unavailable: {CANDIDATE_CACHE_DIR}")
    sources = {source["id"]: source for source in ingest.load_sources()}
    output = ROOT / "docs/evidence/source-audit-ing03-runtime-refresh-20261101/reconciliation"
    preimages = Path(tempfile.mkdtemp(prefix="ing03-runtime-refresh-preimage-20261101-"))
    report = {
        "review_type": "current_runtime_cache_refresh_with_private_receipt_overlay",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor_type": "automated",
        "actor_id": "curriculos-abertos:ing03-runtime-refresh-20261101",
        "candidate_cache_dir": str(CANDIDATE_CACHE_DIR),
        "preimage_backup_dir": str(preimages),
        "preimages": [],
        "sources": [],
        "active_receipts_modified": False,
        "bundle_or_latest_modified": False,
        "database_or_publication_modified": False,
        "whole_source_reconciliation_or_pedagogical_review_reopened": False,
    }
    cache_ops = []
    overlay_ops = []
    for sid, pin in BASELINE.items():
        source = sources[sid]
        assert source["sha256"] == pin["source"]
        dest = ROOT / "data/extracted" / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        candidate = CANDIDATE_CACHE_DIR / dest.name
        active_receipt = ROOT / "data/manifests/reconciliation" / f"{sid}.json"
        old_cache_bytes = dest.read_bytes()
        old_receipt_bytes = active_receipt.read_bytes()
        candidate_bytes = candidate.read_bytes()
        receipt = json.loads(old_receipt_bytes)
        old_cache = json.loads(old_cache_bytes)
        new_cache = json.loads(candidate_bytes)
        assert sha(old_cache_bytes) == pin["old_cache"]
        assert sha(old_receipt_bytes) == pin["old_receipt"]
        assert sha(candidate_bytes) == pin["new_cache"]
        assert receipt["source_id"] == sid and receipt["artifact_sha256"] == source["sha256"]
        assert receipt["v2_gate_result"]["own_source_reconciled"] is True
        assert receipt["v2_gate_result"]["whole_source_reconciled"] is True
        assert receipt["v2_gate_result"]["issues"] == []
        assert receipt["v2_gate_result"]["actual_item_count"] == pin["v2_items"]
        assert old_cache["source_id"] == new_cache["source_id"] == sid
        assert old_cache["sha256"] == new_cache["sha256"] == source["sha256"]
        assert new_cache["extraction_revision"] == ingest.EXTRACTION_REVISION
        assert new_cache["extraction_config_sha256"] == pin["config"] == ingest.extraction_config_hash(source)
        assert new_cache["parser_fingerprint"] == ingest.parser_fingerprint(source)
        assert new_cache["runtime"] == ingest.runtime_identity()
        assert old_cache.get("ocr_pending") == new_cache.get("ocr_pending")
        assert len(old_cache["items"]) == len(new_cache["items"]) == pin["items"]
        item_fields = ("id", "code", "text", "normalized_text", "kind", "positions", "evidence")
        core = lambda cache: [{key: item.get(key) for key in item_fields} for item in cache["items"]]
        assert stable(core(old_cache)) == stable(core(new_cache))
        assert len(old_cache["pages"]) == len(new_cache["pages"])
        changed_pages = [a["page"] for a, b in zip(old_cache["pages"], new_cache["pages"]) if a["text"] != b["text"]]
        assert not changed_pages
        assert old_cache.get("ocr_pending") == new_cache.get("ocr_pending") is False
        ocr_replay = []
        for page in new_cache["pages"]:
            if not page.get("ocr_required"):
                continue
            metadata = page.get("ocr") or {}
            key = metadata.get("cache_key")
            result_sha = metadata.get("result_sha256")
            assert key and result_sha
            ocr_path = ROOT / "data/extracted/ocr" / f"{key}.json"
            result = ingest_ocr._load_cache(ocr_path, key)
            assert result is not None and result.get("result_sha256") == result_sha
            assert result.get("configuration") == metadata.get("configuration")
            assert result.get("artifact_sha256") == source["sha256"] and result.get("page") == page["page"]
            ocr_replay.append({"page": page["page"], "cache_key": key, "result_sha256": result_sha,
                               "configuration": metadata["configuration"]})
        old_copy = preimages / dest.name
        old_copy.write_bytes(old_cache_bytes)
        report["preimages"].append({"path": str(old_copy), "sha256": sha(old_cache_bytes), "source_id": sid})

        runtime = copy.deepcopy(receipt["v2_current_runtime_verification"])
        runtime.update({
            "cache_path": str(dest.relative_to(ROOT)),
            "cache_sha256": sha(candidate_bytes),
            "extraction_revision": new_cache["extraction_revision"],
            "extraction_config_sha256": new_cache["extraction_config_sha256"],
            "parser_fingerprint": new_cache["parser_fingerprint"],
            "runtime": new_cache["runtime"],
        })
        candidate_receipt = copy.deepcopy(receipt)
        candidate_receipt["v2_current_runtime_verification"] = runtime
        overlay_path = output / f"{sid}.json"
        overlay_bytes = (json.dumps(candidate_receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        overlay_ops.append((overlay_path, overlay_bytes))
        cache_ops.append((dest, candidate_bytes))
        report["sources"].append({
            "source_id": sid,
            "source_sha256": source["sha256"],
            "active_cache_preimage_sha256": sha(old_cache_bytes),
            "candidate_cache_sha256": sha(candidate_bytes),
            "active_receipt_preimage_sha256": sha(old_receipt_bytes),
            "overlay_receipt_sha256": sha(overlay_bytes),
            "current_extraction_config_sha256": new_cache["extraction_config_sha256"],
            "current_parser_fingerprint_sha256": new_cache["parser_fingerprint"]["sha256"],
            "pages": len(new_cache["pages"]),
            "page_text_changes": changed_pages,
            "ocr_pending": new_cache.get("ocr_pending"),
            "pinned_ocr_replay": ocr_replay,
            "source_item_count": len(new_cache["items"]),
            "source_items_exactly_equal_to_preimage": True,
            "ocr_pending_unchanged": old_cache.get("ocr_pending") == new_cache.get("ocr_pending"),
            "stored_v2_gate_result_preserved": True,
        })

    for path, data in cache_ops:
        atomic_write(path, data)
    for path, data in overlay_ops:
        atomic_write(path, data)
    report["overlay_directory"] = str(output.relative_to(ROOT))
    report["cache_files_updated"] = [str(path.relative_to(ROOT)) for path, _ in cache_ops]
    report["active_receipt_hashes_after"] = {
        sid: sha((ROOT / "data/manifests/reconciliation" / f"{sid}.json").read_bytes())
        for sid in BASELINE
    }
    report["command_to_revalidate"] = [
        "var/venv-pipeline/bin/python", "pipeline/release_check.py", "--json",
        "--bundle", "data/bundles/ca-7d302a9c674a97b83278.manifest.json",
        "--reconciliation-root", str(output.relative_to(ROOT)),
        "--output", "docs/evidence/source-audit-ing03-runtime-refresh-20261101/candidate-release-check.json",
    ]
    report_path = ROOT / "docs/evidence/source-audit-ing03-runtime-refresh-20261101/cache-refresh-report.json"
    atomic_write(report_path, (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "preimages": str(preimages),
                      "sources": report["sources"], "active_receipts_modified": False}, ensure_ascii=False))

if __name__ == "__main__":
    main()
