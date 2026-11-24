"""Makes the program show up as "Dubzar" (name, description and icon) in the Task Manager instead of "Python".

Windows names a process after its executable file and describes it with the file's version resource. The installer therefore
puts a copy of the Python interpreter next to the others in the virtual environment as ``Dubzar.exe`` (with the DLLs it needs)
and gives that copy its own version resource and icon. It is the real interpreter, not a launcher that starts another
process, so the Task Manager shows one entry. Run by the installer: ``python -m dubzar.branding <venv folder>``.
"""

import ctypes
import shutil
import struct
import sys
from ctypes import wintypes
from pathlib import Path

NAME = "Dubzar"
EXE_NAME = "Dubzar.exe"
RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
LANG_EN_US = 0x0409
ICON_FILE = Path(__file__).with_name("ui") / "dubzar.ico"
DLL_NAMES = ("python3.dll", "vcruntime140.dll", "vcruntime140_1.dll")


def _padded(data: bytes) -> bytes:
    return data + b"\0" * (-len(data) % 4)


def _assemble(head_key: bytes, value: bytes, children: bytes, text: bool) -> bytes:
    """One VS_VERSIONINFO node: length, value length, type, key, 32-bit aligned value, then its children."""
    body = head_key + _padded(value) + children
    length = len(body)
    value_length = len(value) // 2 if text else len(value)
    return struct.pack("<HH", length, value_length) + body[4:]


def version_resource(version: str = "0.2.1", description: str = "Dubzar: oyunlara Türkçe altyazı") -> bytes:
    numbers = ([int(part) for part in version.split(".") if part.isdigit()] + [0, 0, 0, 0])[:4]
    ms, ls = (numbers[0] << 16) | numbers[1], (numbers[2] << 16) | numbers[3]
    fixed = struct.pack("<IIIIIIIIIIIII", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x00040004, 1, 0, 0, 0)
    strings = {"CompanyName": NAME, "FileDescription": NAME, "FileVersion": version, "InternalName": NAME,
               "LegalCopyright": NAME, "OriginalFilename": EXE_NAME, "ProductName": NAME, "ProductVersion": version,
               "Comments": description}
    string_nodes = b"".join(_padded(_assemble(_padded(struct.pack("<HHH", 0, 0, 1) + (k + "\0").encode("utf-16-le")),
                                              (v + "\0").encode("utf-16-le"), b"", True)) for k, v in strings.items())
    table = _assemble(_padded(struct.pack("<HHH", 0, 0, 1) + "040904B0\0".encode("utf-16-le")), b"", string_nodes, False)
    string_info = _assemble(_padded(struct.pack("<HHH", 0, 0, 1) + "StringFileInfo\0".encode("utf-16-le")), b"", _padded(table), False)
    translation = _assemble(_padded(struct.pack("<HHH", 0, 0, 0) + "Translation\0".encode("utf-16-le")),
                            struct.pack("<HH", LANG_EN_US, 1200), b"", False)
    var_info = _assemble(_padded(struct.pack("<HHH", 0, 0, 1) + "VarFileInfo\0".encode("utf-16-le")), b"", _padded(translation), False)
    return _assemble(_padded(struct.pack("<HHH", 0, 0, 0) + "VS_VERSION_INFO\0".encode("utf-16-le")), fixed,
                     _padded(string_info) + var_info, False)


def _icon_resources(ico: bytes) -> tuple[list[tuple[int, bytes]], bytes]:
    """The pictures of an .ico file as (resource id, data) and the group directory that lists them."""
    _, _, count = struct.unpack_from("<HHH", ico, 0)
    pictures, entries = [], b""
    for i in range(count):
        w, h, colours, reserved, planes, bits, size, offset = struct.unpack_from("<BBBBHHII", ico, 6 + 16 * i)
        pictures.append((i + 1, ico[offset:offset + size]))
        entries += struct.pack("<BBBBHHIH", w, h, colours, reserved, planes, bits, size, i + 1)
    return pictures, struct.pack("<HHH", 0, 1, count) + entries


def _update(path: Path, version: str, ico: Path | None) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
    kernel.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    handle = kernel.BeginUpdateResourceW(str(path), False)
    if not handle:
        raise OSError(f"cannot update {path}: error {ctypes.get_last_error()}")

    def put(kind: int, name: int, data: bytes) -> None:
        buffer = ctypes.create_string_buffer(data, len(data))
        if not kernel.UpdateResourceW(handle, kind, name, LANG_EN_US, buffer, len(data)):
            raise OSError(f"cannot write resource {kind}/{name}: error {ctypes.get_last_error()}")

    try:
        put(RT_VERSION, 1, version_resource(version))
        if ico is not None and ico.exists():
            pictures, group = _icon_resources(ico.read_bytes())
            for number, data in pictures:
                put(RT_ICON, number, data)
            put(RT_GROUP_ICON, 1, group)
    except Exception:
        kernel.EndUpdateResourceW(handle, True)      # discard the half-finished update
        raise
    if not kernel.EndUpdateResourceW(handle, False):
        raise OSError(f"cannot save {path}: error {ctypes.get_last_error()}")


def brand_executable(venv: Path, version: str = "0.2.3", ico: Path | None = ICON_FILE) -> Path:
    """Creates ``<venv>/Scripts/Dubzar.exe`` and returns its path. Raises OSError when it cannot."""
    base = Path(sys.base_prefix)
    source = base / "pythonw.exe"
    scripts = Path(venv) / "Scripts"
    if not source.exists() or not scripts.is_dir():
        raise OSError("no interpreter to copy")
    target = scripts / EXE_NAME
    shutil.copy2(source, target)
    for dll in sorted(base.glob("python3*.dll")) + [base / name for name in DLL_NAMES]:
        if dll.exists():
            shutil.copy2(dll, scripts / dll.name)
    _update(target, version, ico)
    return target


def main(argv: list[str]) -> int:
    if not argv:
        print("kullanım: python -m dubzar.branding <venv klasörü>")
        return 2
    try:
        print(brand_executable(Path(argv[0])))
    except OSError as exc:
        print(f"Dubzar.exe oluşturulamadı ({exc}); simge adı 'Python' kalacak.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
