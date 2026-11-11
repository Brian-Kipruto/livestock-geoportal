# ADR-009 — SeaweedFS instead of MinIO for self-hosted S3

**Status:** Proposed (deviation from SDD §6.2 / §7, which name MinIO)

## Context
The SDD names MinIO as the S3-compatible store. During M0 setup (Nov 2026) MinIO's public Docker images were no longer pullable (`docker.io/minio/minio` returns "access denied"); MinIO stopped distributing community builds in 2025. An unmaintained object store is a handover risk (R11) and the AGPL licence needs review for ECA ownership (C3).

## Decision
Use **SeaweedFS** (Apache-2.0) with its S3 gateway in Docker Compose (`s3` service). All code talks to the S3 API through env vars (`S3_ENDPOINT`, keys, bucket names), so any S3 provider can replace it in production without code changes.

## Consequences
- Buckets are created by `manage.py ensure_buckets` at Django start.
- Alternatives if needed: Garage (AGPL), or a managed S3 from the host.
