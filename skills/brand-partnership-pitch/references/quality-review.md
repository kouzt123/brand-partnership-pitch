# Script review, scoring and recommendation

Retain the product's visible assessment: creator style match, brand alignment, production effort, brand safety, reviewer explanation and a ranked recommendation. Scores are editorial estimates, not observed performance predictions.

After writing all alternatives, read them afresh against channel evidence and the complete brief. Use two review perspectives: (1) creator performance/format/voice and (2) brand goals/facts/production. A reviewer must assess both style and brand so aggregation remains comparable. If the environment and task authorize independent agents, actual separate reviewers can produce independent records. Otherwise perform separate passes in Codex, clearly labelled `separate_pass`; never claim different external models or independent consensus. No extra model API is needed.

Use these anchors for both 0–100 scores: 90–100 specific, well-supported and ready; 75–89 credible but concrete repairs needed; 60–74 material mismatch; below 60 requires restructuring. Explain deductions with scene IDs and evidence. Do not produce a score from follower count. Low effort means existing people/location/props; Medium adds setup or several inserts; High involves demanding effects, travel or complex staging. Brand-safe means editorial review passed under the given brief, not legal certification. Block unsupported claims and fictitious personal experience before delivery.

Review every alternative for:
- Creator: actual hook/voice/edit grammar, solo/ensemble attribution, narrative interruptibility, sponsor transition, credible topic, appropriate duration.
- Brand: objective, acceptable format, key messages, concrete product features in dialogue/actions, tone, mandatory/forbidden items, accurate product use, CTA mapped to goal.
- Execution: actual words to speak, shootable actions, complete organic portions, continuous timing with pauses, practical production checklist.
- Originality: distinct premises rather than paraphrased hooks; new ideas not misreported as observed behavior.

Save `analysis/reviews.json` keyed by variation ID:

```json
{"v1":[
 {"reviewer":"Codex creator pass","mode":"separate_pass","style_match":88,"brand_alignment":85,"production_level":"Low","brand_safe":true,"notes":"s1 uses the evidenced comparison hook; s3 should reserve two seconds for the CTA."},
 {"reviewer":"Codex brand pass","mode":"separate_pass","style_match":86,"brand_alignment":90,"production_level":"Low","brand_safe":true,"notes":"s2 demonstrates the confirmed feature, with no unsourced performance claim; brand and CTA are explicit."}
]}
```

Include all IDs, apply with `review --script JOB/script.json --reviews JOB/analysis/reviews.json`. It averages style/brand scores, computes match, aggregates production effort and ANDs brand safety, ranks descending and recommends one. The reviewer notes and provenance appear in exports. The command only aggregates supplied reviews; it does not perform reasoning. Never fill missing scores with success defaults. Re-review revised content; stale review fingerprints fail validation.
