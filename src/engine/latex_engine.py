# src/engine/latex_engine.py
import os
import re
from typing import Optional

import cv2
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from src.core.models import Diagram, EngineResult

load_dotenv()


class LatexConverterEngine:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("Missing GEMINI_API_KEY. Check your .env file.")
        self.client = genai.Client(api_key=key)
        self.cloud_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    def _extract_diagrams(self, raw_text: str, cv_frame: np.ndarray, preprocessor=None) -> tuple[str, list]:
        """Strips Mermaid blocks and @@DIAGRAM@@ tags from text and returns them as a separate list."""
        diagrams = []

        # 1. Extract ```mermaid ... ``` blocks
        def mermaid_replacer(match):
            code = match.group(1).strip()
            diagrams.append(Diagram(
                type="mermaid",
                label=f"FIG 0{len(diagrams) + 1}",
                content=code
            ))
            return ""

        cleaned = re.sub(r"```mermaid\s*([\s\S]+?)```", mermaid_replacer, raw_text)

        # 2. Extract @@DIAGRAM: [ymin, xmin, ymax, xmax]@@ tags
        def crop_replacer(match):
            coords_str = match.group(1)
            try:
                bbox = [int(x.strip()) for x in coords_str.split(",")]
                if len(bbox) == 4 and preprocessor is not None:
                    b64_img = preprocessor.extract_clean_diagram(cv_frame, bbox)
                    if b64_img:
                        diagrams.append(Diagram(
                            type="image",
                            label=f"FIG 0{len(diagrams) + 1}",
                            content=b64_img
                        ))
            except Exception as e:
                print(f"[WARN] Diagram crop failed: {e}")
            return ""

        cleaned = re.sub(r"@@DIAGRAM:\s*\[(\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+)\]@@", crop_replacer, cleaned)
        cleaned = re.sub(r"```(?:latex|tex|markdown)?\n?(.*?)\n?```", r"\1", cleaned, flags=re.DOTALL)
        return cleaned.strip(), diagrams

    def convert(self, cv_frame: np.ndarray, retry: bool = False, preprocessor=None) -> EngineResult:
        pil_img = Image.fromarray(cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB))

        prompt = (
            "You are an automated classroom whiteboard transcription engine.\n"
            "Transcribe everything written on this whiteboard into clean Markdown with LaTeX math.\n"
            "Strict Rules:\n"
            "1. Output ONLY raw content (never wrap the whole response in ```markdown or ```latex codeblocks).\n"
            "2. Format headings, bullet points, and labels like **(iii.) Identity:** using standard Markdown (**bold**, - bullets).\n"
            "3. TABLES & ARRAYS: If the board contains a table, memory block grid, or tabular rows/columns with borders, "
            "format it as a proper Markdown Table (using | Col1 | Col2 | syntax). Do NOT tag tables as @@DIAGRAM@@.\n"
            "4. Wrap inline math/arrows in single $...$ (e.g. $\\rightarrow$, $\\leftarrow$) and standalone equations/matrices in $$...$$.\n"
            "5. Keep English words OUTSIDE of $...$ math delimiters.\n"
            "6. Omit obvious corner brand logos, projector watermarks, or partial cut-off tables on an adjacent screen.\n"
            "7. DIAGRAMS: Only for actual non-tabular drawings:\n"
            "   - For node/edge graphs, trees, or flowcharts, output a ```mermaid ... ``` block at the very end.\n"
            "   - For freehand geometric/physics/circuit sketches (NOT tables or text boxes), output its bounding box "
            "at the very end in this exact format: @@DIAGRAM: [ymin, xmin, ymax, xmax]@@ (using 0-1000 normalized coordinates)."
        )

        if retry:
            prompt += (
                "\n8. RETRY MODE: Carefully re-examine handwritten numbers vs letters (e.g. '5' vs 'S', 'Location' vs 'Ladin') "
                "and table alignments."
            )

        temp = 0.3 if retry else 0.0
        last_err = None

        for model_name in self.cloud_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[pil_img, prompt],
                    config=types.GenerateContentConfig(temperature=temp)
                )
                clean_text, diagrams = self._extract_diagrams(response.text, cv_frame, preprocessor)
                return EngineResult(
                    status="success",
                    latex=clean_text,
                    diagrams=diagrams,
                    error=None
                )
            except Exception as e:
                print(f"[WARN] {model_name} failed: {e}")
                last_err = str(e)

        return EngineResult(status="error", latex=None, diagrams=[], error=last_err)
