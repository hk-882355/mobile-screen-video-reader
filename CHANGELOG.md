# Changelog

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

