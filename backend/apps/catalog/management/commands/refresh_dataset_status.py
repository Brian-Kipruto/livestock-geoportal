from django.core.management.base import BaseCommand

from apps.catalog.tasks import refresh_dataset_status


class Command(BaseCommand):
    help = "Recompute dataset freshness status (live / stale / pending / error)."

    def handle(self, *args, **opts):
        n = refresh_dataset_status()
        self.stdout.write(self.style.SUCCESS(f"{n} dataset(s) changed status"))
