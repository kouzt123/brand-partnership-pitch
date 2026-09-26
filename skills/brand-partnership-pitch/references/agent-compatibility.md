# Agent compatibility and image providers

## Recommended host: Codex

Use Codex with local command execution, image viewing and built-in imagegen available. Codex performs creator analysis, script writing and review; the image tool receives the actual reference frames. No separate image API key is needed for that built-in path. Tool access depends on the running Codex environment; installation alone does not grant image generation. This project has no OpenRouter dependency and does not require a separate text-model API.

## Other agents

Load this SKILL.md and keep its supporting folders intact. The agent must support local Python/FFmpeg execution, image inspection and file output. For illustrated scripts it also needs either:

1. A native image-generation/editing tool that accepts reference images; or
2. A third-party image-generation API configured and selected by the user, with real image-input support.

A text-only agent or text-to-image endpoint without image inputs cannot preserve the original host reference workflow. Do not silently replace the host with an invented person. If no compatible generator exists, finish the text work and mark illustration as incomplete.

## Provider-neutral handoff

`image-plan` outputs per-scene `prompt`, `aspect_ratio`, `referenced_image_paths`, reference provenance and suggested output path. These are generation instructions, not a running API integration. This release does not ship a universal third-party image client and makes no claim to support arbitrary vendor schemas.

For an explicitly configured API/tool:

- Verify its current official documentation supports reference images. Adapt those inputs to that provider's file upload, image URL or binary-image fields.
- Inspect the source frames. Send the actual images, not just their filenames or descriptions. Preserve the original host reference in every host scene; use earlier sketches additionally for continuity.
- Pass the same black-and-white line-art prompt and requested aspect ratio. Do not silently change models, invent a product UI, or switch to colored illustrations.
- Keep API credentials in the local environment/credential store. Send them only to the configured provider's authentication endpoint/headers, never in prompts or public artifacts. Tell the user which provider receives the creator frames and about its charging model before the first unconfigured upload.
- Set a per-job image/cost limit. Record successful outputs and provider request IDs locally. Do not automatically repeat an uncertain billed request.
- Save the resulting image into the private job folder, inspect identity/action/monochrome/no-text quality, then run the same `register-image --qa`, validation and document-export commands.

Apify handles acquisition; ElevenLabs is optional speech-to-text. Neither supplies storyboard reasoning or image generation. Local subtitle/ASR and local media inputs can avoid those external services where suitable.
