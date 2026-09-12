# docs/design

The September 2026 audit's 207 files of evidence moved to **`planetai-design`, at `design/audit/2026-09/`** — this is a repo households install from, and the pixels of a design review are not theirs to pull. `AUDIT_2026-09.md` and `HANDOFF_audit.md` stay here and read it from there: `HANDOFF_audit.md`'s paths were rewritten, and `AUDIT_2026-09.md` cites evidence as `audit/…`, which now means `planetai-design/design/audit/2026-09/…`.

The visual language is not this repo's to edit either. **`planetai-design/planetai-theme.css`** is generated from that repo's `references/planetai-layer.md`, and `app/static/planetai-theme.css` is a byte-for-byte copy of it, held there by `tools/check_theme.py` — which is in `make lint` and fails.

Change a token in the design repo and copy it here. `LANGUAGE_GAP.md` records where this dashboard still disagrees with that language.
