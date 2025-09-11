import io
import os
import re
import zipfile
from dataclasses import dataclass
from typing import List, Tuple

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from .models import EpisodeModel, SliceModel

ZERO_PAD = 4  # 0001, 0002, ...


@dataclass
class ImportReport:
    total_in_zip: int
    accepted_images: int
    created_slices: int
    replaced_existing: int
    errors: List[str]


def _is_image_member(name: str) -> bool:
    # Allow jpg/jpeg only as per plan (extend to png if needed)
    return bool(re.search(r"\.(jpg|jpeg)$", name.strip().lower()))


def _numeric_key(name: str) -> Tuple[int, str]:
    """
    Natural/numeric sort key.
    Takes basename and extracts the FIRST number for ordering.
    Falls back to a large number if no digits to push such files to the end.
    """
    base = os.path.basename(name)
    digits = re.findall(r"(\d+)", base)
    primary = int(digits[0]) if digits else 10**9
    return (primary, base.lower())


@transaction.atomic
def import_episode_slices_zip(episode: EpisodeModel, zip_file) -> ImportReport:
    """
    Import slices from a ZIP file for a given episode.
    - Filters JPG/JPEG
    - Ignores nested folders; only root files are considered
    - Sorts by numeric filename (natural sort)
    - Atomic Replace All (deletes previous SliceModel entries and their files)
    - Saves via Django storage (S3/local), path digitalcomics/episodes/<episode_id>/slices/0001.jpg
    Returns ImportReport.
    """
    report = ImportReport(
        total_in_zip=0,
        accepted_images=0,
        created_slices=0,
        replaced_existing=0,
        errors=[],
    )

    # Read zip into memory
    try:
        zip_bytes = zip_file.read()
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as e:
        report.errors.append(f"Invalid ZIP: {e}")
        return report

    # Collect files
    members = [m for m in zf.infolist() if not m.is_dir()]
    report.total_in_zip = len(members)

    # Only root-level files; filter and sort
    def is_root_level(m: zipfile.ZipInfo) -> bool:
        # Accept files without '/' or with exactly one path segment (basename)
        return '/' not in m.filename.strip('/')

    image_members = [m for m in members if is_root_level(m) and _is_image_member(os.path.basename(m.filename))]
    image_members.sort(key=lambda m: _numeric_key(m.filename))
    report.accepted_images = len(image_members)

    if report.accepted_images == 0:
        report.errors.append("No JPG/JPEG files found in ZIP root. Use 0001.jpg, 0002.jpg, ...")
        return report

    # Replace All: delete existing slices and their files
    existing = list(SliceModel.objects.filter(episode=episode).order_by("order"))
    report.replaced_existing = len(existing)
    for s in existing:
        try:
            if s.file and s.file.name and default_storage.exists(s.file.name):
                default_storage.delete(s.file.name)
        except Exception:
            # Ignore storage delete failures; DB cleanup still happens
            pass
    SliceModel.objects.filter(episode=episode).delete()

    # Create new slices with zero-padded order
    order = 1
    for m in image_members:
        fname = f"{str(order).zfill(ZERO_PAD)}.jpg"
        data = zf.read(m.filename)  # read by filename for compatibility
        cf = ContentFile(data)

        slice_obj = SliceModel(
            episode=episode,
            order=order,
            width=1080,   # default; client can compute real from image if needed
            height=None,
        )
        # Saving via ImageField ensures upload_to path and URL generation
        slice_obj.file.save(fname, cf, save=False)
        slice_obj.save()
        report.created_slices += 1
        order += 1

    return report