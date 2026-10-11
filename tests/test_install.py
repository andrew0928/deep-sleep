import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Installer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        mocks = self.root / 'mocks'
        mocks.mkdir()
        scripts = {
            'uname': '#!/bin/sh\nprintf "%s\\n" "${TEST_OS:-Darwin}"\n',
            'curl': '''#!/bin/sh
case "$2" in
    */deep-sleep) cp "$TEST_REPO/deep-sleep" "$4" ;;
    */examples/config.env)
        [ "${TEST_FAIL_CONFIG:-0}" = 0 ] || exit 22
        cp "$TEST_REPO/examples/config.env" "$4" ;;
    *) exit 2 ;;
esac
''',
        }
        for name, content in scripts.items():
            path = mocks / name
            path.write_text(content)
            path.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(mocks) + ':' + os.environ['PATH'],
                        TEST_REPO=str(ROOT))

    def run_install(self, **changes):
        # Exercise the same stdin execution used by curl | sh.
        return subprocess.run(['/bin/sh'], input=(ROOT / 'install.sh').read_text(),
                              text=True, capture_output=True,
                              env=dict(self.env, **changes))

    def test_installs_executable_and_private_config_without_running_cli(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        binary = self.home / '.local/bin/deep-sleep'
        config = self.home / '.deep-sleep/.env'
        self.assertEqual(binary.read_bytes(), (ROOT / 'deep-sleep').read_bytes())
        self.assertEqual(binary.stat().st_mode & 0o777, 0o755)
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertIn('--dry-run', result.stdout)
        self.assertIn('export PATH=', result.stdout)
        self.assertFalse((self.home / '.deep-sleep/state').exists())

    def test_repeat_install_preserves_configuration(self):
        self.assertEqual(self.run_install().returncode, 0)
        config = self.home / '.deep-sleep/.env'
        config.write_text('DEEP_SLEEP_VOLUME_1="/Volumes/My Backup"\n')
        original = config.read_bytes()
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_bytes(), original)
        self.assertIn('Preserved existing configuration', result.stdout)

    def test_download_failure_preserves_installed_binary(self):
        binary = self.home / '.local/bin/deep-sleep'
        binary.parent.mkdir(parents=True)
        binary.write_text('previous version\n')
        result = self.run_install(TEST_FAIL_CONFIG='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(binary.read_text(), 'previous version\n')
        self.assertFalse((self.home / '.deep-sleep/.env').exists())

    def test_other_platform_is_rejected_before_installation(self):
        result = self.run_install(TEST_OS='Linux')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires macOS', result.stderr)
        self.assertFalse((self.home / '.local').exists())
