from django.core.management.base import BaseCommand
from django.db import transaction
from uuid import UUID

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
    if ct == "digital":
        # lower-case canonical UUID string
        try:
            return str(UUID(str(value))).lower()
        except Exception:
            return str(value).lower()
    return str(value)


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

            # Purge all then re-insert unique normalized rows
            FavouriteModel.objects.all().delete()
            FavouriteModel.objects.bulk_create(by_key.values())

            # Optional: drop rows whose comic does not exist anymore
            to_delete = []
            for r in FavouriteModel.objects.all():
                if r.comic_type == "digital":
                    if not DigitalComicModel.objects.filter(id__iexact=r.comic_id).exists():
                        to_delete.append(r.id)
                else:
                    if not MotionComicModel.objects.filter(id=r.comic_id).exists():
                        to_delete.append(r.id)
            if to_delete:
                FavouriteModel.objects.filter(id__in=to_delete).delete()

        self.stdout.write(self.style.SUCCESS("Favourites cleanup complete."))