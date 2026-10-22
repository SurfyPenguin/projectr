# src/engine/whiteboard_cv.py
import base64
import json
import os

import cv2
import numpy as np


class WhiteboardPreprocessor:
    def __init__(self, config_path: str = "calibration_config.json"):
        self.config_path = config_path
        self.board_corners = self._load_corners()

    def _load_corners(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = json.load(f)
                return np.array(data["corners"], dtype="float32")
        return None

    def set_warp(self, enabled: bool) -> None:
        """Opt in to the stored homography; new frames are never warped implicitly."""
        self.board_corners = self._load_corners() if enabled else None

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Automatically orders 4 clicked points into: [top-left, top-right, bottom-right, bottom-left]."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum
        rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # Top-right has smallest difference
        rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest difference
        return rect

    def calibrate_interactively(self, image: np.ndarray) -> np.ndarray:
        """Opens a GUI window allowing the user to click the 4 corners of the whiteboard."""
        clicked_points = []
        display_img = image.copy()

        # Resize for screen display if the photo is huge (e.g., 4K phone photo)
        h, w = display_img.shape[:2]
        scale = 1280 / w if w > 1280 else 1.0
        if scale < 1.0:
            display_img = cv2.resize(display_img, (int(w * scale), int(h * scale)))

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
                # Map back to original image resolution
                orig_x, orig_y = int(x / scale), int(y / scale)
                clicked_points.append([orig_x, orig_y])
                cv2.circle(display_img, (x, y), 8, (0, 255, 0), -1)
                cv2.putText(
                    display_img,
                    f"P{len(clicked_points)}",
                    (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow(
                    "Calibrate Whiteboard (Click 4 Corners, then press ANY KEY)",
                    display_img,
                )

        print("\n[CALIBRATION] Click the 4 corners of the whiteboard in any order.")
        cv2.imshow(
            "Calibrate Whiteboard (Click 4 Corners, then press ANY KEY)", display_img
        )
        cv2.setMouseCallback(
            "Calibrate Whiteboard (Click 4 Corners, then press ANY KEY)", mouse_callback
        )
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        if len(clicked_points) != 4:
            raise ValueError("You must click exactly 4 corners to calibrate.")

        ordered = self._order_points(np.array(clicked_points, dtype="float32"))
        self.board_corners = ordered

        with open(self.config_path, "w") as f:
            json.dump({"corners": ordered.tolist()}, f, indent=4)
        print(f"[INFO] Saved whiteboard calibration to {self.config_path}")
        return ordered
    
    def process_whiteboard(
        self, frame: np.ndarray, out_width=1920, out_height=1080
    ) -> np.ndarray:
        """Runs perspective warp + LAB illumination normalization."""
        # 1. Perspective Warp
        if self.board_corners is not None:
            dst = np.array(
                [
                    [0, 0],
                    [out_width - 1, 0],
                    [out_width - 1, out_height - 1],
                    [0, out_height - 1],
                ],
                dtype="float32",
            )
            matrix = cv2.getPerspectiveTransform(self.board_corners, dst)
            warped = cv2.warpPerspective(frame, matrix, (out_width, out_height))
        else:
            warped = frame.copy()

        # 2. Remove Fluorescent Glare & Boost Marker Contrast
        lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)

        # Estimate background whiteboard illumination
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))
        bg_illumination = cv2.morphologyEx(l_channel, cv2.MORPH_CLOSE, kernel)

        # Normalize lighting hotspot
        norm_l = cv2.divide(l_channel, bg_illumination, scale=255)

        # Apply mild sharpening so thin marker lines pop from 15 feet away
        merged = cv2.merge([norm_l, a, b])
        clean_bgr = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return clean_bgr

    def extract_clean_diagram(self, frame: np.ndarray, bbox: list) -> str:
        """
        Crops [ymin, xmin, ymax, xmax] (normalized 0-1000 coordinates from Gemini),
        cleans whiteboard background into pure white, and returns a base64 PNG string.
        """
        h, w = frame.shape[:2]
        ymin, xmin, ymax, xmax = bbox

        # Convert 0-1000 normalized coordinates to pixel coordinates with a small 2% padding
        pad_y, pad_x = int(h * 0.02), int(w * 0.02)
        y1 = max(0, int((ymin / 1000.0) * h) - pad_y)
        x1 = max(0, int((xmin / 1000.0) * w) - pad_x)
        y2 = min(h, int((ymax / 1000.0) * h) + pad_y)
        x2 = min(w, int((xmax / 1000.0) * w) + pad_x)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""

        # Convert to grayscale and isolate marker ink from whiteboard background
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Adaptive thresholding turns uneven grey board into pure white (255) and ink into crisp black (0)
        clean_sketch = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )

        _, buffer = cv2.imencode(".png", clean_sketch)
        b64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"
