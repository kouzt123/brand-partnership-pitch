# Capability contract

A creator channel plus a brand brief should become a practical, reviewed script package. The primary use is sponsored content after the brand requirement is known; this is not an outreach-email or contract-negotiation tool. Explicit organic requests can use the same workflow without an invented sponsor.

| Capability | Required behavior | Implementation |
| --- | --- | --- |
| Brief | Brand/product, objective, audience, messages, concrete features, tone, deliverables, acceptable formats, usage, goal and constraints; distinguish facts from assumptions | SKILL.md, creative-method.md, data-contract.md |
| Creator evidence | Several actual videos, timestamped frames/transcripts, content structure and sponsor transitions; unknown remains unknown | providers.py, media.py |
| Host appearance | Bind clear original-video frames to each cast member; send actual image inputs for each relevant scene | workflow.py bind_reference/image_plan |
| Alternatives | Three complete, distinct and performable scripts by default, with full organic portions in integrations | creative-method.md |
| Review | Style/brand scores, production difficulty, safety notes, transparent review provenance and ranking | workflow.py apply_reviews |
| Storyboards | Black-and-white hand-drawn sketches, clean lines, minimal shading, no lettering; actual host continuity | storyboards.md, script_data.py |
| Revision | Scene feedback, independent visual/audio locks, exact full-lock preservation, saved versions and restore | workflow.py apply_revision/save_revision/restore_revision |
| Reuse | Dialogue-only changes keep valid images; visual/cast/reference changes invalidate affected images | script_data.py visual_fingerprint/revision_diff |
| Documents | Editable single-column scenes, images, full dialogue and scene notes; full brief/reviews/sources in companion notes or an optional appendix; PDF and page QA | documents.py |
| Reading/copying | Standalone HTML with embedded images and plain text; files are not a public share URL | preview.py |

The illustrated delivery gate requires current recorded review, all selected-variant images, bound real-person references, visual inspection records, fresh hashes and a complete, visually checked document export. Other full-script alternatives may be text-only until selected. No billing, login, production database, social posting or public hosting is bundled.
