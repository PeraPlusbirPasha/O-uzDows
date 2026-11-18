import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import load

import offline
helper = load("offline_driver_helper", "system/usr/local/sbin/oguzdows-driver-helper")
prepare = load("prepare_install", "system/usr/lib/oguzdows/prepare-install.py")
cache = load("cache_drivers", "system/usr/lib/oguzdows/cache-drivers.py")


class OfflineDriverTests(unittest.TestCase):
    def make_payload(self, directory, action="broadcom"):
        package = offline.PACKAGES[action]
        archive = directory / (package + "_1_all.deb")
        archive.write_bytes(b"test package fixture, not an executable archive")
        manifest = {"format": 1, "packages": {package: {"filename": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}}}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return archive, manifest

    def test_payload_requires_known_action_and_matching_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, _ = self.make_payload(root)
            self.assertEqual(offline.payload("broadcom", root), archive)
            self.assertIsNone(offline.payload("arbitrary", root))
            archive.write_bytes(b"modified")
            self.assertIsNone(offline.payload("broadcom", root))

    def test_payload_rejects_path_traversal_symlinks_and_invalid_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, manifest = self.make_payload(root)
            archive.rename(root / "real.deb")
            archive.symlink_to(root / "real.deb")
            self.assertIsNone(offline.payload("broadcom", root))
            for filename in ("../escape.deb", "/tmp/escape.deb", "not-a-package.txt", []):
                manifest["packages"]["broadcom-sta-dkms"]["filename"] = filename
                (root / "manifest.json").write_text(json.dumps(manifest))
                self.assertIsNone(offline.payload("broadcom", root))
            (root / "manifest.json").write_text("{broken")
            self.assertIsNone(offline.payload("broadcom", root))

    def test_exact_kernel_headers_and_explicit_selection_persist(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertFalse(offline.headers_available("kernel-a", root))
            headers = root / "kernel-a/build"
            headers.mkdir(parents=True)
            (headers / "Makefile").touch()
            self.assertTrue(offline.headers_available("kernel-a", root))
            self.assertFalse(offline.headers_available("kernel-b", root))
            choices = root / "run/choices.json"
            offline.remember("broadcom", choices)
            offline.remember("broadcom", choices)
            self.assertEqual(offline.selected(choices), ["broadcom"])
            self.assertEqual(choices.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                offline.remember("execute-arbitrary-command", choices)
            choices.write_text('["broadcom", "unsafe"]')
            self.assertEqual(offline.selected(choices), [])

    def test_offline_install_has_no_network_or_package_removal(self):
        archive = Path("/usr/share/oguzdows/offline-drivers/broadcom-sta-dkms_1_all.deb")
        with patch.object(helper, "headers_available", return_value=True):
            commands = helper.commands("broadcom", archive, True)
        self.assertEqual(len(commands), 1)
        self.assertIn("--no-download", commands[0])
        self.assertIn("--no-remove", commands[0])
        self.assertNotIn("update", commands[0])
        self.assertEqual(commands[0][-1], str(archive))
        self.assertIn("Dir::Cache::archives=" + str(archive.parent), commands[0])
        self.assertEqual(offline.install_command(archive, simulate=True), [argument if argument != "-y" else "--simulate" for argument in commands[0]])
        with self.assertRaises(ValueError):
            offline.install_command(Path("relative/package.deb"))
        with self.assertRaises(RuntimeError):
            helper.commands("intel-legacy-accept-license", None, True)
        with patch.object(helper, "headers_available", return_value=False), self.assertRaises(RuntimeError):
            helper.commands("broadcom", archive, True)

    def test_intel_requires_matching_hardware_and_explicit_license_action(self):
        with patch.object(helper.sys, "argv", ["helper", "intel-legacy"]), patch.object(helper.subprocess, "run") as run, patch("sys.stderr", io.StringIO()):
            self.assertEqual(helper.main(), 2)
            run.assert_not_called()
        with patch.object(helper.sys, "argv", ["helper", "intel-legacy-accept-license", "--offline"]), patch.object(helper.os, "geteuid", return_value=0), patch.object(helper, "supported_intel_legacy", return_value=[]), patch.object(helper.subprocess, "run") as run, patch("sys.stderr", io.StringIO()):
            self.assertEqual(helper.main(), 1)
            run.assert_not_called()

    def test_live_activation_never_unloads_other_device_drivers(self):
        with patch.object(helper.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertTrue(helper.activate("broadcom", io.StringIO()))
            self.assertEqual(run.call_args.args[0], ["/usr/sbin/modprobe", "wl"])
            self.assertNotIn("-r", run.call_args.args[0])

    def test_prepare_installer_finds_live_media_and_only_copies_approved_choices(self):
        import yaml
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "etc/calamares"
            (config / "modules").mkdir(parents=True)
            (config / "settings.conf").write_text("branding: oguzdows\n")
            medium = root / "live-medium"
            (medium / "live").mkdir(parents=True)
            (medium / "live/filesystem.squashfs").touch()
            prepare.prepare(config, (root / "absent", medium), ["broadcom", "unsafe-shell; rm", "intel-legacy-accept-license"])
            unpack = yaml.safe_load((config / "modules/unpackfs.conf").read_text())
            self.assertEqual(unpack["unpack"][0]["source"], str(medium / "live/filesystem.squashfs"))
            drivers = yaml.safe_load((config / "modules/selected-drivers.conf").read_text())
            self.assertEqual(drivers["script"], list(prepare.COMMANDS.values()))
            self.assertFalse(drivers["dontChroot"])
            prepare.prepare(config, (medium,), [])
            self.assertEqual(yaml.safe_load((config / "modules/selected-drivers.conf").read_text())["script"], [])
            with self.assertRaises(FileNotFoundError):
                prepare.source((root / "absent",))

    def test_intel_offline_install_preseeds_only_the_explicitly_accepted_license(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            logs = root / "logs"
            real_open = helper.os.open
            def local_open(path, flags, mode=0o777):
                if str(path) == "/run/lock/oguzdows-drivers.lock":
                    path = root / "lock"
                self.assertTrue(Path(path).is_relative_to(root))
                return real_open(path, flags, mode)
            with patch.object(helper.sys, "argv", ["helper", "intel-legacy-accept-license", "--offline"]), \
                 patch.object(helper.os, "geteuid", return_value=0), \
                 patch.object(helper, "supported_intel_legacy", return_value=["8086:4220"]), \
                 patch.object(helper, "payload", return_value=Path("/trusted/firmware-ipw2x00.deb")), \
                 patch.object(helper, "is_live", return_value=False), \
                 patch.object(helper, "Path", return_value=logs), \
                 patch.object(helper.os, "open", side_effect=local_open), \
                 patch.object(helper.subprocess, "run") as run, patch("sys.stdout", io.StringIO()):
                self.assertEqual(helper.main(), 0)
                self.assertEqual(run.call_count, 3)
                self.assertEqual(run.call_args_list[0].args[0], ["/usr/bin/debconf-set-selections"])
                self.assertIn("accepted boolean true", run.call_args_list[0].kwargs["input"])
                self.assertIn("--no-download", run.call_args_list[1].args[0])

    def test_cache_preserves_licenses_and_hashes_without_installing_or_accepting_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            modules = root / "modules"
            (modules / "kernel/build").mkdir(parents=True)
            (modules / "kernel/build/Makefile").touch()
            (modules / "kernel/modules.dep").touch()
            directory = root / "cache"
            current = []
            def run(command, **kwargs):
                if command[0].endswith("apt-get") and "download" in command:
                    package = command[-1]
                    (Path(kwargs["cwd"]) / (package + "_1_all.deb")).write_bytes(package.encode())
                elif command[0].endswith("dpkg-deb") and "-f" in command:
                    current[:] = [Path(command[2]).name.split("_")[0]]
                    return subprocess.CompletedProcess(command, 0, f"Package: {current[0]}\nVersion: 1\n", "")
                elif command[0].endswith("dpkg-deb") and "-x" in command:
                    license_file = Path(command[-1]) / "usr/share/doc" / current[0] / "copyright"
                    license_file.parent.mkdir(parents=True)
                    license_file.write_text("Original license: explicit acceptance required")
                return subprocess.CompletedProcess(command, 0, "", "")
            with patch.object(cache.subprocess, "run", side_effect=run) as invoked, patch("sys.stdout", io.StringIO()):
                cache.cache(directory, modules)
            for action in offline.PACKAGES:
                self.assertIsNotNone(offline.payload(action, directory))
                self.assertIn("Original license", offline.license_text(action, directory))
            commands = [call.args[0] for call in invoked.call_args_list]
            self.assertFalse(any("debconf-set-selections" in " ".join(command) for command in commands))
            self.assertTrue(all("--simulate" in command for command in commands if command[0].endswith("apt-get") and "install" in command))

    def test_cache_refuses_missing_matching_headers_before_network_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            modules = root / "modules"
            (modules / "kernel").mkdir(parents=True)
            (modules / "kernel/modules.dep").touch()
            with patch.object(cache.subprocess, "run") as run, self.assertRaises(RuntimeError):
                cache.cache(root / "cache", modules)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
