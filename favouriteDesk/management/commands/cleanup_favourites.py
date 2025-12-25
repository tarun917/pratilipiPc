from django.core.management.base import BaseCommand
from django.db import transaction

from favouriteDesk.models import FavouriteModel
from digitalcomicDesk.models import ComicModel as DigitalComicModel
from motioncomicDesk.models import ComicModel as MotionComicModel


def canonical_type(t: str) -> str:
    t = (t or "").lower()
    if t in ("digital", "digitalcomic"):
        return "digital"
    if t in ("motion", "motioncomic"):
        return "motion"
    return t


def normalize_id(ct: str, value: str) -> str:
    """
    Normalize IDs - both digital and motion comics now use simple integer IDs.
    Just return as string.
    """
    return str(value).strip()


class Command(BaseCommand):
    help = "Normalize FavouriteModel rows: fix comic_type aliases, normalize IDs, and dedupe."

    def handle(self, *args, **options):
        self.stdout.write("Starting favourites cleanup…")
        with transaction.atomic():
            rows = list(FavouriteModel.objects.all().select_for_update())
            fixed = []
            for row in rows:
                ct = canonical_type(row.comic_type)
                cid = normalize_id(ct, row.comic_id)
                row.comic_type = ct
                row.comic_id = cid
                fixed.append(row)

            # Upsert normalized rows into a temporary dict keyed by (user_id, type, id)
            by_key = {}
            for r in fixed:
                key = (r.user_id, r.comic_type, r.comic_id)
                # Keep the newest (largest created_at); fallback to last writer wins
                prev = by_key.get(key)
                if prev is None or (getattr(r, "created_at", None) and getattr(prev, "created_at", None) and r.created_at > prev.created_at):
                    by_key[key] = r

            # Delete all and bulk create deduplicated
            FavouriteModel.objects.all().delete()
            FavouriteModel.objects.bulk_create(by_key.values())

        self.stdout.write(self.style.SUCCESS(f"Cleanup complete. {len(by_key)} favourites retained."))
