"""
CADMentor Backend — Local FastAPI server for question parsing.

This server receives engineering drawing questions extracted from AutoCAD,
sends them to Google Gemini for structured entity extraction, validates
the response, and returns it as JSON.

Gemini is used ONLY for NLP extraction — it does NOT compute geometry.

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Environment:
    GEMINI_API_KEY  — Required. Your Google Gemini API key.
    Can be set in backend/.env or as a system environment variable.
"""

import json
import os
import re
import sys
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from dotenv import load_dotenv

# Add the project root to sys.path so we can import the geometry engine
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from geometry.engine import point_projection, line_projection, plane_projection

# Load .env file from the backend directory
load_dotenv()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cadmentor")


# ── Gemini Client Setup ──

from google import genai

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not _api_key:
    logger.warning(
        "GEMINI_API_KEY not set. The /parse endpoint will fail. "
        "Set it in backend/.env or as an environment variable."
    )
    _gemini_client = None
else:
    _gemini_client = genai.Client(api_key=_api_key)
    logger.info("Gemini client initialized successfully.")

# Model to use
GEMINI_MODEL = "gemini-3.1-flash-lite"


# ── System Prompt (STRICT — as specified) ──

SYSTEM_PROMPT = """You are a geometry entity extractor for engineering drawing problems.

Your ONLY job is to extract structured data from the problem statement.

You MUST NOT:
- calculate coordinates
- calculate projections
- assume missing values
- add information not explicitly stated

Return ONLY valid JSON.
No explanation. No markdown. No extra text.

Key rules:
- "position" refers to the FIRST endpoint (A or P) unless stated otherwise
- "length" in dimensions is always the TRUE LENGTH of the line/edge
- For lines: angle_to_hp = inclination to HP, angle_to_vp = inclination to VP
- "above HP" means above the Horizontal Plane
- "in front of VP" or "infront of VP" means in front of the Vertical Plane
- "below HP" means below the Horizontal Plane
- "behind VP" means behind the Vertical Plane

Schema:
{
  "shape": "point | line | plane | cone | cylinder | prism | pyramid | sphere | lamina",
  "shape_type": "pentagon | hexagon | square | rectangle | triangle | etc (if applicable)",,
  "dimensions": {},
  "position": {
    "above_hp": null,
    "below_hp": null,
    "infront_vp": null,
    "behind_vp": null,
    "on_hp": false,
    "on_vp": false
  },
  "inclination": {
    "angle_to_hp": null,
    "angle_to_vp": null, // Use this for BOTH surface inclination AND resting edge inclination to VP
    "angle_to_xy": null,
    "resting_element": null
  },
  "extra": {}
}"""


# ── FastAPI App ──

app = FastAPI(
    title="CADMentor Backend",
    description="Local server for parsing descriptive geometry questions via Gemini NLP + deterministic geometry",
    version="0.3.0",
)


# ── Request / Response Models ──


class ParseRequest(BaseModel):
    """The question text extracted from the AutoCAD drawing."""
    question: str


class PositionData(BaseModel):
    above_hp: Optional[float] = None
    below_hp: Optional[float] = None
    infront_vp: Optional[float] = None
    behind_vp: Optional[float] = None
    on_hp: bool = False
    on_vp: bool = False


class InclinationData(BaseModel):
    angle_to_hp: Optional[float] = None
    angle_to_vp: Optional[float] = None
    angle_to_xy: Optional[float] = None
    resting_element: Optional[str] = None


class ParsedEntity(BaseModel):
    """Validated entity extracted by Gemini."""
    shape: str
    shape_type: Optional[str] = None
    dimensions: dict[str, Any] = {}
    position: PositionData = PositionData()
    inclination: InclinationData = InclinationData()
    extra: dict[str, Any] = {}


class Step(BaseModel):
    """A single construction step in the solution."""
    step_id: int
    type: str
    parameters: dict[str, float]
    layer: str
    description: str


class PointCoord(BaseModel):
    """A 2D point coordinate."""
    x: float
    y: float


class PointsData(BaseModel):
    """Computed projection coordinates for a point."""
    front_view: PointCoord
    top_view: PointCoord


class ParseResponse(BaseModel):
    """Response from /parse — contains NLP extraction + geometry + drawing steps."""
    parsed: ParsedEntity
    points: Optional[dict[str, Any]] = None  # Point or line projection data
    steps: list[Step] = []


# ── Gemini Call Logic ──


def _call_gemini(question: str) -> str:
    """
    Sends the question to Gemini with the system prompt.
    Returns the raw text response.
    Raises RuntimeError on failure.
    """
    if _gemini_client is None:
        raise RuntimeError(
            "Gemini API key not configured. "
            "Set GEMINI_API_KEY in backend/.env"
        )

    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.0,  # Deterministic extraction
        },
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return response.text


def _strip_markdown_fences(text: str) -> str:
    """
    Strips markdown code fences (```json ... ```) from Gemini output.
    Gemini sometimes wraps JSON in markdown despite being told not to.
    """
    # Remove ```json ... ``` or ``` ... ```
    stripped = re.sub(
        r"^```(?:json)?\s*\n?(.*?)\n?\s*```$",
        r"\1",
        text.strip(),
        flags=re.DOTALL,
    )
    return stripped.strip()


def _parse_json_strict(raw: str) -> dict:
    """
    Parses JSON strictly. Raises ValueError on invalid JSON.
    """
    cleaned = _strip_markdown_fences(raw)
    return json.loads(cleaned)


# ── Validation Layer ──

VALID_SHAPES = {
    "point", "line", "plane", "cone", "cylinder",
    "prism", "pyramid", "sphere", "lamina",
}

POSITION_KEYS = {
    "above_hp", "below_hp", "infront_vp", "behind_vp", "on_hp", "on_vp",
}

INCLINATION_KEYS = {
    "angle_to_hp", "angle_to_vp", "angle_to_xy", "resting_element",
}


def _validate_and_normalize(data: dict) -> ParsedEntity:
    """
    Validates the Gemini-extracted JSON against the expected schema.
    
    - Ensures all required keys exist with correct types
    - Fills missing keys with null/default values
    - Removes unknown keys
    - Normalizes shape to lowercase
    
    Raises ValueError if data is fundamentally invalid (e.g., shape missing).
    """
    # ── Shape ──
    shape = data.get("shape")
    if not shape or not isinstance(shape, str):
        raise ValueError("Missing or invalid 'shape' field")

    shape = shape.strip().lower()
    if shape not in VALID_SHAPES:
        raise ValueError(f"Unknown shape '{shape}'. Valid: {VALID_SHAPES}")

    # ── Dimensions ──
    dimensions = data.get("dimensions", {})
    if not isinstance(dimensions, dict):
        dimensions = {}

    # ── Position ──
    raw_position = data.get("position", {})
    if not isinstance(raw_position, dict):
        raw_position = {}

    position = PositionData(
        above_hp=_to_optional_float(raw_position.get("above_hp")),
        below_hp=_to_optional_float(raw_position.get("below_hp")),
        infront_vp=_to_optional_float(raw_position.get("infront_vp")),
        behind_vp=_to_optional_float(raw_position.get("behind_vp")),
        on_hp=bool(raw_position.get("on_hp", False)),
        on_vp=bool(raw_position.get("on_vp", False)),
    )

    # ── Inclination ──
    raw_inclination = data.get("inclination", {})
    if not isinstance(raw_inclination, dict):
        raw_inclination = {}

    inclination = InclinationData(
        angle_to_hp=_to_optional_float(raw_inclination.get("angle_to_hp")),
        angle_to_vp=_to_optional_float(raw_inclination.get("angle_to_vp")),
        angle_to_xy=_to_optional_float(raw_inclination.get("angle_to_xy")),
        resting_element=_to_optional_str(raw_inclination.get("resting_element")),
    )

    # ── Extra ──
    extra = data.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    return ParsedEntity(
        shape=shape,
        shape_type=data.get("shape_type"),
        dimensions=dimensions,
        position=position,
        inclination=inclination,
        extra=extra,
    )


def _to_optional_float(value) -> Optional[float]:
    """Safely converts a value to float or None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_str(value) -> Optional[str]:
    """Safely converts a value to string or None."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s and s.lower() != "null" else None


# ── Endpoints ──


@app.get("/health")
async def health_check():
    """Health check endpoint for verifying the server is running."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "gemini_configured": _gemini_client is not None,
    }


@app.post("/parse", response_model=ParseResponse)
async def parse_question(request: ParseRequest):
    """
    Parse a descriptive geometry question and compute projections.
    
    Flow:
    1. Send question to Gemini with strict system prompt
    2. Strip any markdown fences from response
    3. Parse JSON strictly
    4. Validate and normalize against schema
    5. Retry once if JSON parsing fails
    6. If shape is supported, compute geometry deterministically
    7. Return parsed entity + computed coordinates + drawing steps
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question text is empty")

    logger.info(f"── Received question: {question}")

    # ── NLP Extraction via Gemini ──
    parsed_entity = None
    last_error = None

    for attempt in range(1, 3):  # Max 2 attempts (1 original + 1 retry)
        try:
            logger.info(f"── Gemini call (attempt {attempt})...")
            raw_response = _call_gemini(question)

            logger.info(f"── Raw Gemini output:\n{raw_response}")

            # Strip markdown and parse JSON
            cleaned = _strip_markdown_fences(raw_response)
            logger.info(f"── Cleaned JSON:\n{cleaned}")

            data = json.loads(cleaned)

            # Validate and normalize
            parsed_entity = _validate_and_normalize(data)
            logger.info(f"── Validation passed: shape={parsed_entity.shape}")
            break  # Success — exit retry loop

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON from Gemini (attempt {attempt}): {e}"
            logger.warning(last_error)
            continue  # Retry

        except ValueError as e:
            last_error = f"Validation failed (attempt {attempt}): {e}"
            logger.warning(last_error)
            continue  # Retry

        except RuntimeError as e:
            # API key missing or Gemini returned empty — don't retry
            logger.error(f"── Gemini error: {e}")
            raise HTTPException(status_code=503, detail=str(e))

        except Exception as e:
            last_error = f"Unexpected error (attempt {attempt}): {e}"
            logger.error(last_error)
            continue  # Retry

    if parsed_entity is None:
        logger.error(f"── All attempts failed: {last_error}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse Gemini response after 2 attempts. Last error: {last_error}",
        )

    # ── Geometry Computation (deterministic, NO AI) ──
    points_data = None
    steps: list[Step] = []

    if parsed_entity.shape in ("point", "line", "plane", "lamina"):
        try:
            parsed_dict = parsed_entity.model_dump()

            if parsed_entity.shape == "point":
                result = point_projection(parsed_dict)
                logger.info(f"── Point projection computed: {result['points']}")
            elif parsed_entity.shape == "line":
                result = line_projection(parsed_dict)
                logger.info(f"── Line projection computed: {result['points']}")
            else:
                # plane or lamina
                result = plane_projection(parsed_dict)
                logger.info(f"── Plane projection computed: {len(result.get('steps', []))} steps")

            # Store points data as generic dict
            points_data = result["points"]

            # Convert step dicts to Step models
            steps = [
                Step(**step_dict) for step_dict in result["steps"]
            ]

            logger.info(f"── Generated {len(steps)} drawing steps")

            if len(steps) == 0:
                logger.warning("── Geometry engine returned 0 steps (unsupported case?)")

        except Exception as e:
            logger.error(f"── Geometry computation failed: {e}")
            steps = []
    else:
        logger.info(
            f"── Shape '{parsed_entity.shape}' geometry not yet implemented. "
            f"Returning parsed data only."
        )

    return ParseResponse(
        parsed=parsed_entity,
        points=points_data,
        steps=steps,
    )


# ── Main entry point ──

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



