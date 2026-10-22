# 02. System Architecture & Data Flow

## 1. End-to-End Pipeline

```text
[Image / Camera Frame]
       │
       ▼
[src/whiteboard_cv.py : WhiteboardPreprocessor]
  ├─ Optional 4-Point Perspective Homography (flattens angled camera views)
  ├─ LAB Color-Space Morphological Closing (removes overhead tube-light glare)
  └─ Adaptive Gaussian Thresholding (crops & cleans freehand diagrams into crisp black-on-white figures)
       │
       ▼
[src/latex_engine.py : LatexConverterEngine]
  ├─ Tier 1: Gemini 2.5 Flash (temperature=0.0 for initial scan, 0.3 for retry/recapture)
  ├─ Tier 2: Gemini 2.5 Flash-Lite (instant failover on HTTP 503 high-demand spikes)
  ├─ Tier 3: Local LAN Ollama Server (http://<LAN_IP>:11434/api/chat running qwen2.5vl:7b)
  └─ Post-Processor (`_extract_diagrams`): Separates prose/math/tables from Mermaid & BBox diagram tags
       │
       ▼
[app_server.py : Flask + Socket.IO Server]
  ├─ Stores chronological slide deck in `LECTURE_SLIDES` (tracks `slide_num`, `timestamp`, `image_path`, `latex`, `diagrams`)
  ├─ Emits `new_latex_slide` (on Capture) or `update_latex_slide` (on Recapture)
  └─ Generates dynamic LAN QR code (`http://<LAN_IP>:5000/student`)
       │
       ├──► [templates/projector.html] (16:9 Dark Mode HDMI Kiosk View)
       └──► [templates/student_notes.html] (Google Slides Filmstrip + White Canvas Mobile/Laptop View)