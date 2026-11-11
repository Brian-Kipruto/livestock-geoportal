from celery import shared_task
from django.utils import timezone

from .models import Dataset
from .status import compute_status


@shared_task
def refresh_dataset_status() -> int:
    """Hourly: recompute freshness for every dataset (SDD §12.2). Returns rows changed."""
    today = timezone.localdate()
    changed = 0
    for ds in Dataset.objects.prefetch_related("versions"):
        v = ds.latest_version
        new = compute_status(
            ds.update_cadence, v.data_date if v else None, ds.last_job_failed, today
        )
        if new != ds.status:
            ds.status = new
            ds.save(update_fields=["status"])
            changed += 1
    return changed
