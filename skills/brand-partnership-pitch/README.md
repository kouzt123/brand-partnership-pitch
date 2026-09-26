# Brand Partnership Pitch skill

Use `$brand-partnership-pitch` with a creator channel and brand requirement to produce creator-matched scripts, black-and-white storyboards using actual host reference frames, and editable documents.

Codex with built-in imagegen is recommended. Other agents need image viewing, local execution and a reference-image-capable generator or a user-configured third-party image API. See [compatibility](references/agent-compatibility.md). No OpenRouter is used.

Read [SKILL.md](SKILL.md), [operations](references/operations.md), and [data contract](references/data-contract.md). Keep the whole folder intact. Credentials and generated jobs stay outside this distributable directory.

```bash
python scripts/brand_pitch.py doctor
python -m unittest discover -s tests -v
python scripts/brand_pitch.py validate --script examples/script.json
```

Installation and bilingual usage instructions are in the [repository](https://github.com/kouzt123/brand-partnership-pitch). Source code is MIT; bundled fonts retain their own OFL license.
