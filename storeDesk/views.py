from decimal import Decimal
from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from django.core.cache import cache

import boto3
from botocore.exceptions import NoCredentialsError

from .models import (
    Genre,
    Comic,
    Order,
    OrderItem,
    Review,
    Wishlist,
    Promotion,
    PromotionRedemption,
)
from .serializers import (
    GenreSerializer,
    ComicSerializer,
    OrderSerializer,
    ReviewSerializer,
    WishlistSerializer,
    PromotionSerializer,
    QuoteRequestSerializer,
    QuoteResponseSerializer,
)
from profileDesk.models import CustomUser  # noqa: F401


# -------------------------
# Pagination
# -------------------------
class StorePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# -------------------------
# Helpers
# -------------------------
def _compute_unit_price(comic: Comic) -> Decimal:
    return Decimal(comic.discount_price if comic.discount_price is not None else comic.price)


def _validate_and_get_active_promo(code: str) -> Promotion | None:
    if not code:
        return None
    v = code.strip().upper()
    now = timezone.now()
    return Promotion.objects.filter(code=v, start_date__lte=now, end_date__gte=now).first()


def _is_promo_applicable_to_line(promo: Promotion, comic: Comic) -> bool:
    if promo.comic_id and promo.comic_id != comic.id:
        return False
    if promo.genre_id and not comic.genres.filter(id=promo.genre_id).exists():
        return False
    return True


def _apply_promo_to_subtotal(subtotal_applicable: Decimal, promo: Promotion) -> Decimal:
    if subtotal_applicable <= 0:
        return Decimal("0.00")
    if promo.discount_type == "percentage":
        discount = (subtotal_applicable * Decimal(promo.discount_value)) / Decimal("100")
    else:
        discount = Decimal(promo.discount_value)
    if discount < 0:
        discount = Decimal("0.00")
    if discount > subtotal_applicable:
        discount = subtotal_applicable
    return discount


def _build_lines_from_payload(data: dict) -> list[dict]:
    """
    Returns list of dict lines: {comic: Comic, quantity: int, unit_price: Decimal, line_subtotal: Decimal}
    Supports both legacy comic+quantity and items[] payloads.
    """
    lines = []
    if data.get("items"):
        for it in data["items"]:
            comic = it["comic"]
            qty = int(it.get("quantity") or 1)
            unit = _compute_unit_price(comic)
            lines.append(
                {
                    "comic": comic,
                    "quantity": qty,
                    "unit_price": unit,
                    "line_subtotal": unit * qty,
                }
            )
    else:
        comic = data["comic"]
        qty = int(data.get("quantity") or 1)
        unit = _compute_unit_price(comic)
        lines.append(
            {
                "comic": comic,
                "quantity": qty,
                "unit_price": unit,
                "line_subtotal": unit * qty,
            }
        )
    return lines


def _compute_quote(data: dict) -> dict:
    """
    data contains validated serializer attrs for either quote or order create.
    Returns {items: [...], subtotal, discount_total, final_price, promo, eligible_comics}
    """
    promo_code = (data.get("promo_code") or "").strip().upper() or None
    promo = _validate_and_get_active_promo(promo_code) if promo_code else None

    lines = _build_lines_from_payload(data)
    subtotal = sum((ln["line_subtotal"] for ln in lines), start=Decimal("0.00"))

    discount_total = Decimal("0.00")
    if promo:
        applicable_subtotal = sum(
            (ln["line_subtotal"] for ln in lines if _is_promo_applicable_to_line(promo, ln["comic"])),
            start=Decimal("0.00"),
        )
        min_amount = Decimal(promo.min_order_amount) if promo.min_order_amount is not None else None
        if min_amount is not None and subtotal < min_amount:
            discount_total = Decimal("0.00")
        else:
            discount_total = _apply_promo_to_subtotal(applicable_subtotal, promo)

    final_price = subtotal - discount_total
    if final_price < 0:
        final_price = Decimal("0.00")

    resp_items = [
        {
            "comic": ln["comic"].id,
            "quantity": ln["quantity"],
            "unit_price": ln["unit_price"],
            "discount_applied": Decimal("0.00"),
            "final_price": ln["line_subtotal"],
        }
        for ln in lines
    ]

    eligible_ids = [
        ln["comic"].id
        for ln in lines
        if promo and _is_promo_applicable_to_line(promo, ln["comic"])
    ]

    return {
        "items": resp_items,
        "subtotal": subtotal,
        "discount_total": discount_total,
        "final_price": final_price,
        "promo": promo,
        "eligible_comics": eligible_ids,
    }


# -------------------------
# Genre
# -------------------------
class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


# -------------------------
# Comic
# -------------------------
class ComicViewSet(viewsets.ModelViewSet):
    queryset = Comic.objects.all()
    serializer_class = ComicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StorePagination

    def get_queryset(self):
        queryset = self.queryset
        genre_ids = self.request.query_params.get("genre", "").split(",")
        if genre_ids and genre_ids[0]:
            queryset = queryset.filter(genres__id__in=genre_ids).distinct()

        search = self.request.query_params.get("search", "")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(genres__name__icontains=search)
            ).distinct()

        sort = self.request.query_params.get("sort", "created_at")
        if sort == "price":
            queryset = queryset.order_by("price")
        elif sort == "-price":
            queryset = queryset.order_by("-price")
        elif sort == "rating":
            queryset = queryset.order_by("-rating")
        elif sort == "-rating":
            queryset = queryset.order_by("rating")
        elif sort == "newest":
            queryset = queryset.order_by("-created_at")

        filter_param = self.request.query_params.get("filter", "")
        if filter_param:
            if "rating>4" in filter_param:
                queryset = queryset.filter(rating__gt=4)
            if "stock>0" in filter_param:
                queryset = queryset.filter(stock_quantity__gt=0)
        return queryset

    def retrieve(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        serializer = self.get_serializer(comic)
        data = dict(serializer.data)

        # Truncate description
        words = (data.get("description") or "").split()
        if len(words) > 50:
            data["description"] = " ".join(words[:50]) + " ...more"

        # Apply active promotion discount (genre/comic based) for display only
        current_time = timezone.now()
        active_promo = Promotion.objects.filter(
            Q(comic=comic) | Q(genre__in=comic.genres.all()),
            start_date__lte=current_time,
            end_date__gte=current_time,
        ).first()
        if active_promo and (data.get("discount_price") in (None, "")):
            base = comic.discount_price if comic.discount_price is not None else comic.price
            if active_promo.discount_type == "percentage":
                discount = (base * active_promo.discount_value) / Decimal("100")
            else:
                discount = active_promo.discount_value
            new_price = base - discount
            if new_price < 0:
                new_price = Decimal("0.00")
            data["discount_price"] = new_price

        # Signed preview URL (if using S3)
        if comic.preview_file:
            s3_client = boto3.client("s3")
            try:
                preview_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": "your-bucket-name", "Key": comic.preview_file.name},
                    ExpiresIn=3600,
                )
                data["preview_file"] = preview_url
            except NoCredentialsError:
                data["preview_file"] = None

        return Response(data)

    @action(detail=True, methods=["get"])
    def share_link(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        base_url = request.build_absolute_uri("/")[:-1]
        link = f"{base_url}/api/store/comics/{comic.id}/"
        return Response({"share_link": link}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="reviews")
    def reviews(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        queryset = Review.objects.filter(comic=comic).order_by("-created_at")
        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# -------------------------
# Order
# -------------------------
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related("user").prefetch_related("items__comic")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "order"

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="quote")
    def quote(self, request):
        """
        Compute price for either {comic, quantity} or {items: [{comic, quantity}, ...]}, with optional promo_code.
        Does not create an order or mutate stock.
        """
        req_ser = QuoteRequestSerializer(data=request.data, context={"request": request})
        req_ser.is_valid(raise_exception=True)
        quote = _compute_quote(req_ser.validated_data)

        resp_ser = QuoteResponseSerializer(
            {
                "items": quote["items"],
                "subtotal": quote["subtotal"],
                "discount_total": quote["discount_total"],
                "final_price": quote["final_price"],
                "eligible_comics": quote.get("eligible_comics", []),
            }
        )
        return Response(resp_ser.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create order with legacy or multi-item payload.
        - Validates stock at serializer level.
        - Computes totals and promo here.
        - Does NOT decrement stock or increment buyer_count here (post-payment via webhook).
        """
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Compute totals and promo
        payload = dict(serializer.validated_data)
        if "items" in serializer.validated_data:
            payload["items"] = serializer.validated_data["items"]
        quote_info = _compute_quote(payload)

        promo_code = (request.data.get("promo_code") or "").strip().upper() or None
        promo_obj = quote_info.get("promo")

        # Enforce promo limits on create (not in quote)
        if promo_obj:
            if promo_obj.max_uses is not None and promo_obj.used_count >= promo_obj.max_uses:
                return Response({"error": "Promo code usage limit reached."}, status=status.HTTP_400_BAD_REQUEST)
            user_used = PromotionRedemption.objects.filter(user=request.user, promotion=promo_obj).count()
            if promo_obj.per_user_limit is not None and user_used >= promo_obj.per_user_limit:
                return Response(
                    {"error": "You have already used this promo code the maximum number of times."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Save order and items via serializer.create
        order: Order = serializer.save(
            user=request.user,
            promo_code=promo_code if promo_obj else None,
        )

        # Update totals and amount from quote
        order.subtotal = quote_info["subtotal"]
        order.discount_applied = quote_info["discount_total"]
        order.final_price = quote_info["final_price"]
        order.amount = quote_info["final_price"]
        order.save(update_fields=["subtotal", "discount_applied", "final_price", "amount"])

        # Return the created order
        resp = self.get_serializer(order)
        return Response(resp.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="dev-confirm")
    @transaction.atomic
    def dev_confirm(self, request, pk=None):
        # Guard: only allow in DEBUG
        if not settings.DEBUG:
            return Response({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        from .serializers import DevConfirmRequestSerializer  # local import to avoid cycles

        req = DevConfirmRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        status_choice = req.validated_data["status"]

        order: Order = self.get_object()  # get_queryset already scopes to request.user

        # Idempotent behavior
        if order.payment_status in ("paid", "failed"):
            ser = self.get_serializer(order)
            return Response(ser.data, status=status.HTTP_200_OK)

        if status_choice == "failed":
            order.payment_status = "failed"
            order.save(update_fields=["payment_status"])
            ser = self.get_serializer(order)
            return Response(ser.data, status=status.HTTP_200_OK)

        # status_choice == "paid"
        # Build lines (support legacy single-item and multi-item)
        if order.items.exists():
            lines = [{"comic": li.comic, "qty": int(li.quantity)} for li in order.items.all()]
        else:
            if not order.comic_id or not order.quantity:
                return Response({"error": "Order lines missing."}, status=status.HTTP_400_BAD_REQUEST)
            lines = [{"comic": order.comic, "qty": int(order.quantity)}]

        # Stock validation
        for ln in lines:
            if ln["comic"].stock_quantity < ln["qty"]:
                return Response(
                    {"error": f"'{ln['comic'].title}' has only {ln['comic'].stock_quantity} in stock."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Apply side-effects: decrement stock, increment buyer_count, promo redemption
        for ln in lines:
            Comic.objects.filter(id=ln["comic"].id).update(stock_quantity=F("stock_quantity") - ln["qty"])
            Comic.objects.filter(id=ln["comic"].id).update(buyer_count=F("buyer_count") + ln["qty"])

        # Promo redemption bookkeeping (if promo_code still active)
        if order.promo_code:
            promo = _validate_and_get_active_promo(order.promo_code)
            if promo:
                Promotion.objects.filter(id=promo.id).update(used_count=F("used_count") + 1)
                PromotionRedemption.objects.get_or_create(user=order.user, promotion=promo, order=order)

        # Mark paid
        order.payment_status = "paid"
        order.save(update_fields=["payment_status"])

        ser = self.get_serializer(order)
        return Response(ser.data, status=status.HTTP_200_OK)


# -------------------------
# Review
# -------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "review"

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        comic = serializer.validated_data["comic"]

        # Must be paid order, either legacy single-item or multi-item
        purchased_legacy = Order.objects.filter(
            user=user, comic=comic, payment_status="paid"
        ).exists()
        purchased_multi = OrderItem.objects.filter(
            order__user=user, order__payment_status="paid", comic=comic
        ).exists()
        if not (purchased_legacy or purchased_multi):
            raise PermissionDenied("You can only review a comic you have purchased.")

        review = serializer.save(user=user)
        # Update comic rating aggregates
        comic.rating_count = (comic.rating_count or 0) + 1
        comic.rating = ((comic.rating or Decimal("0")) * (comic.rating_count - 1) + review.rating) / comic.rating_count
        comic.save(update_fields=["rating", "rating_count"])


# -------------------------
# Wishlist
# -------------------------
class WishlistViewSet(viewsets.ModelViewSet):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "wishlist"

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        comic_id = request.data.get("comic")
        comic = get_object_or_404(Comic, pk=comic_id)
        user = request.user
        existing = Wishlist.objects.filter(user=user, comic=comic)
        if existing.exists():
            existing.delete()
            return Response({"message": "Removed from wishlist"}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data={"comic": comic_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# -------------------------
# Promotion
# -------------------------
class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StorePagination

    def get_queryset(self):
        return self.queryset.filter(end_date__gte=timezone.now())


# -------------------------
# Recommendations (simple heuristic)
# -------------------------
class RecommendationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        cache_key = f"recommendations_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # Consider both legacy and multi-item paid orders
        paid_orders = Order.objects.filter(user=user, payment_status="paid").prefetch_related("items__comic__genres")
        genre_ids = set()
        comic_ids_purchased = set()

        for od in paid_orders:
            if od.comic_id:
                comic_ids_purchased.add(od.comic_id)
            for li in od.items.all():
                comic_ids_purchased.add(li.comic_id)

        if comic_ids_purchased:
            genres_qs = Genre.objects.filter(comic__id__in=comic_ids_purchased).distinct()
            genre_ids.update(genres_qs.values_list("id", flat=True))

            all_comics = Comic.objects.filter(genres__id__in=genre_ids).distinct().order_by("-rating")
            recommended = [c for c in all_comics if c.id not in comic_ids_purchased][:5]
            if not recommended:
                recommended = [c for c in all_comics if c.id in comic_ids_purchased][:5]

            serializer = ComicSerializer(recommended, many=True)
            cache.set(cache_key, serializer.data, timeout=60 * 60)
            return Response(serializer.data)

        return Response({"message": "No recommendations available"}, status=status.HTTP_200_OK)