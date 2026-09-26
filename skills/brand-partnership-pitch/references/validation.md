# Validation record — 2026-09-23

This record distinguishes implementation checks from real service and creative output checks. No test credential, raw channel data, source video or real-person reference image is distributed in the skill.

## Workflow review

Reviewed brief interpretation, creator analysis, actual-host storyboard references, scoring, locked revisions, history and AV document delivery. The maintained requirements are in product-contract.md. No production data mutation or OpenRouter call was used.

## Live external services

User-supplied test credentials were held only in one test process's environment; API calls used authorization headers. They were not saved into the skill or package.

| Check | Result |
| --- | --- |
| TikTok Apify channel scrape | Passed; 3 normalized videos from a public creator channel |
| YouTube Apify channel scrape | Passed; 3 normalized Shorts |
| Instagram Apify Reels scrape | Passed; 3 normalized videos |
| TikTok Apify media acquisition | Passed; downloaded and decoded an 82-second reference clip |
| Instagram direct media acquisition | Passed; downloaded two clips, approximately 40 and 20 seconds |
| YouTube local media acquisition | Passed using yt-dlp 2026.08.19 on Python 3.12; downloaded a 20-second video with audio |
| ElevenLabs Scribe v2 | Passed on all 3 analyzed source clips; timestamped transcripts saved and inspected |
| Local faster-whisper inference | Not executed; optional backend code/mock/cache tests do not prove local-model quality |

An initial YouTube attempt from a Python 3.9 environment installed obsolete yt-dlp 2025.10.14 and failed. A Python 3.12 environment installed the required current version and succeeded. Setup instructions now warn about this dependency trap. A real Instagram clip exposed a JPEG color-range extraction failure; FFmpeg output explicitly uses full-range JPEG pixels and the corrected extraction succeeded. Frame sampling also respects the video stream duration when audio runs slightly longer.

## Actual-host storyboard and document acceptance

- Analyzed 3 public MKBHD clips: robot-camera demonstration, ruler/caliper demonstration, and hands-only phone demonstration. Source timestamps and limitations recorded locally. These samples do not establish the channel's complete sponsorship history or audience demographics.
- Used the inspected visible presenter frame from the robot-camera clip at 67.08 seconds as an actual imagegen identity reference. The person's name comes from channel metadata, not facial recognition.
- Wrote 3 complete 45-second alternatives for a clearly fictional DeskFold test brief. Two explicitly labelled Codex review passes ranked them; no independent-model consensus is claimed.
- Generated 4 black-and-white hand-drawn storyboard frames for the selected version: 3 preserve the host appearance; 1 is an intentional faceless product insert. Inspected face/wardrobe continuity, action, monochrome treatment and absence of image text.
- Produced editable Word, matching 4-page PDF, standalone AV-table HTML and copyable text. Visually checked all 4 PDF pages. The documents skill's canonical DOCX render matched those 4 page images pixel-for-pixel at 100 DPI.
- Checked HTML at normal desktop size and 390-pixel mobile width. Images remain embedded and text selectable. No public share URL is created by exporting HTML.
- Other alternatives are complete text scripts with explicit missing-storyboard labels; selecting them triggers their own full storyboard generation. They are not presented as illustrated.

## Automated checks

42 behavioral tests cover time ranges and missing evidence, actual reference requirements and hashes, black-and-white image acceptance, review aggregation/ranking/freshness, full/partial scene locks, dialogue-only image reuse, changed-image invalidation, snapshot/restore, provider normalization and interrupted paid-run recovery, subtitle parsing, real FFmpeg audio/silent fixtures and complete DOCX dialogue including long ensemble scripts. The skill-creator structural validator also passes.

This is a concrete one-channel creative acceptance test plus platform API canaries, not a claim that every creator, language, protected platform video or future provider version has been tested. API access and imagegen tool availability remain environment-dependent.

## Compact document layout — 2026-09-27

The illustrated six-scene demo was re-rendered with the single-column template and visually checked on all six pages using the canonical document renderer. All spoken lines remained extractable. A Chinese long-dialogue fixture exercised continuation pages and the optional full-notes appendix. The HTML was viewed at 390 px and desktop widths, with no horizontal overflow. This is rendered-layout verification, not a physical Word mobile app test.
