# main.py
"""Headless composition root: the same core pipeline without Flask or sockets."""

import argparse

from src.core.scan_service import ScanService
from src.core.slide_deck import SlideDeck
from src.engine.pipeline import WhiteboardEngine
from src.inputs.file_source import FileImageSource
from src.outputs.console_sink import ConsoleSink


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Whiteboard image -> Markdown + LaTeX (no server)"
    )
    parser.add_argument(
        "--image",
        type=str,
        default="test_images/board1.jpeg",
        help="Path to whiteboard image",
    )
    parser.add_argument(
        "--use-warp",
        action="store_true",
        help="Apply the saved 4-corner homography (opt-in for a fixed camera mount)",
    )
    parser.add_argument(
        "--recalibrate",
        action="store_true",
        help="Click the 4 board corners before scanning (implies --use-warp)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Save debug_flattened_cleaned.jpg and show the cleaned frame",
    )
    parser.add_argument(
        "--save-tex",
        default="output_notes.tex",
        help="Where to write the raw LaTeX (empty string disables)",
    )
    args = parser.parse_args()

    engine = WhiteboardEngine()

    if args.recalibrate:
        import cv2

        frame = cv2.imread(args.image)
        if frame is None:
            raise SystemExit(f"[ERROR] Could not load image at '{args.image}'")
        engine.preprocessor.calibrate_interactively(frame)
        args.use_warp = True

    if args.preview:
        _preview(engine, args.image, use_warp=args.use_warp)

    deck = SlideDeck()
    service = ScanService(deck, engine)
    service.add_sink(ConsoleSink())

    outcome = service.capture(
        FileImageSource(args.image), use_warp=args.use_warp
    )
    if outcome.status != "success" or outcome.slide is None:
        raise SystemExit(f"[ERROR] Conversion failed: {outcome.error}")

    print("\n================ GENERATED LATEX ================")
    print(outcome.slide.latex)
    print("=================================================\n")

    if args.save_tex:
        with open(args.save_tex, "w", encoding="utf-8") as f:
            f.write(outcome.slide.latex)
        print(f"[SUCCESS] Saved raw LaTeX to '{args.save_tex}'")


def _preview(engine: WhiteboardEngine, image_path: str, *, use_warp: bool) -> None:
    """Dev-only before/after view; the debug_* file is ignored by the scanner."""
    import cv2

    frame = cv2.imread(image_path)
    if frame is None:
        return
    engine.preprocessor.set_warp(use_warp)
    cleaned = engine.preprocessor.process_whiteboard(
        frame, out_width=frame.shape[1], out_height=frame.shape[0]
    )
    cv2.imwrite("test_images/debug_flattened_cleaned.jpg", cleaned)
    preview = cv2.resize(cleaned, (960, 540))
    cv2.imshow("Cleaned Whiteboard (press any key)", preview)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
