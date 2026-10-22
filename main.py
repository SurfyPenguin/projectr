# main_track1.py
import cv2
import argparse
from src.engine.whiteboard_cv import WhiteboardPreprocessor
from src.engine.latex_engine import LatexConverterEngine


def main():
    parser = argparse.ArgumentParser(
        description="Track 1: Whiteboard Vision & LaTeX Engine"
    )
    parser.add_argument(
        "--image",
        type=str,
        default="test_images/board1.jpeg",
        help="Path to whiteboard image",
    )
    parser.add_argument(
        "--recalibrate", action="store_true", help="Force 4-corner mouse calibration"
    )
    args = parser.parse_args()

    # 1. Load Image
    frame = cv2.imread(args.image)
    if frame is None:
        print(
            f"[ERROR] Could not load image at '{args.image}'. Put a whiteboard photo there first!"
        )
        return

    # 2. Initialize Preprocessor & Calibrate Corners if needed
    preprocessor = WhiteboardPreprocessor()
    if preprocessor.board_corners is None or args.recalibrate:
        preprocessor.calibrate_interactively(frame)

    # 3. Flatten Perspective & Remove Glare
    print("[INFO] Flattening perspective and removing whiteboard glare...")
    cleaned_board = preprocessor.process_whiteboard(frame)

    # Save debug output so you can show "Before vs After" in your project report!
    cv2.imwrite("test_images/debug_flattened_cleaned.jpg", cleaned_board)
    print(
        "[INFO] Saved preprocessed board to 'test_images/debug_flattened_cleaned.jpg'"
    )

    # Show side-by-side preview (press any key to continue to OCR)
    preview = cv2.resize(cleaned_board, (960, 540))
    cv2.imshow("Cleaned Whiteboard (Press ANY KEY to convert to LaTeX)", preview)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 4. Run LaTeX Conversion
    print("[INFO] Sending cleaned whiteboard to LaTeX Engine...")
    engine = LatexConverterEngine()
    result = engine.convert(cleaned_board)

    if result.status == "success":
        print("\n================ GENERATED LATEX ================")
        print(result.latex)
        print("=================================================\n")

        with open("output_notes.tex", "w", encoding="utf-8") as f:
            f.write(result.latex)
        print("[SUCCESS] Saved raw LaTeX to 'output_notes.tex'")
    else:
        print(f"[ERROR] Conversion failed: {result.error}")


if __name__ == "__main__":
    main()
