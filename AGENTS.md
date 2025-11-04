# Repository Guidelines

## Project Structure & Module Organization
- `record.py`: Standalone screen, webcam, and audio capture. Keep device constants (`AUDIO_DEVICE`, `WEBCAM_DEVICE`) local to each deployment.
- `client.py`: Long-running recorder client. Maintains global `subprocess.Popen` handles for paired ffmpeg sessions.
- `master.py`: Simple TCP command dispatcher for `client.py`. Update the `CLIENTS` list per site.
- `client_launcher.bat`: Windows helper to daemonize `client.py`.
- `pyproject.toml` and `uv.lock`: Package metadata and dependency lock managed by uv; edit via `uv add` to keep them consistent.

## Build, Test, and Development Commands
- `uv sync`: Install runtime and dev dependencies (Python 3.12+, ffmpeg must be installed separately).
- `uv run record.py`: Validate standalone capture and timestamped output under the current device settings.
- `uv run client.py`: Launch a client node; combine with `uv run master.py` on the controller to exercise distributed start/stop.
- `uv run ruff check .`: Static lint pass; run before submitting changes to keep style consistent.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation and descriptive snake_case for functions; keep globals that represent configuration in SCREAMING_SNAKE_CASE.
- Maintain direct `ffmpeg` argument lists rather than shell strings, and structure new logic around small helpers (see `build_cmds()` in `client.py`) to ease testing.
- Preserve user-facing console cues (emoji prefixes and short Japanese prompts) for operator clarity.

## Testing Guidelines
- Manual verification remains essential: confirm expected `.mp4` artifacts and synchronized stop/start across nodes after code changes.
- When adding automation, place tests in a new `tests/` package and exercise them with `uv run pytest`; prefer fixtures that simulate socket traffic without requiring hardware.
- Document device matrix or special setup steps in PRs so other contributors can reproduce the scenario.

## Commit & Pull Request Guidelines
- Existing history favors concise present-tense messages (e.g., `Update README.md`, `fix client.py`). Continue with imperative summaries and mention the touched module when helpful.
- Each PR should describe scope, list manual test commands (`uv run ...`), and call out environment specifics such as device names or Windows version.
- Link related issues when available, attach screenshots or logs for UI/output changes, and wait for at least one peer review before merging.
