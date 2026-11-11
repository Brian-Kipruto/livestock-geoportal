# ADR-008 — Template-based profile text

**Status:** Proposed

## Decision
Profile summaries come from Django templates with conditional phrases over statistics, not from an LLM. Each PDF stores the dataset versions used.

## Consequences
Reproducible, zero runtime cost, translatable, auditable.
