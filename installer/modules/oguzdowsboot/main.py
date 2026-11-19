"""PC disk açılışı için dar kapsamlı BIOS/UEFI kontrolü; bölüm oluşturmaz/silmez."""
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import libcalamares


class BootError(ValueError):
    pass


def boot_partition(partitions: list[dict]) -> dict:
    for mount in ("/boot", "/"):
        found = [p for p in partitions if p.get("mountPoint") == mount]
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise BootError("Birden fazla önyükleme bölümü var; disk hedefi otomatik seçilmedi.")
    raise BootError("Kurulumun kök / önyükleme bölümü bulunamadı.")


def block_node(device: str) -> Path:
    if not isinstance(device, str) or not device.startswith("/dev/"):
        raise BootError("Geçerli bir disk aygıtı seçilmedi.")
    info = os.stat(device)
    if not stat.S_ISBLK(info.st_mode):
        raise BootError("Önyükleme hedefi gerçek bir blok aygıtı değil.")
    return (Path("/sys/dev/block") / f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}").resolve(strict=True)


def selected_disk(boot_loader: dict | None) -> tuple[Path, Path]:
    device = boot_loader.get("installPath") if isinstance(boot_loader, dict) else None
    if not isinstance(device, str) or not device:
        raise BootError("BIOS için önyükleyici diski seçilmemiş. Bölümleme ekranında hedef diskin MBR'sini seçin; kurulum sessizce önyükleyicisiz tamamlanamaz.")
    node = block_node(device)
    if (node / "partition").exists():
        raise BootError("BIOS önyükleyicisi bir bölüme değil diskin tamamına kurulmalı. Örneğin /dev/sda1 yerine /dev/sda seçin; diskiniz farklıysa adını buna göre kontrol edin.")
    if (node / "slaves").is_dir() and any((node / "slaves").iterdir()):
        raise BootError("Sanal/RAID önyükleme diski otomatik değiştirilmedi; fiziksel önyükleme hedefini kontrol edin.")
    return Path(device), node


def primary_number(partition: dict, disk_node: Path) -> int | None:
    node = block_node(partition.get("device", ""))
    number = node / "partition"
    if node.parent != disk_node or not number.is_file():
        # Başka diskte /boot kullanan kurulumda rastgele bir bölümü işaretleme.
        return None
    return int(number.read_text().strip())


def active_offset(sector: bytes, number: int | None) -> int | None:
    """MSDOS MBR'de yalnızca eksik active baytını seç; GPT/var olan bayrağa dokunma."""
    if len(sector) != 512 or sector[510:512] != b"\x55\xaa":
        raise BootError("Diskin geçerli MBR imzası yok.")
    entries = [sector[446 + 16 * i:462 + 16 * i] for i in range(4)]
    # Koruyucu veya hibrit GPT MBR'ına klasik 'boot' bayrağı yazılmaz.
    if any(entry[4] == 0xEE for entry in entries):
        return None
    if any(entry[0] not in (0, 0x80) for entry in entries):
        raise BootError("MBR bölüm bayrakları geçersiz; güvenlik için değiştirilmedi.")
    active = [entry for entry in entries if entry[0] == 0x80]
    if len(active) > 1 or any(entry[4] == 0 or int.from_bytes(entry[12:16], "little") == 0 for entry in active):
        raise BootError("MBR aktif bölüm seçimi tutarsız; mevcut bayraklar değiştirilmedi.")
    if active:
        return None  # Mevcut işletim sisteminin aktif bölüm tercihini koru.
    if number is None or number < 1:
        raise BootError("Önyükleme bölümü seçilen diskte doğrulanamadı; başka diskin bayrakları değiştirilmedi.")
    if number <= 4:
        index = number - 1
    else:
        # Mantıksal Linux bölümü için MBR'deki genişletilmiş kapsayıcı kullanılır.
        extended = [i for i, entry in enumerate(entries) if entry[4] in (0x05, 0x0F, 0x85)]
        if len(extended) != 1:
            raise BootError("Mantıksal bölümün MBR kapsayıcısı tekil değil; bayrak yazılmadı.")
        index = extended[0]
    entry = entries[index]
    if entry[4] == 0 or int.from_bytes(entry[12:16], "little") == 0:
        raise BootError("Önyükleme bölümü MBR'de boş görünüyor; bayrak yazılmadı.")
    return 446 + index * 16


def mark_active(fd: int, number: int | None, backup_dir: Path) -> bool:
    """Açılmış diskte tek bayt; sektörün geri kalanını ve disk kimliğini aynen koru."""
    before = os.pread(fd, 512, 0)
    offset = active_offset(before, number)
    if offset is None:
        return False
    if not any(before[:440]):
        raise BootError("MBR önyükleme kodu yok; yalnızca bölüm bayrağı yazmak yeterli değil.")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_fd, backup_name = tempfile.mkstemp(prefix="mbr-before-active-", suffix=".bin", dir=backup_dir)
    with os.fdopen(backup_fd, "wb") as backup:
        backup.write(before)
        backup.flush()
        os.fsync(backup.fileno())
    directory_fd = os.open(backup_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    # Bir bölümleme programı veya toplu sektör yazımı kullanma: sadece 0x00 -> 0x80.
    if os.pread(fd, 512, 0) != before:
        raise BootError("MBR eşzamanlı değişti; bayrak yazılmadı.")
    if os.pwrite(fd, b"\x80", offset) != 1:
        raise BootError("MBR aktif bayrağı yazılamadı.")
    os.fsync(fd)
    expected = before[:offset] + b"\x80" + before[offset + 1:]
    if os.pread(fd, 512, 0) != expected:
        raise BootError("MBR yazımı doğrulanamadı; kurulum başarılı sayılmadı.")
    libcalamares.utils.debug("OğuzDows: eksik BIOS aktif bayrağı tamamlandı; önceki MBR: " + backup_name)
    return True


def open_disk(device: Path, write: bool = False) -> int:
    # /dev/disk/by-id gibi meşru bağlantıları çöz; açılan FD'yi tekrar doğrula.
    resolved = device.resolve(strict=True)
    fd = os.open(resolved, (os.O_RDWR if write else os.O_RDONLY) | os.O_NOFOLLOW | os.O_CLOEXEC)
    if not stat.S_ISBLK(os.fstat(fd).st_mode):
        os.close(fd)
        raise BootError("Önyükleme hedefi blok aygıtı olmaktan çıktı; işlem yapılmadı.")
    return fd


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise BootError("Eksik/boş önyükleme dosyası: " + str(path))


def is_partition_mounted(device: str, mount: Path) -> bool:
    # Sadece bir bağlama noktası olması yetmez; seçilen bölüm bağlı olmalı.
    return os.path.ismount(mount) and mount.stat().st_dev == os.stat(device).st_rdev


def require_esp_type(device: str) -> None:
    # KPMcore'un parttype önbelleği ESP bayrağı değişmeden önceki tür olabilir.
    # -p, blkid önbelleği yerine diskteki güncel bölüm tablosunu salt-okunur yoklar.
    try:
        kind = subprocess.check_output(
            ["blkid", "-p", "-s", "PART_ENTRY_TYPE", "-o", "value", "--", device],
            text=True, stderr=subprocess.PIPE, timeout=10).strip().lower().strip("{}")
    except (OSError, subprocess.SubprocessError) as error:
        raise BootError("EFI bölümünün diskteki türü okunamadı: " + device) from error
    if kind not in ("c12a7328-f81f-11d2-ba4b-00a0c93ec93b", "ef", "0xef", "239"):
        raise BootError("EFI bölümü ESP türünde değil; başka bir bölümün türü otomatik değiştirilmedi.")


def efi_partition(root: Path, partitions: list[dict], mount: str) -> Path:
    if mount != "/boot/efi":
        raise BootError("Beklenmeyen EFI bağlama yolu; disk hedefi değiştirilmedi.")
    matches = [p for p in partitions if p.get("mountPoint") == mount]
    if len(matches) != 1 or matches[0].get("fs", "").lower() not in ("fat32", "fat16", "vfat"):
        raise BootError("UEFI için FAT EFI sistem bölümü seçilmemiş; kurulum önyükleyicisiz tamamlanamaz.")
    device = matches[0].get("device", "")
    block_node(device)
    esp = root / mount.lstrip("/")
    if not is_partition_mounted(device, esp):
        raise BootError("Seçilen EFI bölümü hedef sisteme bağlı değil; dosyalar yanlışlıkla başka bölüme yazılmadı.")
    require_esp_type(device)
    return esp


def check(root: Path, firmware: str, partitions: list[dict], boot_loader: dict | None,
          phase: str, efi_mount: str = "/boot/efi") -> None:
    if phase not in ("prepare", "verify") or firmware not in ("bios", "efi"):
        raise BootError("Önyükleme kipi veya denetim aşaması belirsiz.")
    if not root.is_absolute() or root.resolve() == Path("/") or not root.is_dir():
        raise BootError("Güvenli kurulum hedefi bulunamadı; çalışan sistem değiştirilmedi.")
    if firmware == "bios":
        device, node = selected_disk(boot_loader)
        number = primary_number(boot_partition(partitions), node)
        fd = open_disk(device)
        try:
            sector = os.pread(fd, 512, 0)
            offset = active_offset(sector, number)
        finally:
            os.close(fd)
        if phase == "verify":
            require_file(root / "boot/grub/i386-pc/core.img")
            if not any(sector[:440]):
                raise BootError("BIOS MBR önyükleme kodu kurulmamış.")
    else:
        esp = efi_partition(root, partitions, efi_mount)
        if phase == "verify":
            # FAT üzerinde harf büyüklüğü duyarsızdır; ASCII aygıt yolu eski UEFI'ler içindir.
            for relative in ("EFI/OguzDows/grubx64.efi", "EFI/BOOT/BOOTX64.EFI"):
                path = esp / relative
                require_file(path)
                with path.open("rb") as stream:
                    if stream.read(2) != b"MZ":
                        raise BootError("EFI yükleyici geçerli PE dosyası değil: " + str(path))
    if phase == "verify":
        # 'Dosyalar kopyalandı' yeterli değildir: diskte gerçek GRUB menüsü de olmalı.
        grub_cfg = root / "boot/grub/grub.cfg"
        require_file(grub_cfg)
        menu = grub_cfg.read_text(errors="replace")
        if "menuentry " not in menu or not any(line.lstrip().startswith(("linux ", "linux\t", "linuxefi ")) for line in menu.splitlines()):
            raise BootError("Kurulu sistemin çekirdek menüsü oluşturulmamış.")
        if firmware == "bios" and offset is not None:
            fd = open_disk(device, write=True)
            try:
                mark_active(fd, number, root / "var/log/oguzdows")
            finally:
                os.close(fd)


def pretty_name():
    return "OğuzDows disk önyüklemesi denetleniyor"


def run():
    gs = libcalamares.globalstorage
    try:
        check(Path(gs.value("rootMountPoint") or ""), gs.value("firmwareType"),
              gs.value("partitions") or [], gs.value("bootLoader"),
              libcalamares.job.configuration.get("phase", "verify"),
              gs.value("efiSystemPartition") or "/boot/efi")
    except (OSError, ValueError, TypeError) as error:
        return ("Disk önyüklemesi tamamlanamadı", str(error))
    return None
