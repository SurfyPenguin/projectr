# Project Context: Whiteboard-to-LaTeX Live Projection System

## Quick Overview
An embedded Edge-AI classroom system that captures handwritten math, text, tables, and diagrams from a physical whiteboard, converts them into structured Markdown + LaTeX, projects them live over HDMI in a minimal presentation interface, and syncs slides in real-time to student smartphones via a LAN QR code.

## Tech Stack
- **Computer Vision (`src/engine/whiteboard_cv.py`):** OpenCV (`cv2`), NumPy, PIL. Handles 4-point perspective homography, LAB color-space morphological glare removal, and adaptive Gaussian thresholding for diagram crops.
- **Inference Engine (`src/engine/latex_engine.py`):** 3-Tier Cascade (tier 3 pending):
  1. Primary Cloud: `gemini-2.5-flash` (`google-genai` SDK)
  2. Secondary Cloud Failover (503 protection): `gemini-2.5-flash-lite`
  3. Offline LAN Compute Node: Ollama (`qwen2.5vl:7b`) via HTTP REST API
- **Engine Facade (`src/engine/pipeline.py`):** `WhiteboardEngine.process(frame, retry, use_warp)` — image in, `EngineResult` out.
- **Core (`src/core/`):** `SlideDeck` (replaces the global `LECTURE_SLIDES`), `ScanService` orchestrator, domain models, and ports (`FrameSource`, `OutputSink`, `EnginePort`).
- **Inputs (`src/inputs/`):** `FileImageSource`, `UploadSource`, `LiveCameraSource`; triggers (`HttpTrigger`, `KeyboardTrigger`, `GpioTrigger` stub) call `ScanService`, never the engine.
- **Outputs (`src/outputs/`):** `SocketIOSink` and `ConsoleSink`.
- **Backend & Real-Time Sync (`app_server.py`):** Flask + Flask-SocketIO + `qrcode`; thin `create_app()` wiring and routes only.
- **Frontend (`templates/projector.html`, `templates/student_notes.html`):** Vanilla JS, Socket.IO, `marked.js` (Markdown), `KaTeX` (Math), `mermaid.js` (Topological diagrams).

## Critical Engineering Guardrails (DO NOT VIOLATE)
1. **Never replace `\\` with `<br>` before KaTeX rendering:** Matrix environments (`\begin{bmatrix} a & b \\ c & d \end{bmatrix}`) require `\\` for row breaks. Always protect `$$...$$` and `$...$` blocks with placeholders (`@@MATH_BLOCK_N@@`) before running `marked.parse()`.
2. **Never apply `calibration_config.json` homography blindly to new test images:** Only warp perspective when `use_warp=True` is explicitly set for a fixed camera mount.
3. **Ignore `debug_*` files in `test_images/`:** The file scanner must filter out `debug_flattened_cleaned.jpg` so the engine never scans its own debug artifacts.
4. **Strict UI Aesthetic:** Follow a `cobalt.tools` + Google Slides minimal aesthetic. Zero emojis, zero rounded pill corners (`border-radius: 0`), `1px solid` borders, monospace metadata (`JetBrains Mono`), and unified `KaTeX_Main` serif typography inside the slide body.

## Documentation Index
- See `docs/01_PRD_AND_VISION.md` for project scope and classroom applications.
- See `docs/02_ARCHITECTURE.md` for pipeline data flow and LAN worker setup.
- See `docs/03_DESIGN_DECISIONS.md` for root-cause analyses of past bugs and why specific prompts/parsers exist.
- See `docs/04_UI_UX_SPEC.md` for typography, halation fixes, and split-screen diagram layouts.
- See `docs/05_ROADMAP_STATUS.md` for current build status and Track 3 hardware plans.