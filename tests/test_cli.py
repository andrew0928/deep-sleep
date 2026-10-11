"""Integration tests run the actual Bash entry point against a disk/power model."""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"
UUID_C = "33333333-3333-3333-3333-333333333333"


class CLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="deep-sleep-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.user_dir = self.base / "user"
        self.user_dir.mkdir()
        self.state_dir = self.user_dir / ".deep-sleep" / "state"
        self.journal = self.state_dir / "pending"
        self.fixture = self.base / "model.json"
        self.state = {
            "calls": [],
            "volumes": [
                {"uuid": UUID_A, "path": "/Volumes/My Backup", "mounted": True},
                {"uuid": UUID_B, "path": "/Volumes/Archive", "mounted": True},
                {"uuid": UUID_C, "path": "/Volumes/Offline", "mounted": False},
            ],
        }
        # No environment hook exists in the production executable. Sourcing the
        # script lets this driver replace just the external command adapters.
        adapter = f"{shlex.quote(sys.executable)} {shlex.quote(str(ROOT / 'tests/fake_system.py'))}"
        self.driver = self.base / "driver.sh"
        self.driver.write_text(f"""source {shlex.quote(str(ROOT / 'deep-sleep'))}
ds_user_home() {{ printf '%s\\n' {shlex.quote(str(self.user_dir))}; }}
ds_diskutil() {{ {adapter} diskutil "$@"; }}
ds_pmset() {{ {adapter} pmset "$@"; }}
ds_pause() {{ {adapter} pause "$@"; }}
ds_same_directory() {{ {adapter} same-directory "$@"; }}
ds_main "$@"
""")

    def run_cli(self, *args, code=0):
        self.fixture.write_text(json.dumps(self.state))
        result = subprocess.run(
            ["/bin/bash", str(self.driver), *args], text=True, capture_output=True,
            env={**os.environ, "DEEP_SLEEP_FIXTURE": str(self.fixture)}, timeout=30,
        )
        self.state = json.loads(self.fixture.read_text())
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertFalse((self.state_dir / "lock").exists(), "lock leaked")
        return result

    def mutations(self):
        return [(t, a, tick) for t, a, tick in self.state["calls"]
                if (t == "diskutil" and a[0] in ("unmount", "mount"))
                or (t == "pmset" and a == ["sleepnow"])]

    def config(self, text):
        path = self.user_dir / ".deep-sleep" / ".env"
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        return path

    def pending(self, text):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.journal.write_text(text)

    def run_ids(self):
        return [path.stem for path in (self.state_dir / "runs").glob("*.tsv")]

    def test_help_version_and_all_topics_are_side_effect_free(self):
        for args in [("--help",), ("--version",), ("--skill",),
                     *[("--skill", t) for t in ("overview", "sleep", "recovery")]]:
            result = self.run_cli(*args)
            self.assertTrue(result.stdout)
            self.assertEqual(self.state["calls"], [])
            self.assertFalse(self.state_dir.exists())

    def test_version_source_matches_release_notes(self):
        script = (ROOT / "deep-sleep").read_text()
        source = re.search(r"^ds_version=(\d+\.\d+\.\d+)$", script, re.MULTILINE)
        release = re.search(r"^## (\d+\.\d+\.\d+)\b", (ROOT / "CHANGELOG.md").read_text(), re.MULTILINE)
        self.assertIsNotNone(source)
        self.assertIsNotNone(release)
        self.assertEqual(source.group(1), release.group(1))
        self.assertEqual(self.run_cli("--version").stdout.strip(), f"deep-sleep {source.group(1)}")

    def test_operational_run_reports_version(self):
        result = self.run_cli("--dry-run")
        version = self.run_cli("--version").stdout.strip().split()[-1]
        self.assertIn(f"deep-sleep: version {version}", result.stderr)

    def test_bad_options_and_topics(self):
        for args in [("--unknown",), ("--volume",), ("--volume=",),
                     ("--skill", "oops"), ("--skill=",), ("--config",),
                     ("--help", "--dry-run"), ("--recover", "--volume", UUID_A),
                     ("--", "/Volumes/Archive")]:
            self.run_cli(*args, code=2)
        self.assertEqual(self.state["calls"], [])

    def test_auto_discovery_ignores_legacy_config_and_unmounted_volume(self):
        self.config('DEEP_SLEEP_VOLUME_1="/Volumes/Offline"\n')
        result = self.run_cli("--dry-run")
        self.assertIn(UUID_A, result.stdout)
        self.assertIn(UUID_B, result.stdout)
        self.assertNotIn(UUID_C, result.stdout)
        self.assertEqual(self.mutations(), [])
        self.assertFalse(self.state_dir.exists())

    def test_no_external_mounted_volume_cancels_sleep(self):
        for volume in self.state["volumes"]:
            volume["mounted"] = False
        self.run_cli("--dry-run", code=3)
        self.assertEqual(self.mutations(), [])

    def test_apfs_container_must_be_backed_by_external_physical_disk(self):
        self.state["physical_store"] = "disk40s2"
        self.run_cli("--dry-run", code=3)
        self.assertEqual(self.mutations(), [])

    def test_config_option_is_rejected(self):
        self.run_cli("--config", "/missing", code=2)
        self.run_cli("--config=/missing", code=2)
        self.assertEqual(self.state["calls"], [])

    def test_legacy_config_is_never_executed(self):
        marker = self.base / "INJECTED"
        for expr in [f"$(touch {marker})", f"`touch {marker}`", "${HOME}"]:
            self.config(f'DEEP_SLEEP_VOLUME_1="/Volumes/{expr}"\n')
            self.run_cli("--dry-run")
            self.assertFalse(marker.exists())

    def test_invalid_target_forms(self):
        for target in ["disk2s1", "Archive", "/", "/System/Volumes/Data", "/Volumes/"]:
            self.run_cli("--volume", target, code=2)
        self.assertEqual(self.mutations(), [])

    def test_whole_disk_system_mount_and_missing_uuid_are_rejected(self):
        cases = [{"whole": True}, {"path": "/System/Volumes/Data"},
                 {"missing_keys": ["VolumeUUID"]}, {"missing_keys": ["WritableVolume"]},
                 {"missing_keys": ["WholeDisk"]}, {"whole": "invalid"},
                 {"missing_keys": ["MountPoint"]}, {"path": "not-an-absolute-path"},
                 {"returned_uuid": UUID_B}]
        for patch in cases:
            original = self.state["volumes"][0].copy()
            self.state["volumes"][0].update(patch)
            self.run_cli("--volume", UUID_A, code=3)
            self.state["volumes"][0] = original
        self.assertEqual(self.mutations(), [])

    def test_native_plist_fields_allow_sg_backup_dry_run(self):
        self.state["volumes"][0]["path"] = "/Volumes/sg-backup"
        result = self.run_cli("--dry-run")
        self.assertIn("Unmount, then restore:", result.stdout)
        self.assertIn(UUID_A, result.stdout)
        self.assertEqual(self.mutations(), [])

    def test_empty_mount_point_is_skipped_without_remounting(self):
        result = self.run_cli("--volume", UUID_C)
        self.assertIn("Skip already unmounted:", result.stdout)
        self.assertFalse(self.state["volumes"][2]["mounted"])
        self.assertEqual([(t, a) for t, a, _ in self.mutations()], [("pmset", ["sleepnow"])])

    def test_case_variant_of_same_mount_point_is_accepted(self):
        self.state["volumes"][0].update({
            "path": "/Volumes/SG-Backup", "aliases": ["/Volumes/sg-backup"],
        })
        self.state["same_directories"] = [["/Volumes/sg-backup", "/Volumes/SG-Backup"]]
        result = self.run_cli("--volume", "/Volumes/sg-backup", "--dry-run")
        self.assertIn("Unmount, then restore:", result.stdout)
        self.assertEqual(self.mutations(), [])

    def test_case_variant_that_is_a_different_directory_is_rejected(self):
        self.state["volumes"][0].update({
            "path": "/Volumes/SG-Backup", "aliases": ["/Volumes/sg-backup"],
        })
        self.run_cli("--volume", "/Volumes/sg-backup", "--dry-run", code=3)
        self.assertEqual(self.mutations(), [])

    def test_real_directory_identity_handles_aliases_and_rejects_children(self):
        directory = self.base / "Backup"
        directory.mkdir()
        child = directory / "child"
        child.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        regular_file = self.base / "file"
        regular_file.touch()
        cases = [(directory, directory, 0), (alias, directory, 0),
                 (child, directory, 1), (self.base / "missing", directory, 1),
                 (regular_file, regular_file, 1)]
        # Exercise the production helper, not the integration adapter.
        script = f'source {shlex.quote(str(ROOT / "deep-sleep"))}; ds_same_directory "$1" "$2"'
        for first, second, expected in cases:
            with self.subTest(first=first, second=second):
                result = subprocess.run(["/bin/bash", "-c", script, "test", str(first), str(second)],
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_subdirectory_is_not_a_volume(self):
        self.state["volumes"][0]["aliases"] = ["/Volumes/My Backup/folder"]
        self.run_cli("--volume", "/Volumes/My Backup/folder", code=3)
        self.assertEqual(self.mutations(), [])

    def test_all_targets_validated_before_unmount(self):
        self.run_cli("-v", UUID_A, "-v", "/Volumes/Missing", code=3)
        self.assertEqual(self.mutations(), [])

    def test_full_cycle_deduplicates_and_skips_previously_unmounted(self):
        self.run_cli("-v", "/Volumes/My Backup/", "--volume=" + UUID_A,
                     "-v", UUID_B, "-v", UUID_C)
        operations = self.mutations()
        self.assertEqual([(t, a) for t, a, _ in operations], [
            ("diskutil", ["unmount", UUID_A]), ("diskutil", ["unmount", UUID_B]),
            ("pmset", ["sleepnow"]), ("diskutil", ["mount", UUID_A]),
            ("diskutil", ["mount", UUID_B]),
        ])
        self.assertTrue(all(tick >= 4 for _, a, tick in operations if a[0] == "mount"))
        self.assertFalse(self.state["volumes"][2]["mounted"])
        self.assertFalse(self.journal.exists())

    def test_default_cycle_creates_readable_completed_history(self):
        self.run_cli()
        ids = self.run_ids()
        self.assertEqual(len(ids), 1)
        self.assertIn("complete", self.run_cli("runs", "list").stdout)
        shown = self.run_cli("runs", "show", ids[0]).stdout
        self.assertIn("INTENT\t" + UUID_A, shown)
        self.assertIn("INTENT\t" + UUID_B, shown)
        self.assertIn("DONE\t-\t-", shown)
        self.assertFalse((self.state_dir / "active").exists())

    def test_disconnected_volume_is_unresolved_but_does_not_block_new_cycle(self):
        self.state["volumes"][1]["unavailable_after_sleep"] = True
        self.run_cli("--volume", UUID_B)
        first = self.run_ids()[0]
        self.assertIn("unresolved:1", self.run_cli("runs", "list").stdout)
        self.assertFalse(self.journal.exists())
        self.assertFalse((self.state_dir / "active").exists())
        self.state["requested"] = False
        self.run_cli("--volume", UUID_A)
        self.state["volumes"][1]["unavailable_after_sleep"] = False
        self.run_cli("runs", "recover", first)
        self.assertIn("complete", self.run_cli("runs", "list").stdout)
        self.assertTrue(self.state["volumes"][1]["mounted"])

    def test_dismiss_then_prune_completed_history(self):
        self.state["volumes"][0]["unavailable_after_sleep"] = True
        self.run_cli("--volume", UUID_A)
        run_id = self.run_ids()[0]
        self.run_cli("runs", "prune", "--before", "9999-12-31")
        self.assertEqual(self.run_ids(), [run_id])
        self.run_cli("runs", "dismiss", run_id, UUID_A)
        self.assertIn("DISMISSED\t" + UUID_A, self.run_cli("runs", "show", run_id).stdout)
        self.assertIn("complete", self.run_cli("runs", "list").stdout)
        self.run_cli("runs", "prune", "--before", "9999-12-31")
        self.assertEqual(self.run_ids(), [])

    def test_full_wake_log_alone_is_insufficient(self):
        self.state["graphics_at"] = 7
        self.run_cli("-v", UUID_A)
        mounts = [tick for _, a, tick in self.mutations() if a[0] == "mount"]
        self.assertEqual(mounts, [7])

    def test_dark_wake_does_not_mount_or_time_out(self):
        self.state["dark_only"] = True
        self.run_cli("-v", UUID_A, code=143)
        self.assertGreaterEqual(self.state["tick"], 35)
        self.assertFalse(any(a[0] == "mount" for _, a, _ in self.mutations()))
        self.assertTrue(self.journal.exists())

    def test_first_sleep_without_history(self):
        self.state["empty_history"] = True
        self.run_cli("-v", UUID_A)
        self.assertFalse(self.journal.exists())

    def test_read_only_mount_preserved(self):
        self.state["volumes"][0]["writable"] = False
        self.run_cli("-v", UUID_A)
        self.assertIn(("diskutil", ["mount", "readOnly", UUID_A], 4), self.mutations())

    def test_busy_second_volume_rolls_back_first_and_does_not_sleep(self):
        self.state["volumes"][1]["unmount_fail"] = True
        self.run_cli("-v", UUID_A, "-v", UUID_B, code=4)
        self.assertTrue(self.state["volumes"][0]["mounted"])
        self.assertFalse(any(t == "pmset" for t, _, _ in self.mutations()))
        self.assertFalse(self.journal.exists())

    def test_sleep_request_failure_rolls_back(self):
        self.state["sleep_fail"] = True
        self.run_cli("-v", UUID_A, code=4)
        self.assertTrue(self.state["volumes"][0]["mounted"])
        self.assertFalse(self.journal.exists())

    def test_unmount_success_is_verified(self):
        self.state["volumes"][0]["stay_mounted"] = True
        self.run_cli("-v", UUID_A, code=4)
        self.assertFalse(any(t == "pmset" for t, _, _ in self.mutations()))

    def test_delayed_device_retries_by_uuid(self):
        self.state["volumes"][0]["mount_after"] = 3
        self.run_cli("-v", UUID_A)
        self.assertEqual(self.state["volumes"][0]["attempts"], 3)

    def test_restore_failure_keeps_journal_and_recovers_later(self):
        self.state["volumes"][0]["mount_fail"] = True
        self.run_cli("-v", UUID_A, code=6)
        self.assertTrue(self.journal.exists())
        self.assertTrue((self.state_dir / "active").exists())
        self.assertEqual(self.state["volumes"][0]["attempts"], 5)
        self.run_cli("-v", UUID_B, code=7)
        self.state["volumes"][0]["mount_fail"] = False
        self.run_cli("--recover")
        self.assertFalse(self.journal.exists())
        self.assertFalse((self.state_dir / "active").exists())

    def test_mount_success_without_mounted_state_fails(self):
        self.state["volumes"][0]["mount_lies"] = True
        self.run_cli("-v", UUID_A, code=6)
        self.assertTrue(self.journal.exists())

    def test_no_new_sleep_never_mounts_prematurely(self):
        self.state["never_sleep"] = True
        self.run_cli("-v", UUID_A, code=5)
        self.assertFalse(any(a[0] == "mount" for _, a, _ in self.mutations()))
        self.assertTrue(self.journal.exists())

    def test_bad_power_history_and_transition_abort_before_unmount(self):
        for flag in ["bad_log", "bad_systemstate", "transition"]:
            self.state[flag] = True
            self.run_cli("-v", UUID_A, code=3)
            self.state[flag] = False
        self.assertEqual(self.mutations(), [])

    def test_log_failure_after_request_keeps_journal(self):
        self.state["bad_log_after_sleep"] = True
        self.run_cli("-v", UUID_A, code=5)
        self.assertTrue(self.journal.exists())
        self.assertFalse(any(a[0] == "mount" for _, a, _ in self.mutations()))

    def test_term_during_unmount_rolls_back(self):
        self.state["volumes"][0]["signal_unmount"] = True
        self.run_cli("-v", UUID_A, code=143)
        self.assertTrue(self.state["volumes"][0]["mounted"])
        self.assertFalse(self.journal.exists())

    def test_term_after_sleep_request_preserves_journal(self):
        self.state["signal_sleep"] = True
        self.run_cli("-v", UUID_A, code=143)
        self.assertFalse(self.state["volumes"][0]["mounted"])
        self.assertTrue(self.journal.exists())

    def test_recovery_dry_run_reads_only_journal(self):
        self.pending(f"{UUID_A} readOnly\n")
        self.state["volumes"][0]["mounted"] = False
        result = self.run_cli("--recover", "--dry-run")
        self.assertIn(UUID_A, result.stdout)
        self.assertEqual(self.state["calls"], [])
        self.assertTrue(self.journal.exists())

    def test_recovery_handles_unterminated_journal_and_already_mounted(self):
        self.pending(f"{UUID_A} readWrite\n{UUID_B} readOnly")
        self.state["volumes"][1]["mounted"] = False
        self.run_cli("--recover")
        self.assertEqual([(t, a) for t, a, _ in self.mutations()], [
            ("diskutil", ["mount", "readOnly", UUID_B])])
        self.assertFalse(self.journal.exists())

    def test_invalid_journal_validated_before_mount(self):
        self.pending(f"{UUID_A} readWrite\nnot-a-uuid readWrite\n")
        self.run_cli("--recover", code=7)
        self.assertEqual(self.mutations(), [])

    def test_no_pending_recovery(self):
        self.run_cli("--recover")
        self.assertEqual(self.mutations(), [])

    def test_existing_lock_is_not_broken(self):
        lock = self.state_dir / "lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text("12345\n")
        self.fixture.write_text(json.dumps(self.state))
        result = subprocess.run(["/bin/bash", str(self.driver), "--volume", UUID_A],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertTrue(lock.exists())
        self.assertEqual(json.loads(self.fixture.read_text())["calls"], [])


if __name__ == "__main__":
    unittest.main()
