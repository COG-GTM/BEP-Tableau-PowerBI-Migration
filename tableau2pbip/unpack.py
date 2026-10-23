from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


@dataclass(frozen=True, slots=True)
class Unpacked:
    twb_path: Path
    hyper_paths: list[Path]
    image_paths: list[Path]


def _target_path(root: Path, member: str) -> Path:
    destination = (root / Path(member)).resolve()
    resolved_root = root.resolve()
    if destination != resolved_root and resolved_root not in destination.parents:
        raise ValueError(f"Archive member escapes extraction directory: {member}")
    return destination


def unpack(twbx: Path, workdir: Path) -> Unpacked:
    source = twbx.resolve()
    target = workdir.resolve()
    target.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() == ".twb":
        images = sorted(
            path
            for path in source.parent.rglob("*")
            if path.is_file() and path.parent.name.lower() == "image"
        )
        hypers = sorted(source.parent.rglob("*.hyper"))
        return Unpacked(source, hypers, images)

    if source.suffix.lower() != ".twbx":
        raise ValueError(f"Expected a .twbx or .twb workbook, got {source.name}")

    with ZipFile(source) as archive:
        members = archive.namelist()
        twb_members = [name for name in members if name.lower().endswith(".twb")]
        if not twb_members:
            raise ValueError(f"No .twb workbook found in {source}")
        twb_member = twb_members[0]
        selected = [
            name
            for name in members
            if name == twb_member
            or name.lower().endswith(".hyper")
            or any(part.lower() == "image" for part in Path(name).parts)
        ]
        for member in selected:
            destination = _target_path(target, member)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as content, destination.open("wb") as output:
                output.write(content.read())

    twb_path = _target_path(target, twb_member)
    hyper_paths = sorted(target.rglob("*.hyper"))
    image_paths = sorted(
        path
        for path in target.rglob("*")
        if path.is_file() and path.parent.name.lower() == "image"
    )
    return Unpacked(twb_path, hyper_paths, image_paths)
