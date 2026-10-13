"""Passively validate the loaded patch and monitor stability without UI input."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnostics.process_probe import ProcessProbe, clipboard_status
from patching.bitmap_guard import ORIGINAL_SHA256
from switch_runtime import processes


def relevant_events(since):
    query = ("*[System[(EventID=1000 or EventID=1001 or EventID=1002) "
             f"and TimeCreated[@SystemTime >= '{since}']]]")
    command = ["wevtutil", "qe", "Application", "/q:" + query,
               "/f:xml", "/e:Events", "/rd:true", "/c:200"]
    result = subprocess.run(command, capture_output=True, timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("Application event query failed: " + result.stderr.decode(errors="replace"))
    payload = result.stdout
    if b"\x00" in payload[:100]:
        payload = payload.decode("utf-16").encode("utf-8")
    root = ET.fromstring(payload)
    ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
    found = []
    for event in root:
        fields = event.findall("e:EventData/e:Data", ns)
        values = {item.get("Name", str(i)): item.text for i, item in enumerate(fields)}
        if not any(name in str(values).lower() for name in
                   ("mackmlink", "snippingtool", "screenclipping")):
            continue
        found.append({
            "id": event.findtext("e:System/e:EventID", namespaces=ns),
            "utc": event.find("e:System/e:TimeCreated", ns).get("SystemTime"),
            "fields": values,
        })
    return found


def monitor(project, seconds, interval, since):
    info = json.loads((project / "runtime/runtime-info.json").read_text(encoding="utf-8"))
    manifest = json.loads((project / "artifacts/patch-manifest.json").read_text(encoding="utf-8"))
    original, repaired = Path(info["original_executable"]), Path(info["repaired_executable"])
    if project / "runtime" not in repaired.resolve().parents:
        raise ValueError("Repair executable is outside the project runtime")
    if info["original_sha256"] != ORIGINAL_SHA256:
        raise ValueError("Runtime references an unknown original build")
    for path, expected in [(original, ORIGINAL_SHA256), (repaired, manifest["patched_sha256"])]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Unexpected executable hash: {path}")
    _, running = processes()
    if len(running) != 1 or running[0][1] != repaired.resolve():
        raise RuntimeError("Exactly one verified repair instance must be running")
    pid = running[0][0]
    probe = ProcessProbe(pid, repaired)
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    samples, changes = [], []
    try:
        for rva_key, bytes_key in [("patch_rva", "replacement_bytes"), ("guard_rva", "guard_bytes")]:
            expected = bytes.fromhex(manifest[bytes_key])
            if probe.read(manifest[rva_key], len(expected)) != expected:
                raise RuntimeError("Loaded repair bytes differ from the build manifest")
        last_clipboard = None
        while True:
            elapsed = time.monotonic() - start
            resource = probe.sample()
            resource["elapsed_seconds"] = round(elapsed, 4)
            samples.append(resource)
            status = clipboard_status()
            if status != last_clipboard:
                changes.append({"elapsed_seconds": round(elapsed, 4), **status})
                last_clipboard = status
            if not resource["alive"] or elapsed >= seconds:
                break
            time.sleep(min(interval, seconds - elapsed))
    finally:
        probe.close()
    _, ending = processes()
    alive = all(sample["alive"] for sample in samples) and ending == running
    resource_samples = [sample for sample in samples if sample["alive"]]
    cpu = (resource_samples[-1]["cpu_seconds"] - resource_samples[0]["cpu_seconds"]
           if resource_samples else 0)
    duration = time.monotonic() - start
    events = relevant_events(since)
    report = {
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "pid": pid, "runtime_path": str(repaired), "loaded_patch_bytes": "passed",
        "original_hash_unchanged": True, "same_process_survived": alive,
        "duration_seconds": round(duration, 3), "samples": len(samples),
        "cpu_seconds_delta": round(cpu, 6),
        "average_cpu_percent_of_one_core": round(cpu / duration * 100, 3),
        "working_set_range_bytes": ([min(s["working_set_bytes"] for s in resource_samples),
                                     max(s["working_set_bytes"] for s in resource_samples)]
                                    if resource_samples else None),
        "clipboard_metadata_changes": changes,
        "event_query_since_utc": since, "new_relevant_events": events,
        "clipboard_opened_or_modified_by_probe": False, "ui_input_performed": False,
        "limits": ["Passive sampling cannot prove screenshot clipboard insertion or Mac transfer.",
                   "Short clipboard locks may fall between samples.",
                   "GetOpenClipboardWindow may return NULL for a clipboard opened without a window.",
                   "Absence of events does not guarantee absence of a silent failure."],
    }
    target = project / "artifacts/passive-runtime-results.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if alive and not events else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--since", required=True, help="UTC event start, e.g. 2026-10-13T09:14:02.000Z")
    args = parser.parse_args()
    if not 0 < args.seconds <= 3600 or not 0.02 <= args.interval <= 10:
        parser.error("seconds must be 0..3600 and interval 0.02..10")
    raise SystemExit(monitor(Path(__file__).resolve().parents[2], args.seconds, args.interval, args.since))
