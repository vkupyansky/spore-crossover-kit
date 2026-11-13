#!/usr/bin/env python3
"""Report overlapping resource keys in Spore DBPF 3.0 packages.

Only stored payloads and their size/compression metadata are compared. RefPack
resources are not decompressed, and DLL behaviour and load order are not checked.
An overlap can be intentional; no overlaps does not prove mod compatibility.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from itertools import combinations
from pathlib import Path
import struct
import sys
from typing import BinaryIO, Sequence


ResourceKey = tuple[int, int, int]  # group, instance, type
HEADER_SIZE = 96
CHUNK_SIZE = 1024 * 1024


class PackageError(ValueError):
    """The file is malformed or uses an unsupported DBPF variant."""


@dataclass(frozen=True)
class Resource:
    stored_size: int
    unpacked_size: int
    compression: int
    sha256: str


@dataclass
class Package:
    path: Path
    sha256: str
    resources: dict[ResourceKey, Resource]
    identical_duplicates: list[ResourceKey]


def hash_range(stream: BinaryIO, offset: int, length: int) -> str:
    stream.seek(offset)
    digest = hashlib.sha256()
    while length:
        block = stream.read(min(length, CHUNK_SIZE))
        if not block:
            raise PackageError("file was truncated while reading resource data")
        digest.update(block)
        length -= len(block)
    return digest.hexdigest()


def format_key(key: ResourceKey) -> str:
    return ":".join(f"{part:08x}" for part in key)


def read_package(path: Path) -> Package:
    """Read an ordinary 32-bit-offset Spore package without extracting its data."""
    with path.open("rb") as stream:
        stream.seek(0, 2)
        file_size = stream.tell()
        stream.seek(0)
        header = stream.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise PackageError("truncated DBPF header (expected 96 bytes)")
        if header[:4] != b"DBPF":
            raise PackageError("expected DBPF magic (DBBF and other formats are unsupported)")
        version = struct.unpack_from("<II", header, 4)
        index_version = (
            struct.unpack_from("<I", header, 32)[0],
            struct.unpack_from("<I", header, 60)[0],
        )
        if version != (3, 0) or index_version != (0, 3):
            raise PackageError(
                f"unsupported DBPF/index versions: {version[0]}.{version[1]} / "
                f"{index_version[0]}.{index_version[1]}"
            )
        count = struct.unpack_from("<I", header, 36)[0]
        index_size = struct.unpack_from("<I", header, 44)[0]
        index_offset = struct.unpack_from("<I", header, 64)[0]
        if index_offset > file_size or index_size > file_size - index_offset:
            raise PackageError("index extends beyond the file")
        if index_size == 0 and count == 0:
            return Package(path, hash_range(stream, 0, file_size), {}, [])
        if index_offset < HEADER_SIZE or index_size < 4:
            raise PackageError("invalid index offset or truncated index flags")
        stream.seek(index_offset)
        index = stream.read(index_size)
        if len(index) != index_size:
            raise PackageError("truncated index")
        flags = struct.unpack_from("<I", index)[0]
        if flags & ~7:
            raise PackageError(f"unsupported index flags: 0x{flags:08x}")
        shared_size = 4 * ((flags & 1 != 0) + (flags & 2 != 0) + (flags & 4 != 0))
        entry_size = 28 - 4 * ((flags & 1 != 0) + (flags & 2 != 0))
        if 4 + shared_size + count * entry_size != index_size:
            raise PackageError("index size does not match its flags and resource count")
        cursor = 4

        def u32() -> int:
            nonlocal cursor
            value = struct.unpack_from("<I", index, cursor)[0]
            cursor += 4
            return value

        shared_type = u32() if flags & 1 else None
        shared_group = u32() if flags & 2 else None
        if flags & 4:
            u32()  # Reserved shared value in Spore's DBPF index.
        resources: dict[ResourceKey, Resource] = {}
        duplicates: list[ResourceKey] = []
        for _ in range(count):
            kind = u32() if shared_type is None else shared_type
            group = u32() if shared_group is None else shared_group
            instance, offset, stored_size, unpacked_size = u32(), u32(), u32(), u32()
            stored_size &= 0x7FFFFFFF
            compression, saved = struct.unpack_from("<HB", index, cursor)
            cursor += 4
            if compression not in (0, 0xFFFF):
                raise PackageError(f"unsupported compression label: 0x{compression:04x}")
            if saved != 1:
                raise PackageError("unsupported unsaved resource entry")
            if offset > file_size or stored_size > file_size - offset:
                raise PackageError("resource data extends beyond the file")
            if compression == 0 and stored_size != unpacked_size:
                raise PackageError("uncompressed resource has inconsistent sizes")
            key = (group, instance, kind)
            resource = Resource(
                stored_size, unpacked_size, compression,
                hash_range(stream, offset, stored_size),
            )
            previous = resources.get(key)
            if previous is not None:
                if previous != resource:
                    raise PackageError(f"conflicting duplicate resource: {format_key(key)}")
                duplicates.append(key)
            resources[key] = resource
        return Package(path, hash_range(stream, 0, file_size), resources, duplicates)


def package_paths(inputs: Sequence[Path]) -> list[Path]:
    """Expand explicitly named directories one level deep and deduplicate paths."""
    result: list[Path] = []
    seen: set[Path] = set()
    for path in inputs:
        path = path.expanduser().resolve(strict=True)
        if path.is_dir():
            candidates = sorted(
                child for child in path.iterdir()
                if child.is_file() and child.suffix.lower() == ".package"
            )
            if not candidates:
                raise PackageError(f"no .package files in directory: {path}")
        elif path.is_file():
            candidates = [path]
        else:
            raise PackageError(f"not a regular file or directory: {path}")
        for candidate in candidates:
            candidate = candidate.resolve(strict=True)
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Exit codes: 0 = no different overlaps; 1 = different overlaps; "
        "2 = invalid input or unsupported format. Identical overlaps can still affect load order.",
    )
    parser.add_argument(
        "paths", metavar="FILE_OR_DIR", nargs="+", type=Path,
        help="package files or directories containing .package files (not recursive)",
    )
    args = parser.parse_args(argv)
    packages: list[Package] = []
    try:
        paths = package_paths(args.paths)
        for path in paths:
            try:
                packages.append(read_package(path))
            except PackageError as exc:
                raise PackageError(f"{path}: {exc}") from exc
    except (OSError, PackageError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for package in packages:
        print(f"PACKAGE {package.path} {len(package.resources)} resources SHA256={package.sha256}")
        for key in package.identical_duplicates:
            print(f"  IDENTICAL DUPLICATE {format_key(key)}")
    different = False
    for first, second in combinations(packages, 2):
        overlap = first.resources.keys() & second.resources.keys()
        if not overlap:
            continue
        print(f"OVERLAP {first.path} / {second.path}: {len(overlap)}")
        for key in sorted(overlap):
            equal = first.resources[key] == second.resources[key]
            different |= not equal
            label = "stored-identical" if equal else "DIFFERENT stored payload/metadata"
            print(f"  {format_key(key)} {label}")
    print("Stored-resource comparison only; this does not prove mod compatibility.")
    return 1 if different else 0


if __name__ == "__main__":
    raise SystemExit(main())
