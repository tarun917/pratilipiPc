from django.apps import AppConfig


class PaymentsDeskConfig(AppConfig):  # Use PaymentsDeskConfig for clarity
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'paymentsDesk'  # <-- Correct name with "s"
