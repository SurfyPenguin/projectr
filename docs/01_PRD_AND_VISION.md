# 01. Product Requirements & Vision

## 1. Problem Statement
In engineering, mathematics, and physics lectures, professors write complex derivations, matrices, tables, and diagrams on physical whiteboards. 
- Students in the back row struggle with glare, small handwriting, and faded markers.
- Students spend all their mental energy frantically copying the board before it gets erased rather than understanding the lecture.
- Traditional OCR (e.g., Tesseract) fails on 2D spatial mathematical notation (fractions, matrices, integrals).

## 2. Core Solution
A hardware-software pipeline:
`Input Interface (Camera / Photo / Live Feed) ---> [Main Component: CV + VLM LaTeX Engine] ---> Output Interface (HDMI Classroom Projector + Live Student Mobile Sync)`

## 3. Target Hardware Deployment
- **Edge I/O Node (Classroom):** Raspberry Pi 5 connected to a 4K USB camera, a physical GPIO push-button on the podium, and the classroom HDMI projector (booted into Chromium Kiosk Mode).
- **Compute Offloading:** Because a Raspberry Pi cannot run heavy Vision-Language Models locally at low latency, inference is routed to Cloud VLMs (`gemini-2.5-flash`) with automatic failover to a Local LAN GPU Worker (laptop/lab PC running Ollama on the same Wi-Fi network).

## 4. Key Applications
1. **Live Classroom Projection:** Projects crisp, high-contrast typeset equations onto the classroom screen alongside the physical board.
2. **Instant Lecture Notes (QR Sync):** Students scan a QR code on the projector to view a live-updating Google Slides-style deck on their phones, with 1-click `.tex` copy (for Overleaf) and multi-page PDF export.
3. **Corporate & Technical Meetings:** Converts brainstorming whiteboard sessions (tables, system architecture graphs, flowcharts) into structured Markdown, Mermaid.js diagrams, and clean figures.
4. **Future Extensions:** Auto-save before duster erase, symbolic math step-by-step error checking (`SymPy`), and math-to-speech accessibility for visually impaired students.