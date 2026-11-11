"""One ingestion run = one `DatasetVersion` + one validation report (SDD §8.6, §12.1).

    with IngestRun("chirps", version_label="2026-10", params={...}) as run:
        run.check_range("rainfall_mm", arr, 0, 2000)
        write_indicator(..., run.version.id, ...)
        run.data_date = date(2026, 10, 31)

All database writes happen in one transaction. A failed check (`level="error"`) or any exception
rolls everything back, marks the dataset `error` and still stores a report saying why.
Warnings (e.g. completeness < 95 %) are recorded but don't fail the run.
"""

from __future__ import annotations

import logging
import traceback
from datetime import date
from typing import Any

import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Dataset, DatasetVersion
from apps.catalog.status import compute_status

from .storage import put_json

log = logging.getLogger("apps.ingest")

COMPLETENESS_THRESHOLD = 0.95  # SDD §8.6


class ValidationFailed(Exception):
    pass


class IngestRun:
    def __init__(
        self,
        dataset_key: str,
        *,
        version_label: str = "",
        params: dict[str, Any] | None = None,
        echo=None,
    ):
        self.dataset_key = dataset_key
        self.version_label = version_label
        self.params = params or {}
        self.echo = echo or log.info
        self.checks: list[dict[str, Any]] = []
        self.stats: dict[str, Any] = {}
        self.sources: list[str] = []
        self.checksum = ""
        self.notes = ""
        self.data_date: date | None = None
        self.version: DatasetVersion

    # --- context manager -----------------------------------------------------------------
    def __enter__(self) -> IngestRun:
        self.dataset = Dataset.objects.get(key=self.dataset_key)
        self.started = timezone.now()
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset, version_label=self.version_label
        )
        self.echo(f"[{self.dataset_key}] run started (version {self.version.id})")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        report = self._report()
        if exc_type is None:
            try:
                key = put_json(settings.S3_BUCKET_MEDIA, self._report_key(), report)
                v = self.version
                v.data_date = self.data_date
                v.checksum = self.checksum
                v.notes = self.notes
                v.validation_report = key
                v.validation = report["summary"]
                v.save()
                ds = self.dataset
                ds.last_job_failed = False
                ds.status = compute_status(
                    ds.update_cadence, self.data_date, False, timezone.localdate()
                )
                ds.save(update_fields=["last_job_failed", "status"])
            except BaseException as e:
                self._atomic.__exit__(type(e), e, e.__traceback__)
                self._fail(report, e)
                raise
            self._atomic.__exit__(None, None, None)
            self.echo(f"[{self.dataset_key}] OK — {report['summary']} → {key}")
            return False

        self._atomic.__exit__(exc_type, exc, tb)
        self._fail(report, exc)
        return False

    def _fail(self, report: dict[str, Any], exc: BaseException) -> None:
        report["summary"]["passed"] = False
        report["error"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        report["traceback"] = traceback.format_exc(limit=8)
        try:
            key = put_json(settings.S3_BUCKET_MEDIA, self._report_key(failed=True), report)
        except Exception:  # storage down: the DB flag below still records the failure
            key = "(report not stored)"
        Dataset.objects.filter(pk=self.dataset.pk).update(last_job_failed=True, status="error")
        self.echo(f"[{self.dataset_key}] FAILED — {report['error']} → {key}")

    def _report_key(self, failed: bool = False) -> str:
        stamp = self.started.strftime("%Y%m%dT%H%M%SZ")
        suffix = "-FAILED" if failed else ""
        return f"reports/{self.dataset_key}/{stamp}-v{self.version.id}{suffix}.json"

    def _report(self) -> dict[str, Any]:
        warnings = sum(c["status"] == "warn" for c in self.checks)
        failed = sum(c["status"] == "fail" for c in self.checks)
        return {
            "dataset": self.dataset_key,
            "dataset_version_id": self.version.id,
            "version_label": self.version_label,
            "data_date": self.data_date,
            "started": self.started,
            "finished": timezone.now(),
            "params": self.params,
            "summary": {
                "passed": failed == 0,
                "checks": len(self.checks),
                "warnings": warnings,
                "failed": failed,
            },
            "checks": self.checks,
            "stats": self.stats,
            "sources": {"count": len(self.sources), "items": self.sources[:2000]},
            "checksum": self.checksum,
            "notes": self.notes,
        }

    # --- checks --------------------------------------------------------------------------
    def check(self, name: str, ok: bool, detail: Any = "", *, level: str = "error") -> bool:
        status = "pass" if ok else ("fail" if level == "error" else "warn")
        self.checks.append({"name": name, "status": status, "detail": detail})
        if status != "pass":
            self.echo(f"[{self.dataset_key}] {status.upper()}: {name} — {detail}")
        if status == "fail":
            raise ValidationFailed(f"{name}: {detail}")
        return ok

    def check_range(self, name: str, values: np.ndarray, lo: float, hi: float) -> bool:
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return self.check(f"{name} has values", False, "no finite values")
        vmin, vmax = float(finite.min()), float(finite.max())
        return self.check(
            f"{name} within [{lo}, {hi}]",
            lo <= vmin and vmax <= hi,
            {"min": round(vmin, 4), "max": round(vmax, 4)},
        )

    def check_completeness(
        self, name: str, values: np.ndarray, land: np.ndarray, labels: list[str] | None = None
    ) -> bool:
        """% of land hexes with a value, per period; warn below 95 % (SDD §8.6)."""
        v = values if values.ndim == 2 else values[:, None]
        frac = np.isfinite(v[land]).mean(axis=0)
        worst = int(np.argmin(frac))
        detail = {
            "min": round(float(frac.min()), 4),
            "mean": round(float(frac.mean()), 4),
            "worst_period": labels[worst] if labels else worst,
            "periods_below": int((frac < COMPLETENESS_THRESHOLD).sum()),
            "land_hexes": int(land.sum()),
        }
        return self.check(
            f"{name} completeness ≥ {COMPLETENESS_THRESHOLD:.0%}",
            bool(frac.min() >= COMPLETENESS_THRESHOLD),
            detail,
            level="warn",
        )

    def record(self, indicator_key: str, values: np.ndarray, periods: list[date], rows: int):
        finite = values[np.isfinite(values)]
        self.stats[indicator_key] = {
            "rows_res7": rows,
            "periods": len(periods),
            "first": periods[0] if periods else None,
            "last": periods[-1] if periods else None,
            "min": float(finite.min()) if finite.size else None,
            "max": float(finite.max()) if finite.size else None,
            "mean": float(finite.mean()) if finite.size else None,
        }
