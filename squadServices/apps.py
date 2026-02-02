from django.apps import AppConfig


class SquadServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "squadServices"

    # def ready(self):
    #     # We must match the filename exactly: jasminSignals.py
    #     try:
    #         import squadServices.signals.jasminSignals

    #         print("Jasmin Signals Imported Successfully")
    #     except ImportError as e:
    #         # This helps debug if there is still an issue
    #         print(f"Signal Import Error: {e}")


# class SquadServicesConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "squadServices"
