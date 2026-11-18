"""Gerçek APT ile salt-okunur çevrimdışı regresyon testleri.

Gerçek .deb'ler ve yerel, sentetik depo dizini oluşturulur. Paket kurulmaz,
sistem paket veritabanı okunmaz/değiştirilmez ve ağa çıkılmaz. APT'nin hem
komutunda hem izole ayarında simülasyon zorunludur; apt-get update çağrılmaz.
"""
import hashlib
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import load

import offline
helper = load("apt_offline_helper", "system/usr/local/sbin/oguzdows-driver-helper")


@unittest.skipUnless(shutil.which("apt-get") and shutil.which("dpkg-deb"), "Gerçek APT/dpkg-deb gerekli")
class AptOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oguzdows-apt-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ("etc/apt.conf.d", "etc/sources.list.d", "etc/preferences.d", "state/lists/partial", "cache/archives/partial", "log", "repo", "embedded"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / "state/status").touch()
        (self.root / "etc/apt.conf").touch()
        (self.root / "etc/sources.list").write_text("deb [trusted=yes] https://github.com/oguzdows-apt-fixture/ ./\n")
        # trusted=yes yalnızca bu sentetik test dizinine aittir. Bu URL'ye
        # istek yapılmaz: dizin dosyası doğrudan yerleştirilir ve simüle edilir.
        config = self.root / "apt.conf"
        config.write_text(f'''Dir::Etc "{self.root}/etc";
Dir::Etc::main "apt.conf";
Dir::Etc::parts "apt.conf.d";
Dir::Etc::sourcelist "sources.list";
Dir::Etc::sourceparts "sources.list.d";
Dir::State "{self.root}/state";
Dir::State::status "{self.root}/state/status";
Dir::Cache "{self.root}/cache";
Dir::Log "{self.root}/log";
Debug::NoLocking "true";
APT::Sandbox::User "{pwd.getpwuid(os.geteuid()).pw_name}";
APT::Get::Simulate "true";
Acquire::Languages "none";
''')
        self.env = {**os.environ, "APT_CONFIG": str(config), "LC_ALL": "C.UTF-8"}
        self.records = []

    def package(self, name, depends=""):
        source = self.root / ("source-" + name)
        (source / "DEBIAN").mkdir(parents=True)
        fields = f"Package: {name}\nVersion: 1.0\nArchitecture: all\nMaintainer: OğuzDows <noreply@example.invalid>\nDescription: Isolated offline APT test\n"
        if depends:
            fields += "Depends: " + depends + "\n"
        (source / "DEBIAN/control").write_text(fields)
        archive = self.root / "repo" / (name + "_1.0_all.deb")
        subprocess.run(["dpkg-deb", "-Zgzip", "--build", str(source), str(archive)], check=True, capture_output=True, text=True)
        data = archive.read_bytes()
        self.records.append(fields + f"Filename: ./{archive.name}\nSize: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n")
        (self.root / "state/lists/github.com_oguzdows-apt-fixture_._Packages").write_text("\n".join(self.records) + "\n")
        return archive

    def simulate(self, command):
        self.assertIn("--simulate", command, "Test gerçek paket kurmamalıdır")
        self.assertNotIn("update", command, "Test depo indirmemelidir")
        return subprocess.run(command, capture_output=True, text=True, env=self.env, timeout=20)

    def test_repository_duplicate_reproduces_failure_and_explicit_cache_fixes_it(self):
        package = self.package("oguzdows-apt-main")
        embedded = Path(shutil.copy2(package, self.root / "embedded"))
        original = ["/usr/bin/apt-get", "--simulate", "--no-download", "--no-remove", "--no-install-recommends", "install", str(embedded)]
        failed = self.simulate(original)
        self.assertEqual(failed.returncode, 100, failed.stdout + failed.stderr)
        self.assertIn("Unable to fetch some archives", failed.stderr)
        fixed = self.simulate(offline.install_command(embedded, simulate=True))
        self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
        self.assertIn("Inst oguzdows-apt-main", fixed.stdout)
        self.assertEqual((self.root / "state/status").read_bytes(), b"")

    def test_missing_dependency_archive_is_not_silently_downloaded_or_ignored(self):
        self.package("oguzdows-apt-dependency")
        package = self.package("oguzdows-apt-main", "oguzdows-apt-dependency (= 1.0)")
        embedded = Path(shutil.copy2(package, self.root / "embedded"))
        result = self.simulate(offline.install_command(embedded, simulate=True))
        self.assertEqual(result.returncode, 100, result.stdout + result.stderr)
        self.assertIn("Unable to fetch some archives", result.stderr)
        self.assertEqual((self.root / "state/status").read_bytes(), b"")

    def test_complete_cache_supports_the_same_runtime_helper_command(self):
        dependency = self.package("oguzdows-apt-dependency")
        package = self.package("oguzdows-apt-main", "oguzdows-apt-dependency (= 1.0)")
        shutil.copy2(dependency, self.root / "embedded")
        embedded = Path(shutil.copy2(package, self.root / "embedded"))
        # Intel yolu başlık istemez; yalnızca komut oluşturulur, yardımcı çalıştırılmaz.
        runtime = helper.commands("intel-legacy-accept-license", embedded, True)[0]
        result = self.simulate([runtime[0], "--simulate", *runtime[1:]])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Inst oguzdows-apt-dependency", result.stdout)
        self.assertIn("Inst oguzdows-apt-main", result.stdout)
        self.assertEqual((self.root / "state/status").read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
