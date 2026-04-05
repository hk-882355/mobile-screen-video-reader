# Changelog

# 0.1.8

- Improve PyPI manual-release guidance in README to match workflow secret naming (`PYPI_API_TOKEN`)
- Clarify manual dispatch behavior and publish toggle in release workflow docs

# 0.1.7

- Move implementation into package module (`mobile_screen_video_reader.app`) so
  non-editable installs can run the console script correctly.
- Keep `scripts/mobile_screen_video_reader.py` as a compatibility wrapper.
- Update tests to target packaged app module for import stability.

## 0.1.6

- Add `--review-prompt` as the preferred prompt filename option for sequence review mode.
- Keep `--mimic-prompt` as a deprecated compatibility alias.
- Emit both `sequence_review` and legacy `mimic` manifest keys, with identical values.
- Add tests for prompt resolution logic and sequence-review manifest output.
- Use timezone-aware UTC timestamp generation for manifest metadata.

## 0.1.5

- Add mode validation and basic metadata checks.
- Improve extraction and transcription behavior for CLI usage.
- Add default prompt output (`codex_review_prompt.md`) and sequence-style prompt path configuration.
