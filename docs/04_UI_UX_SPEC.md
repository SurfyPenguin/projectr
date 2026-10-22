# 04. UI/UX & Typography Specification

## 1. Visual Philosophy (`cobalt.tools` + Google Slides)
- **Zero Fluff:** No emojis, no marketing banners ("SmartBoard Live Projection"), and no "Board #1" card labels[cite: 3, 4, 6].
- **Sharp Geometry:** `border-radius: 0px` across all buttons, inputs, thumbnails, and slide containers[cite: 6].
- **Palette:**
  - Base App Chrome: `#09090b` (Pitch zinc black)
  - Surface / Controls: `#121214`
  - Hairline Borders: `1px solid #27272a`
  - Student Slide Canvas: `#ffffff` background with `#18181b` ink[cite: 5]
  - Projector Slide Canvas: `#09090b` background with `#e4e4e7` anti-aliased ink[cite: 6]

## 2. Typography & Halation Control
- **UI Chrome & Metadata:** Monospace (`JetBrains Mono`, `11px–12px`) for slide headers (`SLIDE 01`), timestamps (`01:55 AM`), and footers (`01 / 01`)[cite: 5, 6, 9].
- **Slide Body Unified Font (`KaTeX_Main`):**
  - *Problem:* Mixing sans-serif prose (`Inter`/`Segoe UI`) with KaTeX's Computer Modern serif equations created a jarring weight and x-height mismatch, worsened by white-on-black halation (irradiation illusion) on the projector[cite: 5, 6].
  - *Solution:* Set `.slide-body` and `#latex-content` to `font-family: 'KaTeX_Main', 'Latin Modern Roman', Georgia, serif;`, normalized `.katex` font-size from `1.21em` down to `1.02em`, and enabled `-webkit-font-smoothing: antialiased;`.

## 3. Adaptive Split-Screen Slide Layout
- **Text-Only Slides:** `.slide-main-area` uses `grid-template-columns: 1fr` (100% width)[cite: 5, 6, 10].
- **Diagram Slides (`.has-diagrams`):** Automatically splits into `62%` Left (Text/Math/Tables) and `38%` Right (`.diagram-sidebar`) separated by a `1px solid` vertical border.