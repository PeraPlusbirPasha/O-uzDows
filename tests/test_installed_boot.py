"""Kurulum sonrası No bootable device regresyonu; yalnızca geçici dosyalara yazar."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from support import ROOT, load

fake_calamares = SimpleNamespace(utils=SimpleNamespace(debug=lambda *_: None))
with patch.dict("sys.modules", {"libcalamares": fake_calamares}):
    boot = load("oguzdows_installed_boot", "installer/modules/oguzdowsboot/main.py")
config = load("oguzdows_installed_config", "scripts/configure.py")


def sector(entries=((0x83, 0),)):
    data = bytearray(512)
    data[:4] = b"GRUB"
    data[440:446] = b"DISKID"
    for i, (kind, flag) in enumerate(entries):
        start = 446 + i * 16
        data[start] = flag
        data[start + 4] = kind
        data[start + 8:start + 12] = (2048 + i * 65536).to_bytes(4, "little")
        data[start + 12:start + 16] = (65536).to_bytes(4, "little")
    data[510:] = b"\x55\xaa"
    return bytes(data)


def put(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, (bytes, bytearray)) else data.encode())
    return path


class LegacyMbrTests(unittest.TestCase):
    def test_regression_inactive_mbr_is_fixed_by_exactly_one_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sector() + b"filesystem payload must not change" * 1000
            disk = put(root, "private-disk.img", before)
            with disk.open("r+b") as stream:
                self.assertTrue(boot.mark_active(stream.fileno(), 1, root / "backup"))
            after = disk.read_bytes()
            self.assertEqual([i for i, (a, b) in enumerate(zip(before, after)) if a != b], [446])
            self.assertEqual(after[446], 0x80)
            self.assertEqual(after[440:446], b"DISKID")
            backups = list((root / "backup").glob("*.bin"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), before[:512])
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
            with disk.open("r+b") as stream:
                self.assertFalse(boot.mark_active(stream.fileno(), 1, root / "backup"))
            self.assertEqual(len(list((root / "backup").glob("*.bin"))), 1)

    def test_existing_active_partition_is_preserved_even_on_another_os(self):
        before = sector(((0x07, 0x80), (0x83, 0)))
        self.assertIsNone(boot.active_offset(before, 2))
        self.assertIsNone(boot.active_offset(before, None))

    def test_correct_primary_and_extended_slot_not_first_disk_or_name_suffix(self):
        self.assertEqual(boot.active_offset(sector(((0x07, 0), (0x83, 0))), 2), 462)
        self.assertEqual(boot.active_offset(sector(((0x07, 0), (0x0F, 0))), 5), 462)
        with self.assertRaises(boot.BootError):
            boot.active_offset(sector(), 5)
        with self.assertRaises(boot.BootError):
            boot.active_offset(sector(((0x05, 0), (0x0F, 0))), 7)

    def test_gpt_and_hybrid_mbr_are_never_edited(self):
        for entries in (((0xEE, 0),), ((0x83, 0), (0xEE, 0))):
            before = sector(entries)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                disk = put(root, "disk", before)
                with disk.open("r+b") as stream:
                    self.assertFalse(boot.mark_active(stream.fileno(), 1, root / "backup"))
                self.assertEqual(disk.read_bytes(), before)
                self.assertFalse((root / "backup").exists())

    def test_invalid_or_ambiguous_mbr_fails_without_any_write(self):
        bad_signature = bytearray(sector())
        bad_signature[510:] = b"xx"
        empty_active = bytearray(sector(((0x83, 0x80),)))
        empty_active[458:462] = bytes(4)
        for value, number in ((b"", 1), (bytes(bad_signature), 1), (sector(((0x83, 0x81),)), 1),
                              (sector(((0x83, 0x80), (0x07, 0x80))), 1), (bytes(empty_active), 1),
                              (sector(((0, 0x80),)), 1), (sector(), None), (sector(), 2), (sector(), 0)):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                disk = put(root, "disk", value)
                with disk.open("r+b") as stream, self.assertRaises(boot.BootError):
                    boot.mark_active(stream.fileno(), number, root / "backup")
                self.assertEqual(disk.read_bytes(), value)
                self.assertFalse((root / "backup").exists())

    def test_a_boot_flag_is_not_substituted_for_missing_grub_mbr_code(self):
        value = bytearray(sector())
        value[:440] = bytes(440)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = put(root, "disk", value)
            with disk.open("r+b") as stream, self.assertRaisesRegex(boot.BootError, "önyükleme kodu"):
                boot.mark_active(stream.fileno(), 1, root / "backup")
            self.assertEqual(disk.read_bytes(), value)

    def test_partition_number_comes_from_sysfs_and_separate_boot_is_preferred(self):
        parts = [{"mountPoint": "/", "device": "/dev/mapper/root"}, {"mountPoint": "/boot", "device": "/dev/disk/by-uuid/test"}]
        self.assertEqual(boot.boot_partition(parts), parts[1])
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory) / "nvme0n1"
            put(disk, "nvme0n1p3/partition", "3\n")
            with patch.object(boot, "block_node", return_value=disk / "nvme0n1p3"):
                self.assertEqual(boot.primary_number(parts[1], disk), 3)
                self.assertIsNone(boot.primary_number(parts[1], Path(directory) / "another-disk"))

    def test_bootloader_must_be_a_whole_disk_and_must_not_be_missing(self):
        with self.assertRaisesRegex(boot.BootError, "seçilmemiş"):
            boot.selected_disk(None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root, "partition", "1")
            with patch.object(boot, "block_node", return_value=root), self.assertRaisesRegex(boot.BootError, "diskin tamamına"):
                boot.selected_disk({"installPath": "/dev/example1"})
        with self.assertRaises(boot.BootError):
            boot.block_node("not-a-device")
        with tempfile.NamedTemporaryFile() as regular:
            with self.assertRaises(boot.BootError):
                boot.block_node(regular.name)
            with self.assertRaises(boot.BootError):
                boot.open_disk(Path(regular.name), write=True)


class InstalledBootIntegrationTests(unittest.TestCase):
    def bios_fixture(self, directory):
        root = Path(directory) / "target"
        put(root, "boot/grub/i386-pc/core.img", b"installed-core")
        put(root, "boot/grub/grub.cfg", "menuentry 'OğuzDows' {\n linux /boot/vmlinuz root=UUID=test\n initrd /boot/initrd.img\n}\n")
        disk = put(Path(directory), "disk.img", sector())
        return root, disk

    def test_prepare_is_read_only_and_verify_runs_after_grub_before_umount(self):
        with tempfile.TemporaryDirectory() as directory:
            root, disk = self.bios_fixture(directory)
            with patch.object(boot, "selected_disk", return_value=(disk, Path("/sys/fake"))), patch.object(boot, "primary_number", return_value=1), patch.object(boot, "open_disk", side_effect=lambda path, write=False: os.open(path, os.O_RDWR if write else os.O_RDONLY)) as opened:
                parts = [{"mountPoint": "/", "device": "/dev/test1"}]
                boot.check(root, "bios", parts, {"installPath": "/dev/test"}, "prepare")
                self.assertEqual(disk.read_bytes()[446], 0)
                self.assertFalse((root / "var/log/oguzdows").exists())
                self.assertFalse(any(call.kwargs.get("write") for call in opened.call_args_list))
                boot.check(root, "bios", parts, {"installPath": "/dev/test"}, "verify")
                self.assertEqual(disk.read_bytes()[446], 0x80)

    def test_missing_grub_or_kernel_menu_cannot_report_install_success_or_mark_active(self):
        for relative in ("boot/grub/i386-pc/core.img", "boot/grub/grub.cfg"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root, disk = self.bios_fixture(directory)
                (root / relative).write_bytes(b"")
                with patch.object(boot, "selected_disk", return_value=(disk, Path("/sys/fake"))), patch.object(boot, "primary_number", return_value=1), patch.object(boot, "open_disk", side_effect=lambda path, write=False: os.open(path, os.O_RDONLY)):
                    with self.assertRaises(boot.BootError):
                        boot.check(root, "bios", [{"mountPoint": "/", "device": "/dev/test1"}], {"installPath": "/dev/test"}, "verify")
                self.assertEqual(disk.read_bytes()[446], 0)

    def test_uefi_requires_a_real_mounted_fat_esp_and_both_efi_loaders(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.bios_fixture(directory)
            esp = root / "boot/efi"
            put(esp, "EFI/OguzDows/grubx64.efi", b"MZ-vendor-efi-fixture")
            fallback = put(esp, "EFI/BOOT/BOOTX64.EFI", b"MZ-fallback-efi-fixture")
            parts = [{"mountPoint": "/", "device": "/dev/test2", "fs": "ext4"}, {"mountPoint": "/boot/efi", "device": "/dev/test1", "fs": "fat32"}]
            with patch.object(boot, "block_node"), patch.object(boot, "is_partition_mounted", return_value=True), patch.object(boot, "open_disk") as opened:
                boot.check(root, "efi", parts, None, "prepare")
                boot.check(root, "efi", parts, None, "verify")
                opened.assert_not_called()  # UEFI yolunda MBR/aktif bayrak yazılmaz.
                fallback.unlink()
                with self.assertRaisesRegex(boot.BootError, "BOOTX64"):
                    boot.check(root, "efi", parts, None, "verify")
                parts[1]["parttype"] = "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"  # veri, ESP değil
                with self.assertRaisesRegex(boot.BootError, "ESP türünde değil"):
                    boot.check(root, "efi", parts, None, "prepare")
                parts[1]["parttype"] = "{C12A7328-F81F-11D2-BA4B-00A0C93EC93B}"
                boot.check(root, "efi", parts, None, "prepare")
            with patch.object(boot, "block_node"), patch.object(boot.os.path, "ismount", return_value=False):
                with self.assertRaisesRegex(boot.BootError, "bağlı değil"):
                    boot.check(root, "efi", parts, None, "prepare")
            with self.assertRaises(boot.BootError):
                boot.check(root, "efi", parts[:1], None, "prepare")

    def test_another_mounted_device_does_not_count_as_the_selected_esp(self):
        for mounted, selected, expected in ((8, 8, True), (8, 9, False)):
            with patch.object(boot.os.path, "ismount", return_value=True), patch.object(boot.os, "stat", side_effect=[SimpleNamespace(st_dev=mounted), SimpleNamespace(st_rdev=selected)]):
                self.assertEqual(boot.is_partition_mounted("/dev/test1", Path("/target/boot/efi")), expected)
        with patch.object(boot.os.path, "ismount", return_value=False), patch.object(boot.os, "stat") as info:
            self.assertFalse(boot.is_partition_mounted("/dev/test1", Path("/target/boot/efi")))
            info.assert_not_called()

    def test_a_menu_without_a_kernel_is_rejected_before_any_mbr_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root, disk = self.bios_fixture(directory)
            put(root, "boot/grub/grub.cfg", "menuentry 'not a kernel' {\n echo no OS\n}\n")
            with patch.object(boot, "selected_disk", return_value=(disk, Path("/sys/fake"))), patch.object(boot, "primary_number", return_value=1), patch.object(boot, "open_disk", side_effect=lambda path, write=False: os.open(path, os.O_RDONLY)):
                with self.assertRaisesRegex(boot.BootError, "çekirdek menüsü"):
                    boot.check(root, "bios", [{"mountPoint": "/", "device": "/dev/test1"}], {"installPath": "/dev/test"}, "verify")
            self.assertEqual(disk.read_bytes()[446], 0)
            self.assertFalse((root / "var/log/oguzdows").exists())

    def test_installer_returns_visible_failure_for_missing_boot_target(self):
        with tempfile.TemporaryDirectory() as directory:
            gs = {"rootMountPoint": directory, "firmwareType": "bios", "partitions": [{"mountPoint": "/", "device": "/dev/test1"}]}
            with patch.object(boot.libcalamares, "globalstorage", SimpleNamespace(value=gs.get), create=True), patch.object(boot.libcalamares, "job", SimpleNamespace(configuration={"phase": "prepare"}), create=True):
                result = boot.run()
                self.assertIsInstance(result, tuple)
                self.assertIn("seçilmemiş", result[1])

    def test_live_root_unknown_firmware_and_unknown_phase_are_rejected(self):
        for root, mode, phase in ((Path("/"), "bios", "verify"), (Path("."), "efi", "verify"), (Path("/tmp"), "unknown", "verify"), (Path("/tmp"), "bios", "arbitrary")):
            with self.assertRaises(boot.BootError):
                boot.check(root, mode, [], None, phase)

    def test_pc_ci_gates_iso_on_disposable_real_grub_checks(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/main.yml").read_text())
        self.assertEqual(workflow["jobs"]["build"]["needs"], ["verify", "installed-boot"])
        job = workflow["jobs"]["installed-boot"]
        self.assertEqual(job["strategy"]["matrix"]["suite"], ["bookworm", "trixie"])
        self.assertIn("target != 'raspberrypi'", job["if"])
        self.assertIn("tests/smoke-installed-boot.py", str(job["steps"]))
        self.assertFalse(workflow["concurrency"]["cancel-in-progress"])
        self.assertIn("inputs.target", workflow["concurrency"]["group"])

    def test_staged_module_and_sequence_preserve_existing_desktop_and_install_steps(self):
        settings = yaml.safe_load((ROOT / "installer/settings.conf").read_text())
        self.assertEqual(settings["modules-search"], ["/etc/calamares/modules", "local"])
        sequence = settings["sequence"][1]["exec"]
        self.assertEqual(sequence[sequence.index("initramfs") + 1:sequence.index("umount")], ["oguzdowsboot@boot-prepare", "bootloader", "oguzdowsboot@boot-verify"])
        self.assertEqual(settings["sequence"][0]["show"], ["welcome", "locale", "keyboard", "partition", "users", "summary"])
        loader = yaml.safe_load((ROOT / "installer/modules/bootloader.conf").read_text())
        self.assertEqual(loader["efiBootloaderId"], "OguzDows")
        self.assertTrue(loader["efiBootloaderId"].isascii())
        self.assertTrue(loader["installEFIFallback"])
        branding = yaml.safe_load((ROOT / "installer/branding/branding.desc").read_text())
        self.assertEqual(branding["strings"]["bootloaderEntryName"], "OğuzDows")
        for arch in ("amd64", "i386"):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                config.configure(arch, output)
                overlay = output / "includes.chroot"
                self.assertTrue((overlay / "etc/calamares/modules/oguzdowsboot/main.py").is_file())
                self.assertFalse(list(overlay.rglob("__pycache__")))
                self.assertEqual(json.loads((overlay / "usr/share/oguzdows/build-info.json").read_text())["arch"], arch)


if __name__ == "__main__":
    unittest.main()
