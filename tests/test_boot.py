import tempfile
import unittest
from pathlib import Path

from support import load

boot = load("oguzdows_boot", "scripts/configure-boot.py")
config = load("oguzdows_boot_config", "scripts/configure.py")
verifier = load("oguzdows_verify", "scripts/verify-iso.py")


class BootTests(unittest.TestCase):
    def fixture(self, base: Path, arch: str, alias=False):
        binary, root = base / "binary", base / "chroot"
        (binary / "live").mkdir(parents=True)
        version = "6.12.0-1-amd64" if arch == "amd64" else "6.1.0-1-686-pae"
        suffix = "" if alias else "-" + version
        (binary / f"live/vmlinuz{suffix}").touch()
        (binary / f"live/initrd.img{suffix}").touch()
        (binary / "isolinux").mkdir()
        (binary / "isolinux/vesamenu.c32").touch()
        (binary / "isolinux/live.cfg").write_text("default upstream menu")
        (binary / "boot/grub/live-theme").mkdir(parents=True)
        (binary / "boot/grub/live-theme/theme.txt").write_text("upstream theme")
        (binary / "boot/grub/grub.cfg").write_text("default upstream menu")
        (binary / "README.diskdefines").touch()
        (binary / "README.html").touch()
        brand = root / "usr/share/oguzdows/brand"
        brand.mkdir(parents=True)
        (brand / "boot-bios.png").write_bytes(b"bios-png-fixture")
        (brand / "boot-efi.png").write_bytes(b"efi-png-fixture")
        (root / "usr/share/grub").mkdir()
        (root / "usr/share/grub/unicode.pf2").touch()
        return binary, root

    def test_iso_menus_and_verifier_on_both_architectures(self):
        for arch in ("amd64", "i386"):
            for alias in (True, False):
                with self.subTest(arch=arch, alias=alias), tempfile.TemporaryDirectory() as directory:
                    binary, root = self.fixture(Path(directory), arch, alias)
                    boot.configure(binary, root, {"arch": arch, "boot_args": config.BOOT_ARGS, **config.ARCHITECTURES[arch]})
                    paths = verifier.validate_tree(binary, arch)
                    self.assertTrue(all((binary / p.lstrip("/")).is_file() for p in paths))
                    self.assertFalse((binary / "isolinux/live.cfg").exists())
                    self.assertFalse((binary / "boot/grub/live-theme").exists())
                    self.assertEqual((binary / "boot/grub/grub.cfg").exists(), arch == "amd64")
                    bios = (binary / "isolinux/isolinux.cfg").read_text(encoding="ascii")
                    self.assertEqual(bios.count("  APPEND boot=live "), 4)
                    self.assertNotIn("acpi=off", bios)
                    self.assertNotIn("noapic", bios)
                    self.assertNotIn("toram", bios)

    def test_each_entry_is_oguzdows_related(self):
        for entry in boot.entries(config.BOOT_ARGS):
            self.assertTrue(entry.title.startswith("OğuzDows"))
            self.assertTrue(entry.bios_title.startswith("OguzDows"))
            self.assertIn("locales=tr_TR.UTF-8", entry.arguments)
            self.assertIn("boot=live", entry.arguments)
        verbose = boot.entries(config.BOOT_ARGS)[3].arguments.split()
        self.assertNotIn("quiet", verbose)
        self.assertNotIn("splash", verbose)
        self.assertIn("loglevel=6", verbose)
        safe = boot.entries(config.BOOT_ARGS)[1].arguments.split()
        self.assertIn("nomodeset", safe)
        self.assertIn("plymouth.enable=0", safe)

    def test_missing_or_ambiguous_kernels_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory)
            (binary / "live").mkdir()
            with self.assertRaises(RuntimeError):
                boot.kernel_pair(binary)
            for version in ("one", "two"):
                (binary / f"live/vmlinuz-{version}").touch()
                (binary / f"live/initrd.img-{version}").touch()
            with self.assertRaises(RuntimeError):
                boot.kernel_pair(binary)

    def test_missing_menu_module_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            binary, root = self.fixture(Path(directory), "amd64")
            (binary / "isolinux/vesamenu.c32").unlink()
            with self.assertRaises(RuntimeError):
                boot.configure(binary, root, {"arch": "amd64", "boot_args": config.BOOT_ARGS, "uefi": True})

    def test_verifier_rejects_unbranded_leftover(self):
        with tempfile.TemporaryDirectory() as directory:
            binary, root = self.fixture(Path(directory), "amd64")
            boot.configure(binary, root, {"arch": "amd64", "boot_args": config.BOOT_ARGS, "uefi": True})
            (binary / "isolinux/unused.cfg").write_text("Debian GNU/Linux")
            with self.assertRaises(ValueError):
                verifier.validate_tree(binary, "amd64")


if __name__ == "__main__":
    unittest.main()
