# Revisions and resumability

Never restart acquisition for a simple script edit. Use the saved channel profile, brief evidence and media. Refresh only when the user requests newer channel data or a fact is time-sensitive.

Use an explicit feedback file and a complete proposed script JSON. Example:

```json
{"variation_id":"v1","overall_feedback":"Make the reveal more immediate.","scenes":[
 {"scene_id":"s1","approved":true,"lock_visual":true,"lock_audio":false,"comment":"Keep this shot; shorten the line."},
 {"scene_id":"s2","approved":true,"comment":"Approved, keep exactly."},
 {"scene_id":"s3","approved":false,"comment":"Show actual product use."}
]}
```

`approved: true` defaults both locks to true. Full locks preserve the whole original scene. Partial locks protect the relevant visual group (visual/cast/image prompt/on-screen cue) or audio and retain timing/notes. Unlocked scenes can change when overall feedback warrants it. All existing scene IDs and order remain; explicit structural rewrites can create a new script version instead of this constrained revision command.

```bash
python "$SKILL/scripts/brand_pitch.py" revise --script JOB/script.json --proposed JOB/proposed.json --feedback JOB/feedback.json
python "$SKILL/scripts/brand_pitch.py" diff --before JOB/revisions/SNAPSHOT.json --after JOB/script.json
python "$SKILL/scripts/brand_pitch.py" restore --script JOB/script.json --snapshot JOB/revisions/SNAPSHOT.json
```

`revise` validates first, saves an immutable old snapshot and feedback, applies lock enforcement, preserves unchanged/dialogue-only image records and clears visually changed images. It marks the variation as requiring a fresh review. It never silently changes other alternatives or global cast/brief. `restore` validates the snapshot against assets in the current job and preserves the current JSON before replacing it. Keep reference and image files; regenerated images use new names so older snapshots remain usable.

For explicitly requested global cast/style/brief changes, save a snapshot, edit the master, mark all affected reviews stale and run `diff`. The fingerprint includes only the actors in each scene, their actual reference hashes, style, aspect, visual, on-screen cue and prompt. Regenerate affected scenes, apply new review passes, render to a new directory and inspect every page. Never reuse a QA pass after editing.

## Provider interruption

Apify writes a submission-intent marker before creating a run, then its run ID and status. Rerunning the same command/state resumes the existing run and reads its dataset; it does not create a new run. If submission was interrupted before the run ID was persisted, inspect the Apify console and use `recover-run --state ... --run-id ...` with the matching run. Do not delete the marker and blindly retry. Failed Actor runs are retained and require a deliberate new state file for a new attempt.

ElevenLabs writes a request marker before upload. A completed transcript is reused when the audio hash/backend/settings match. An interrupted request is not automatically billed again; inspect provider history before removing its marker and explicitly retrying. Local transcription can be rerun safely but should use the cached result when identical.

Media preparation uses new output directories and contains source hashes/range metadata. Resume from a complete `media.json`; incomplete outputs should be inspected and regenerated in a new directory. Export directories are immutable by convention and protected against accidental overwrite by the CLI.

No process is claimed to survive a closed/interrupted Codex task. Saved artifacts and run IDs make a later session resumable.
