# digitalcomicDesk/integrations.py

from dataclasses import dataclass
from typing import Tuple
from django.db import transaction
from profileDesk.models import CustomUser

# In future, replace with premiumDesk services/models

def is_user_premium(user: CustomUser) -> bool:
    """
    Stub premium check. Replace with premiumDesk integration:
    - e.g., Subscription.objects.filter(user=user, active=True).exists()
    """
    # TODO: integrate premiumDesk here
    return getattr(user, "is_premium", False) or False


@dataclass
class DebitResult:
    success: bool
    new_balance: int
    error_code: str | None = None
    error_message: str | None = None


@transaction.atomic
def debit_coins(user: CustomUser, amount: int, idempotency_key: str) -> DebitResult:
    """
    Stub wallet debit using user.coin_count. Replace with premiumDesk WalletLedger.
    Idempotency behavior (stub): no-op; upstream should prevent duplicate charges by access check.
    """
    current = getattr(user, "coin_count", 0) or 0
    if amount <= 0:
        return DebitResult(success=True, new_balance=current)

    if current < amount:
        return DebitResult(
            success=False,
            new_balance=current,
            error_code="insufficient_balance",
            error_message="Insufficient coins",
        )

    new_balance = current - amount
    setattr(user, "coin_count", new_balance)
    # Persist only if coin_count is a real DB field on CustomUser
    try:
        user.save(update_fields=["coin_count"])
    except Exception:
        # Fallback save
        user.save()

    return DebitResult(success=True, new_balance=new_balance)