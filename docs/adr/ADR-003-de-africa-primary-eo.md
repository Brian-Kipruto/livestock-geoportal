# ADR-003 — Digital Earth Africa as primary EO source

**Status:** Proposed

## Context
Free, open, Africa-clipped, cloud-native data reduces processing and licence risk (C3). Google Earth Engine has terms and runtime dependency risks.

## Decision
Pull from DE Africa STAC (`pystac-client` + `odc-stac`) first; original providers only where DE Africa lacks the product or history. GEE may only be used for offline processing if Gladys approves (open question); **never at runtime**.

## Consequences
- Raw downloads cached by checksum; COGs stored locally (R7 mitigation).
