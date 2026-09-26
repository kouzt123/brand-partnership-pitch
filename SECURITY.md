# Credentials and release safety

No provider credential is shipped. Use local environment variables or a credential store for `APIFY_API_TOKEN`, optional `ELEVENLABS_API_KEY`, and any explicitly configured image-provider key. Never put credentials in the prompt, repository, example JSON, screenshots or shared document.

Runtime jobs belong outside the source checkout. Downloaded creator videos, real-person source frames, private briefs, transcripts, provider datasets, signed media URLs, cookies, logs and generated exports are not publication inputs. API authorization headers must only be sent to the selected provider. Local media downloads do not reuse provider authorization headers.

Before committing or releasing, run:

```bash
python scripts/security_check.py --self-test
python scripts/security_check.py
# After staging the intended files:
python scripts/security_check.py --staged
```

The scanner blocks common credential formats, literal secrets, developer home paths and runtime/private file classes. It prints file paths and finding types, never matching values. Automated scanning supplements a manual file-list and diff review; it cannot prove that arbitrary confidential prose is safe to publish. Inspect Git history before publishing existing commits. The initial release is a fresh source-only repository, not copied product history.

CI runs only offline tests and this scanner. Do not add live provider credentials to CI to make these checks pass. Never include a leaked key in a public issue. Revoke exposed credentials with their provider and use a private reporting channel where available.

The bundled font has a separate OFL license. Public creator media and private acceptance samples are excluded from the repository and are not licensed by this project's MIT license.
