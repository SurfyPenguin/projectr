# CLAUDE.md — Agent Guide

## Project
Whiteboard-to-LaTeX live projection system: a classroom whiteboard is captured,
preprocessed, transcribed by a vision-language model into Markdown + LaTeX, and
streamed to an HDMI projector and student phones over LAN.

## Architecture (post-refactor)

```
FrameSource + Trigger  ->  ScanService  ->  WhiteboardEngine  ->  SlideDeck  ->  OutputSink
   src/inputs/               src/core/         src/engine/         src/core/       src/outputs/
```

- `src/engine/` — CV + VLM only. `WhiteboardEngine.process(frame, retry, use_warp)`
  returns `EngineResult(status, latex, diagrams, error)`. No Flask, sockets,
  templates, file pickers, GPIO, QR, or deck state in this layer.
- `src/core/` — domain models (`models.py`), ports (`interfaces.py`),
  `SlideDeck` (replaces the old global `LECTURE_SLIDES`), and `ScanService`
  (source → engine → deck → sinks).
- `src/inputs/` — `FileImageSource` (skips `debug_*`), `UploadSource`,
  `LiveCameraSource`, and triggers (`HttpTrigger`, `KeyboardTrigger`,
  `GpioTrigger` stub). Triggers only call `ScanService`.
- `src/outputs/` — `SocketIOSink` (existing socket event names) and
  `ConsoleSink`.
- `app_server.py` — thin Flask factory (`create_app`) and routes. No business
  logic. `main.py` — headless composition root.

Environment: Python 3.11 (`uv`), Flask + Flask-SocketIO, OpenCV, google-genai,
python-dotenv, qrcode.

## Commands

```bash
uv run app_server.py          # projector: http://localhost:5000
uv run main.py --image test_images/board1.jpeg
uv run pytest -q
uv run ruff check .           # if ruff is available
```

## Guardrails (do not violate)

1. **KaTeX math protection:** never replace `\\` with `<br>`. Both templates
   extract `$$...$$` / `$...$` into `@@MATH_BLOCK_N@@` before `marked.parse()`
   and restore them afterwards.
2. **No blind calibration:** apply `calibration_config.json` only when
   `use_warp=True`. In the engine that is `WhiteboardPreprocessor.set_warp()`.
3. **Ignore debug artifacts:** the image scanner excludes `debug_*` files.
   `test_images/debug_flattened_cleaned.jpg` must never be listed or scanned.
4. **UI aesthetic:** zero emojis, `border-radius: 0`, `1px` hairline borders,
   JetBrains Mono metadata, `KaTeX_Main` slide body. Do not restyle the
   frontend during backend refactors.
5. **Model behaviour is frozen:** prompt text, watermark rule, table-vs-diagram
   rule, and failover order (`gemini-2.5-flash` → `gemini-2.5-flash-lite`) must
   not change structurally. Retry temperature stays `0.0` → `0.3`.
   The Ollama tier mentioned in the PRD is not implemented yet.
6. **Stable contracts:** keep `/`, `/student`, `/api/images`, `/api/scan`
   (`image_path`, `replace_index`, `use_warp`) and socket events
   `new_latex_slide`, `update_latex_slide`, `scan_status`.

## Adding a new input

Create a `FrameSource` (`source_id` property + `get_frame() -> Frame`) in
`src/inputs/`, then wire it in the composition root:

```python
scan_service.capture(LiveCameraSource(0))
```

Triggers are separate: they translate a button/key/HTTP request into a
`capture`/`recapture` call and never reach into the engine.

## Adding a new output

Implement `on_new_slide(slide)` and `on_update_slide(index, slide)` (optionally
`on_status`) in `src/outputs/`, then register one line:

```python
scan_service.add_sink(MySink())
```

## Docs
- `docs/01_PRD_AND_VISION.md` — product scope
- `docs/02_ARCHITECTURE.md` — module map, control flow, extension recipes
- `docs/03_DESIGN_DECISIONS.md` — ADRs and past bug root causes
- `docs/04_UI_UX_SPEC.md` — typography and halftone/halation rules
- `docs/05_ROADMAP_STATUS.md` — build status and Track 3 hardware plans
