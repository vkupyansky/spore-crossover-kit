"""Synthetic DBPF fixtures contain no game or mod data."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import struct
import tempfile
import unittest

from tools import check_packages


KEY = (0x11223344, 0x55667788, 0x99AABBCC)


def package_bytes(entries: list[tuple[tuple[int, int, int], bytes]], flags: int = 4) -> bytes:
    header = bytearray(96)
    header[:4] = b"DBPF"
    struct.pack_into("<II", header, 4, 3, 0)
    struct.pack_into("<I", header, 60, 3)
    payload = bytearray()
    index = bytearray(struct.pack("<I", flags))
    if flags & 1:
        index += struct.pack("<I", KEY[2])
    if flags & 2:
        index += struct.pack("<I", KEY[0])
    if flags & 4:
        index += struct.pack("<I", 0)
    for (group, instance, kind), data in entries:
        if not flags & 1:
            index += struct.pack("<I", kind)
        if not flags & 2:
            index += struct.pack("<I", group)
        index += struct.pack(
            "<IIIIHBB", instance, 96 + len(payload), len(data) | 0x80000000,
            len(data), 0, 1, 0,
        )
        payload += data
    struct.pack_into("<I", header, 36, len(entries))
    struct.pack_into("<I", header, 44, len(index))
    struct.pack_into("<I", header, 64, 96 + len(payload))
    return bytes(header + payload + index)


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write(self, data: bytes, name: str = "test.package") -> Path:
        path = self.directory / name
        path.write_bytes(data)
        return path

    def test_shared_type_and_group_and_zero_id_are_not_missing(self) -> None:
        data = bytearray(package_bytes([(KEY, b"resource")], flags=7))
        index = struct.unpack_from("<I", data, 64)[0]
        struct.pack_into("<II", data, index + 4, 0, 0)
        package = check_packages.read_package(self.write(data))
        self.assertIn((0, KEY[1], 0), package.resources)

    def test_truncated_header_and_bad_magic(self) -> None:
        for data, message in [(b"DBPF", "truncated"), (b"XXXX" + bytes(92), "magic")]:
            with self.subTest(message=message):
                with self.assertRaisesRegex(check_packages.PackageError, message):
                    check_packages.read_package(self.write(data))

    def test_truncated_and_inconsistent_index(self) -> None:
        valid = package_bytes([(KEY, b"resource")])
        count_mismatch = bytearray(valid)
        struct.pack_into("<I", count_mismatch, 36, 1000000)
        for data, message in [(valid[:-1], "beyond"), (count_mismatch, "count")]:
            with self.subTest(message=message):
                with self.assertRaisesRegex(check_packages.PackageError, message):
                    check_packages.read_package(self.write(data))

    def test_bad_payload_range_compression_and_size(self) -> None:
        valid = package_bytes([(KEY, b"resource")])
        index = struct.unpack_from("<I", valid, 64)[0]
        entry = index + 8
        for offset, fmt, value, message in [
            (entry + 12, "<I", len(valid) + 1, "beyond"),
            (entry + 24, "<H", 2, "compression"),
            (entry + 20, "<I", 99, "sizes"),
        ]:
            with self.subTest(message=message):
                data = bytearray(valid)
                struct.pack_into(fmt, data, offset, value)
                with self.assertRaisesRegex(check_packages.PackageError, message):
                    check_packages.read_package(self.write(data))

    def test_identical_and_conflicting_duplicates(self) -> None:
        package = check_packages.read_package(
            self.write(package_bytes([(KEY, b"a"), (KEY, b"a")]))
        )
        self.assertEqual(package.identical_duplicates, [KEY])
        self.assertEqual(len(package.resources), 1)
        with self.assertRaisesRegex(check_packages.PackageError, "conflicting duplicate"):
            check_packages.read_package(self.write(package_bytes([(KEY, b"a"), (KEY, b"b")])))

    def test_uncompressed_and_compressed_storage_are_not_called_identical(self) -> None:
        first = check_packages.read_package(self.write(package_bytes([(KEY, b"a")]), "a.package"))
        data = bytearray(package_bytes([(KEY, b"a")]))
        index = struct.unpack_from("<I", data, 64)[0]
        struct.pack_into("<H", data, index + 8 + 24, 0xFFFF)
        second = check_packages.read_package(self.write(data, "b.package"))
        self.assertNotEqual(first.resources[KEY], second.resources[KEY])

    def test_empty_package(self) -> None:
        self.assertEqual(check_packages.read_package(self.write(package_bytes([]))).resources, {})

    def test_cli_directory_overlaps_exit_codes_and_duplicate_inputs(self) -> None:
        first = self.write(package_bytes([(KEY, b"a")]), "a.package")
        self.write(package_bytes([(KEY, b"a")]), "b.package")
        ignored = self.directory / "nested"
        ignored.mkdir()
        (ignored / "broken.package").write_bytes(b"bad")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(check_packages.main([str(self.directory), str(first)]), 0)
        self.assertEqual(output.getvalue().count("PACKAGE "), 2)
        self.assertIn("stored-identical", output.getvalue())
        self.write(package_bytes([(KEY, b"b")]), "b.package")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check_packages.main([str(self.directory)]), 1)

    def test_cli_invalid_package_has_error_exit_without_traceback(self) -> None:
        path = self.write(b"broken")
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(check_packages.main([str(path)]), 2)
        self.assertIn("ERROR:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
