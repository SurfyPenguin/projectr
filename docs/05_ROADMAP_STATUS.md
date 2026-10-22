# 05. Project Roadmap & Build Status

## Completed Milestones
- [x] **Track 1: Core Vision & Preprocessing (`src/engine/whiteboard_cv.py`)**
  - Interactive 4-corner mouse calibration (`calibration_config.json`)
  - LAB color-space glare removal and contrast normalization
  - Adaptive thresholding diagram cropper (`extract_clean_diagram`)
- [x] **Track 1: VLM LaTeX Engine (`src/engine/latex_engine.py`)**
  - Multi-line math, matrix, and prose transcription
  - Cloud failover (`gemini-2.5-flash` -> `gemini-2.5-flash-lite`)
  - Diagram extraction pipeline (`_extract_diagrams` for Mermaid & BBox crops)
  - Watermark suppression & Markdown table enforcement
- [x] **Track 2: Real-Time Projector & Student Web App (`app_server.py`, `templates/`)**
  - WebSocket broadcast for `new_latex_slide` and in-place `update_latex_slide` (`recapture`)
  - Dynamic LAN IP detection and QR code generation
  - Cobalt/Google Slides minimal UI with filmstrip navigation, `.tex` copy, and multi-page PDF print view
- [x] **Modular Pipeline Refactor (`src/engine/`, `src/core/`, `src/inputs/`, `src/outputs/`)**
  - `WhiteboardEngine.process()` isolates CV + VLM from Flask, sockets, and deck state
  - `SlideDeck` + `ScanService` replace the global `LECTURE_SLIDES` and inline route logic
  - Pluggable `FrameSource` / `OutputSink` adapters with `HttpTrigger`, `KeyboardTrigger`, and `GpioTrigger` stub
  - Unit + Flask/Socket.IO integration tests with fake engine and recording sinks

## Pending Milestones (Next Up)
- [ ] **Local LAN Inference Worker Integration:** Test end-to-end offline failover to Ollama (`qwen2.5vl:7b`) running on laptop LAN IP.
- [ ] **Live Webcam Stream Capture:** `LiveCameraSource` exists; add a `"live_camera"` option to the toolbar `<select>` dropdown and wire it in `app_server.create_app()`.
- [ ] **Track 3: Raspberry Pi 5 Hardware & Kiosk Mode:**
  - GPIO physical button script (Short press = Capture, Long press = Recapture) + status LEDs.
  - Linux systemd service + Chromium `--kiosk` auto-boot script for HDMI projection.
- [ ] **Bonus Viva Features:**
  - Auto-save before whiteboard erase (frame-differencing motion trigger).
  - Inline `.tex` quick-edit drawer in the toolbar for manual 1-character fixes.