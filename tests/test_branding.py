import struct

from dubzar.branding import _icon_resources, version_resource


def test_the_version_resource_names_the_program_dubzar():
    data = version_resource("1.2.3")
    text = data.decode("utf-16-le", errors="ignore")
    for field in ("FileDescription", "ProductName", "OriginalFilename", "Dubzar.exe", "VS_VERSION_INFO"):
        assert field in text
    assert struct.unpack_from("<H", data, 0)[0] == len(data)      # the outer block covers the whole resource


def test_an_ico_file_is_split_into_resource_pictures_and_a_group():
    picture = b"\x89PNG-data"
    ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 16, 16, 0, 0, 1, 32, len(picture), 22) + picture
    pictures, group = _icon_resources(ico)
    assert pictures == [(1, picture)]
    assert struct.unpack_from("<HHH", group, 0) == (0, 1, 1)
