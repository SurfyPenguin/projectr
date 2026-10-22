# 03. Architecture & Design Decisions (ADR Log)

## ADR-01: Avoiding Pure Binarization Before VLM Inference
- **Context:** Classic OCR pipelines binarize images into strict black-and-white pixels.
- **Decision:** Use LAB color-space luminance division (`cv2.divide` against a `MORPH_CLOSE` background kernel) for main board transcription, reserving hard adaptive thresholding only for cropped display figures.
- **Rationale:** Vision Transformers rely on subtle grayscale anti-aliasing along pen strokes to distinguish ambiguous characters (e.g., handwritten `5` vs `S`, or $\alpha$ vs `2`)[cite: 12, 13].

## ADR-02: Protecting LaTeX Matrices from HTML/Markdown Line-Break Corruption
- **Bug Encountered:** Replacing `\\` with `<br>` in JavaScript broke matrix rendering (`\begin{bmatrix} a & b \\ c & d \end{bmatrix}`), causing KaTeX to abort and dump raw `$...$` strings onto the slide[cite: 2].
- **Decision:** Use a 4-stage rendering pipeline in JS (`renderMarkdownWithMath`):
  1. Extract all `$$...$$` and `$...$` blocks into an array and replace them with `@@MATH_BLOCK_N@@` tokens.
  2. Run `marked.parse()` on the surrounding Markdown text.
  3. Restore the untouched `@@MATH_BLOCK_N@@` strings.
  4. Execute `renderMathInElement()` via KaTeX[cite: 3].

## ADR-03: In-Place Slide Recapture with Temperature Escalation
- **Context:** If the VLM misreads a character or someone walks in front of the camera, clicking `capture` again creates a duplicate new slide. Also, retrying with `temperature=0.0` on a static image yields the exact same deterministic mistake.
- **Decision:** Added a `recapture` button (and `R` keyboard shortcut) that passes `replace_index: currentIndex` to `/api/scan`. When `retry=True`, the engine bumps temperature from `0.0` to `0.3`, appends a verification prompt, overwrites `LECTURE_SLIDES[replace_index]` in place, and broadcasts `update_latex_slide`.

## ADR-04: Fixing Image Selection & Stale Calibration Cropping Bugs
- **Bug Encountered:** Changing the image file still produced identical or hallucinated output (e.g., cropped Java code snippets)[cite: 7, 8].
- **Root Causes:**
  1. `find_test_image()` matched `*.jpg` before `*.jpeg`, repeatedly grabbing `debug_flattened_cleaned.jpg`.
  2. Applying `calibration_config.json` corner coordinates from Image A onto Image B (different resolution/framing) warped Image B into an empty corner patch.
- **Decision:** 
  - Excluded `debug_*` files from `list_available_images()`.
  - Added a live file selector dropdown (`#image-select`) in the projector toolbar[cite: 9].
  - Stored `image_path` per slide so `recapture` knows which source image belongs to which slide.
  - Disabled 4-corner homography (`use_warp=False`) by default unless explicitly calibrated for a fixed camera mount.

## ADR-05: Semantic Corner Watermark & Logo Filtering
- **Bug Encountered:** When scanning a whiteboard with a projected aptitude problem (`image_730b36.jpg`), the model transcribed the corner institutional watermark (`FACE`) at the bottom of the slide[cite: 10, 11].
- **Decision:** Added a non-aggressive semantic rule to the system prompt: omit isolated corner brand logos/emblems and projector toolbar icons unrelated to the academic problem, with a safety fallback (*"If unsure whether text is part of the lesson, always include it"*).

## ADR-06: Distinguishing Bordered Tables from Freehand Diagrams
- **Bug Encountered:** A handwritten memory block table (`Block no | Location` with grid lines) was transcribed both as borderless text and tagged as `@@DIAGRAM: [185, 156, 444, 354]@@`[cite: 12, 13].
- **Decision:** Instructed the prompt that tabular grids with rows/columns must be formatted as standard Markdown tables (`| Col1 | Col2 |`) and strictly excluded from `@@DIAGRAM@@` bounding box tags.