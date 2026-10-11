"""Disk/power simulator. Only the test driver imports this command adapter."""
import json
import os
import plistlib
import signal
import sys
from pathlib import Path

state_path = Path(os.environ["DEEP_SLEEP_FIXTURE"])
state = json.loads(state_path.read_text())
tool, *args = sys.argv[1:]
state["calls"].append([tool, args, state.get("tick", 0)])


def save():
    state_path.write_text(json.dumps(state))


def finish(code=0, text=""):
    save()
    if text:
        print(text)
    sys.exit(code)


if tool == "pause":
    state["tick"] = state.get("tick", 0) + 1
    finish()

if tool == "same-directory":
    # Explicit filesystem identity, independent of diskutil's path resolution.
    finish(0 if args in state.get("same_directories", []) else 1)

if tool == "diskutil":
    verb = args[0]
    if verb == "list":
        physical = {"DeviceIdentifier": "disk4", "Partitions": [
            {"DeviceIdentifier": "disk4s2"}]}
        apfs = {"DeviceIdentifier": "disk5", "APFSPhysicalStores": [
            {"DeviceIdentifier": state.get("physical_store", "disk4s2")}], "APFSVolumes": [
            {"DeviceIdentifier": f"disk5s{i + 1}", **({"MountPoint": v["path"]} if v["mounted"] else {})}
            for i, v in enumerate(state["volumes"])]}
        result = {"AllDisksAndPartitions": [physical] if "physical" in args else [physical, apfs]}
        save()
        sys.stdout.buffer.write(plistlib.dumps(result))
        sys.exit(0)
    target = args[-1]
    if target == "disk4s2" and verb == "info":
        save()
        sys.stdout.buffer.write(plistlib.dumps({"MountPoint": ""}))
        sys.exit(0)
    volume = next(
        (v for i, v in enumerate(state["volumes"]) if target == f"disk5s{i + 1}"
         or target.rstrip("/").upper() == v["uuid"]
         or target.rstrip("/") == v["path"] or target in v.get("aliases", [])), None
    )
    if volume is None:
        finish(1, "Mock: volume unavailable")
    if verb == "info":
        if volume.get("unavailable_after_sleep") and state.get("requested"):
            finish(1)
        result = {
            "VolumeUUID": volume.get("returned_uuid", volume["uuid"]),
            # diskutil info -plist uses WholeDisk and MountPoint, unlike the
            # human-readable labels Whole and Mounted. Unmounted means "".
            "WholeDisk": volume.get("whole", False),
            "MountPoint": volume["path"] if volume["mounted"] else "",
            "WritableVolume": volume.get("writable", True),
            "DeviceIdentifier": "disk99s1" if state.get("requested") else target,
        }
        for key in volume.get("missing_keys", []):
            result.pop(key, None)
        save()
        sys.stdout.buffer.write(plistlib.dumps(result))
        sys.exit(0)
    if verb == "unmount":
        if volume.get("unmount_fail"):
            finish(1, "Mock: busy")
        volume["mounted"] = volume.get("stay_mounted", False)
        save()
        if volume.get("signal_unmount"):
            os.kill(os.getppid(), signal.SIGTERM)
        finish()
    if verb == "mount":
        volume["attempts"] = volume.get("attempts", 0) + 1
        if (volume.get("mount_fail") or (volume.get("unavailable_after_sleep") and state.get("requested"))
                or volume["attempts"] < volume.get("mount_after", 1)):
            finish(1, "Mock: not ready")
        # A success exit alone is insufficient; the CLI must verify Mounted.
        if not volume.get("mount_lies"):
            volume["mounted"] = True
        finish()
    finish(90, "Unexpected diskutil operation")

if tool == "pmset":
    if args == ["sleepnow"]:
        if state.get("sleep_fail"):
            finish(1, "Mock: sleep denied")
        state["requested"] = True
        save()
        if state.get("signal_sleep"):
            os.kill(os.getppid(), signal.SIGTERM)
        finish()
    if args == ["-g", "systemstate"]:
        if state.get("bad_systemstate"):
            finish(text="Internal error")
        if state.get("transition"):
            finish(text="Current System Capabilities are: CPU Graphics Audio Network\nCurrent Power State: 4\nDesired State: 2")
        tick = state.get("tick", 0)
        full = not state.get("requested") or tick >= state.get("graphics_at", 4)
        finish(text="Current System Capabilities are: CPU " + ("Graphics " if full else "") + "Network\nCurrent Power State: 4")
    if args == ["-g", "log"]:
        if state.get("bad_log") or (state.get("bad_log_after_sleep") and state.get("requested")):
            finish(text="Unrecognized power log")
        text = """UUID: AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA
2026-10-10 09:00:00 +0800 Sleep Entering Sleep state due to 'Software Sleep' Using AC 10 secs
2026-10-10 09:00:10 +0800 Wake Wake from Normal Sleep [CDNVA] : due to UserActivity Using AC
"""
        tick = state.get("tick", 0)
        if state.get("empty_history"):
            text = "Showing all currently held IOKit power assertions\n"
        if state.get("requested") and tick >= 1 and not state.get("never_sleep"):
            text += "UUID: BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB\n"
            text += "2026-10-11 01:00:00 +0800 Sleep Entering Sleep state due to 'Software Sleep' Using AC 10 secs\n"
            if tick >= 2:
                text += "2026-10-11 01:00:10 +0800 DarkWake DarkWake from Normal Sleep [CDN] : due to Maintenance Using AC\n"
            if tick >= 3:
                text += "2026-10-11 01:00:11 +0800 Wake Requests [process=powerd request=UserWake]\n"
            if tick >= 4 and not state.get("dark_only"):
                text += "2026-10-11 01:00:12 +0800 Wake DarkWake to FullWake from Normal Sleep [CDNVA] : due to UserActivity Using AC\n"
        # Break a simulated infinite dark-wake wait with TERM, without real sleeps.
        if state.get("dark_only") and tick >= 35:
            save()
            os.kill(os.getppid(), signal.SIGTERM)
        finish(text=text)
    finish(90, "Unexpected pmset operation")

finish(90, "Unexpected tool")
