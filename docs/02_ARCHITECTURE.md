# 02. System Architecture & Data Flow

## 1. Pipeline Shape

```text
 INPUT INTERFACE              ENGINE                     OUTPUT INTERFACE
 ───────────────              ──────                     ────────────────
 FrameSource ──┐                                    ┌── OutputSink
               │        WhiteboardEngine            │     ├─ SocketIOSink
 Trigger ──────┼──► ScanService ──► (CV + VLM) ──► SlideDeck ──► ├─ ConsoleSink
               │        │   ▲                       │     └─ (your adapter)
               │        └───┴── publishes events ──┘
```

The engine is a pure function of a frame: **image/frame in → structured result
out**. It has no knowledge of Flask, Socket.IO, templates, file pickers, GPIO,
QR codes, or deck state.

## 2. Module Map

| Layer | Path | Responsibility |
|---|---|---|
| Engine | `src/engine/whiteboard_cv.py` | Perspective homography (opt-in), LAB glare removal, adaptive-threshold diagram crops |
| Engine | `src/engine/latex_engine.py` | Gemini 2.5 Flash → Flash-Lite failover, prompts, retry temperature, `_extract_diagrams` |
| Engine | `src/engine/pipeline.py` | `WhiteboardEngine.process(frame, retry, use_warp)`: preprocess → transcribe |
| Core | `src/core/models.py` | `Frame`, `Slide`, `Diagram`, `EngineResult`, `ScanOutcome` |
| Core | `src/core/interfaces.py` | `FrameSource`, `EnginePort`, `OutputSink`, `StatusListener` protocols |
| Core | `src/core/slide_deck.py` | Replaces `LECTURE_SLIDES`; owns `slide_num`, timestamps, `add`/`replace` |
| Core | `src/core/scan_service.py` | Orchestrates source → engine → deck → sinks |
| Inputs | `src/inputs/file_source.py` | `FileImageSource` + `list_available_images()` (skips `debug_*`) |
| Inputs | `src/inputs/upload_source.py` | `UploadSource` for in-memory bytes |
| Inputs | `src/inputs/camera_source.py` | `LiveCameraSource` (`cv2.VideoCapture`) |
| Inputs | `src/inputs/triggers.py` | `HttpTrigger`, `KeyboardTrigger`, `GpioTrigger` stub (short press = capture, long press = recapture) |
| Outputs | `src/outputs/socketio_sink.py` | Broadcasts `new_latex_slide`, `update_latex_slide`, `scan_status` |
| Outputs | `src/outputs/console_sink.py` | Transport-free reference sink |
| Web | `app_server.py` | `create_app()` composition root + thin routes; QR/LAN helpers |
| CLI | `main.py` | Composition root with no Flask: `FileImageSource → ScanService → ConsoleSink` |

## 3. Capture Control Flow

1. A trigger (HTTP button, `R`/`C` key, GPIO) asks `ScanService` to `capture` or
   `recapture`. Triggers never touch the engine.
2. `ScanService` emits `scan_status: scanning` and calls `source.get_frame()`.
3. `WhiteboardEngine.process(frame, retry, use_warp)` preprocesses and transcribes.
4. On success, `SlideDeck.add()` (capture) or `SlideDeck.replace(index)` (recapture)
   produces the authoritative `Slide`.
5. Each registered `OutputSink` receives `on_new_slide` or `on_update_slide`.
6. `ScanOutcome` travels back to the HTTP adapter as JSON.

A recapture keeps `slide_num`, refreshes `timestamp`, and overwrites the same
index. `retry=True` bumps the engine temperature from `0.0` to `0.3` and appends
the verification prompt (unchanged behaviour).

## 4. Engine Contract

```python
result = engine.process(frame, retry=False, use_warp=False)
# EngineResult(status, latex, diagrams, error)
```

- `use_warp=True` is the **only** way `calibration_config.json` is applied.
- The engine never mutates deck state and never emits events.
- Diagram extraction still strips Mermaid blocks and `@@DIAGRAM@@` bounding boxes
  before returning the Markdown/LaTeX body.

> Note: `docs/01_PRD_AND_VISION.md` and `AGENTS.md` describe a third Ollama LAN
> tier. The current code ships the two Gemini tiers only; adding tier 3 is a
> model-behaviour change and is intentionally out of scope for the refactor.

## 5. Stable Interfaces

HTTP:

- `GET /` → projector view (deck + image list + QR)
- `GET /student` → student notes view
- `GET /api/images` → `{"images": [...]}` (debug artifacts excluded)
- `POST /api/scan` → accepts `image_path`, `replace_index`, `use_warp`;
  returns `{"status", "slide", "replaced"}` or `{"status", "message"}`

Socket.IO:

- `new_latex_slide` (slide payload on capture)
- `update_latex_slide` (`{index, slide}` on recapture)
- `scan_status` (`{status, mode|message}`)

## 6. Composition Roots

- Web: `app_server.create_app()` builds the deck, engine, `ScanService`, the
  `SocketIOSink`, and the `HttpTrigger`. Tests inject fakes here.
- CLI: `main.py` builds the engine, deck, `ScanService`, and `ConsoleSink`.

## 7. How to Add a New Input

Create one adapter that satisfies `FrameSource` (`source_id` + `get_frame`),
then wire it. No engine changes are required.

```python
# 1. src/inputs/camera_source.py already ships LiveCameraSource.
from src.inputs.camera_source import LiveCameraSource

# 2. In your composition root (app_server.create_app or a route):
camera = LiveCameraSource(0)
outcome = scan_service.capture(camera)      # or recapture(index, camera)
```

For an entirely new source, implement two members:

```python
class ClipboardSource:
    source_id = "clipboard"
    def get_frame(self) -> Frame:
        return Frame(image=decode(paste()), source_id=self.source_id)
```

## 8. How to Add a New Output

Implement `on_new_slide` / `on_update_slide` (and optionally `on_status`), then
register it with one line.

```python
# src/outputs/telegram_sink.py
class TelegramSink:
    def __init__(self, bot, chat_id):
        self.bot, self.chat_id = bot, chat_id
    def on_new_slide(self, slide):
        self.bot.send_message(self.chat_id, f"Slide {slide.slide_num}\n{slide.latex}")
    def on_update_slide(self, index, slide):
        self.bot.send_message(self.chat_id, f"Slide {index + 1} updated")
```

```python
# app_server.create_app()
scan_service.add_sink(TelegramSink(bot, chat_id))
```

A Markdown-file sink is equally valid: write `slide.to_dict()` or
`slide.latex` from `on_new_slide` and overwrite the file from `on_update_slide`.
