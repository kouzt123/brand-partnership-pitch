# Installation

## Codex recommended

```bash
codex plugin marketplace add kouzt123/brand-partnership-pitch
codex plugin add brand-partnership-pitch@brand-partnership-pitch-marketplace
```

This repository has its own marketplace name so it can coexist with other plugin repositories. The marketplace currently pins the plugin to `v1.1.0`. Refresh/start a new Codex task after installation, then invoke `$brand-partnership-pitch`.

To update when a new release is available:

```bash
codex plugin marketplace upgrade brand-partnership-pitch-marketplace
codex plugin add brand-partnership-pitch@brand-partnership-pitch-marketplace
```

Check the active Codex environment exposes built-in imagegen and image viewing. Installing a skill does not grant those tools. No external image key is needed for the built-in path.

## Python and local tools

Use Python 3.10+; old Python can cause pip to install an obsolete yt-dlp. From a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r skills/brand-partnership-pitch/requirements.txt
# Optional local ASR and YouTube download:
python -m pip install -r skills/brand-partnership-pitch/requirements-transcription.txt
python skills/brand-partnership-pitch/scripts/brand_pitch.py doctor
```

FFmpeg/ffprobe, Poppler (`pdftoppm`) and headless LibreOffice are also needed for full local media/document work. Codex can use its bundled document runtime where available. Pass its verified `soffice` path when rendering; do not silently launch a desktop office app.

Set `APIFY_API_TOKEN` in your local environment if using Apify acquisition. Set `ELEVENLABS_API_KEY` only if choosing optional cloud transcription. Do not paste keys into a task or commit them. With local videos and existing subtitles, neither credential is required.

## Standalone skill or another agent

Copy the complete `skills/brand-partnership-pitch/` folder into the agent's supported skill directory. In Codex a project-local option is `.agents/skills/brand-partnership-pitch/`. Avoid duplicate plugin and standalone installations of the same skill.

Other agents must support local execution, image viewing and a reference-image-capable generator, or configure a third-party image API themselves. Follow [agent compatibility](skills/brand-partnership-pitch/references/agent-compatibility.md). There is no OpenRouter requirement or bundled universal image API adapter.

## Verify

```bash
python -m unittest discover -s skills/brand-partnership-pitch/tests -v
python scripts/security_check.py
python skills/brand-partnership-pitch/scripts/brand_pitch.py validate --script skills/brand-partnership-pitch/examples/script.json
```

Then ask the agent to use `$brand-partnership-pitch` with a real channel and brief. The example JSON is fictional structural test data, not a pre-analyzed channel.

## 中文

推荐按上方两条 Codex plugin 命令安装，然后开启新任务。调用名为 `$brand-partnership-pitch`。Codex 环境需要提供内置 imagegen 与看图能力；不需要额外图片 API Key。

其他 agent 可加载完整 skill 文件夹，但必须自带支持参考图的生图工具，或自行配置第三方图片 API。原始视频帧必须作为图片输入传递，不能只用人物文字描述替代。Python 与本地处理依赖见上方命令。Apify 和 ElevenLabs 的密钥由使用者在本地配置，仓库与 CI 均不包含这些凭据。
