import os
import base64
import traceback
import time
import logging
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, PlainTextResponse
from dotenv import load_dotenv
import google.generativeai as genai

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config
from datadog import initialize, statsd

# Set service name before patching
config.fastapi["service_name"] = "tryonservice"
config.service = "tryonservice"

# Initialize Datadog tracing
patch_all()

# Initialize DogStatsD
initialize(statsd_host=os.getenv('DD_AGENT_HOST', 'localhost'), statsd_port=8125)

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "tryonservice", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger('tryonservice')

# Pillow Security: Prevent Decompression Bomb attacks
# Set the limit to 50M pixels
Image.MAX_IMAGE_PIXELS = 50_000_000

# Configure PIL to raise errors instead of warnings for decompression bombs
import warnings
from PIL import Image as PILImage
warnings.filterwarnings('error', category=PILImage.DecompressionBombWarning) 

def emit_tryon_metrics(inference_duration_ms: float, category: str, success: bool = True, error_type: str = None, user_id: str = None):
    """Emit custom try-on service metrics to Datadog"""
    tags = [f"category:{category}", f"success:{str(success).lower()}", "service:tryonservice", "env:hackathon"]
    if error_type:
        tags.append(f"error_type:{error_type}")
    if user_id:
        tags.append(f"user_id:{user_id}")
    
    # Emit Proper Metrics (queryable via Metrics API)
    statsd.increment("tryon.request.count", tags=tags)
    logger.info(f"[METRIC] statsd.increment('tryon.request.count', value=1) tags={tags}")
    
    if success:
        statsd.gauge("tryon.inference.duration_ms", inference_duration_ms, tags=tags)
    else:
        statsd.increment("tryon.error.count", tags=tags)
        logger.info(f"[METRIC] statsd.increment('tryon.error.count', value=1) tags={tags}")
        if error_type:
            metric_name = f"tryon.security.{error_type}"
            statsd.increment(metric_name, tags=tags)
            logger.info(f"[METRIC] statsd.increment('{metric_name}', value=1) tags={tags} user_id={user_id}")

    # Span tags (for APM traces)
    span = tracer.current_span()
    if span:
        span.set_tag("tryon.inference.duration_ms", inference_duration_ms)
        span.set_tag("tryon.category", category)
        span.set_tag("tryon.success", success)
        if error_type:
            span.set_tag("tryon.error_type", error_type)

# ============================================

# Load environment variables (e.g., GEMINI_API_KEY)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

# Configure Gemini
TRYON_MODEL = os.getenv("TRYON_MODEL", "gemini-2.5-flash-image-preview")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(TRYON_MODEL)

MAX_SIDE = int(os.getenv("TRYON_MAX_SIDE", "1024"))

def downscale(img: Image.Image, max_side: int = MAX_SIDE) -> Image.Image:
    w, h = img.size
    scale = min(1.0, float(max_side) / max(w, h))
    if scale < 1.0:
        new_size = (int(w * scale), int(h * scale))
        return img.resize(new_size, Image.LANCZOS)
    return img


def file_to_image_part(file_bytes: bytes, mime: str = "image/png") -> Tuple[dict, Optional[str]]:
    """
    Convert raw bytes to the inline_data format.
    Returns (data_part, error_type).
    
    Security: PIL is configured to raise DecompressionBombWarning as an error
    when images exceed MAX_IMAGE_PIXELS (50M). This is caught below.
    """
    try:
        # Catch Pillow errors before they hit the LLM
        img = Image.open(BytesIO(file_bytes))
        
        # Log image info for security monitoring
        width, height = img.size
        pixel_count = width * height
        logger.info(f"Processing image: {width}x{height} = {pixel_count:,} pixels (limit: {Image.MAX_IMAGE_PIXELS:,})")
        
        # Explicitly verify the image loading
        img.verify() 
        
        # Re-open or seek back since verify() closes/moves pointer
        # This is where PIL will raise DecompressionBombWarning (converted to error)
        img = Image.open(BytesIO(file_bytes)).convert("RGB")
        
        # Log after successful load
        logger.info(f"Image loaded successfully: {width}x{height}")
        
        img = downscale(img, MAX_SIDE)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return {"mime_type": mime, "data": buf.getvalue()}, None
        
    except Image.DecompressionBombWarning as e:
        # PIL raises this when image exceeds MAX_IMAGE_PIXELS (we configured it as error)
        logger.error(f"Decompression bomb detected by PIL! {e}")
        return {}, "decompression_bomb"
    except Image.DecompressionBombError as e:
        # This catches PIL's built-in detection (for extremely large images)
        logger.error(f"Decompression bomb detected by PIL! {e}")
        return {}, "decompression_bomb"
    except Exception as e:
        logger.error(f"Image loading failed: {type(e).__name__}: {str(e)}")
        return {}, "invalid_image"

FASHION_PROMPT = """
Create a professional e-commerce fashion photo. Take the product from the first image and let the person from the second image wear it. 
Generate a realistic, full-body shot of the person wearing the product, with the lighting and shadows adjusted to match the environment in a plain background. 
Ensure the product fits naturally on the person while maintaining photographic quality."""

HOME_DECOR_PROMPT = """
Create a professional home interior design photo. Take the decor item from the first image and place it naturally in the room setting from the second image.
Generate a realistic interior shot showing how the decor item enhances the space, with proper lighting, shadows, and perspective and angles.
Ensure the item fits the room's style and scale appropriately while maintaining photographic quality."""

FURNITURE_PROMPT = """
Create a professional furniture showcase photo. Take the furniture piece from the first image and place it in the room setting from the second image.
Generate a realistic interior shot showing the furniture in use, with natural lighting, proper shadows, and realistic proportions and angles.
Ensure the furniture fits harmoniously with the existing space and maintains the room's aesthetic while looking photorealistic."""

KITCHEN_PROMPT = """
Create a professional kitchen product photo. Take the kitchen item from the first image and integrate it into the kitchen setting from the second image.
Generate a realistic kitchen scene showing the product in its natural context, with appropriate lighting, reflections, and shadows and angles.
Ensure the item looks functional and fits seamlessly into the kitchen environment while maintaining professional photography quality."""

PROMPT_MAP = {
    "fashion": FASHION_PROMPT,
    "clothing": FASHION_PROMPT,
    "accessories": FASHION_PROMPT,
    "footwear": FASHION_PROMPT,
    "home": HOME_DECOR_PROMPT,
    "decor": HOME_DECOR_PROMPT,
    "furniture": FURNITURE_PROMPT,
    "kitchen": KITCHEN_PROMPT,
    "appliances": KITCHEN_PROMPT
}

def get_prompt_for_category(category: str) -> str:
    """Get the appropriate prompt based on product category."""
    category_lower = category.lower()
    selected_prompt = PROMPT_MAP.get(category_lower, FASHION_PROMPT)
    print(f"[DEBUG] Received category: '{category_lower}'")
    print(f"[DEBUG] Selected prompt starts with: '{selected_prompt[:50]}...'")
    return selected_prompt

GENERATION_CONFIG = {"temperature": 0.4}

app = FastAPI(title="Try-On Service", version="1.0.0")

@app.get("/_healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"

@app.post("/tryon")
async def tryon(
    base_image: UploadFile = File(...), 
    product_image: UploadFile = File(...),
    category: str = Form("fashion"),
    user_id: str = Form(None)  # Optional user_id for tracking security attacks
):
    start_time = time.time()
    # Generate a default user_id if not provided (for attack tracking)
    if not user_id:
        user_id = f"anonymous-{int(time.time())}"
    
    try:
        base_bytes = await base_image.read()
        product_bytes = await product_image.read()
        if not base_bytes or not product_bytes:
            raise HTTPException(status_code=400, detail="Both images are required")

        person_part, person_err = file_to_image_part(base_bytes)
        product_part, prod_err = file_to_image_part(product_bytes)
        
        if person_err or prod_err:
            err_type = person_err or prod_err
            logger.warning(f"SECURITY: Potential attack detected! user_id={user_id} error_type={err_type}")
            emit_tryon_metrics(0, category, success=False, error_type=err_type, user_id=user_id)
            raise HTTPException(status_code=400, detail=f"Image processing failed: {err_type}")

        # Get the appropriate prompt based on category
        prompt = get_prompt_for_category(category)

        try:
            inference_start = time.time()
            resp = model.generate_content(
                [prompt, person_part, product_part],
                generation_config=GENERATION_CONFIG,
                request_options={"timeout": 180},
            )
            inference_duration = (time.time() - inference_start) * 1000
        except Exception as ge:
            # Log full traceback server-side
            logger.error("[tryon] generate_content failed:\n" + traceback.format_exc())
            emit_tryon_metrics(inference_duration_ms=0, category=category, success=False, user_id=user_id)
            # Surface a useful error message
            raise HTTPException(status_code=502, detail=f"Generation call failed: {str(ge)}")

        # Extract the first inline image from response
        img_bytes: Optional[bytes] = None
        if getattr(resp, "candidates", None):
            for cand in resp.candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []):
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None) is not None:
                        data = inline.data
                        if isinstance(data, str):
                            data = base64.b64decode(data)
                        img_bytes = data
                        break
                if img_bytes:
                    break
        if not img_bytes:
            # Try to include additional info if available
            details = getattr(resp, "text", None) or str(getattr(resp, "prompt_feedback", "No image generated"))
            emit_tryon_metrics(inference_duration_ms=inference_duration, category=category, success=False, user_id=user_id)
            raise HTTPException(status_code=502, detail=f"No image generated: {details}")

        # Emit successful metrics
        emit_tryon_metrics(inference_duration_ms=inference_duration, category=category, success=True, user_id=user_id)
        logger.info(f"Try-on completed successfully for category '{category}' in {inference_duration:.2f}ms")

        return Response(content=img_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[tryon] Unexpected error:\n" + traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# If running directly: uvicorn try_on:app --host 0.0.0.0 --port 8080
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("try_on:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))