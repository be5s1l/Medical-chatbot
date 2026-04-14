from __future__ import annotations

from dataclasses import dataclass

from src.core.config import settings


@dataclass(frozen=True)
class VisionDescription:
    description: str


class VisionService:
    """
    Vision model (Gemini) is used ONLY to describe the image contents.
    """

    DEFAULT_VISION_MODEL = "models/gemini-2.5-flash-image"

    def __init__(self) -> None:
        if not getattr(settings, "gemini_api_key", ""):
            raise RuntimeError("GEMINI_API_KEY is not set (required for image analysis)")

        self._model = (getattr(settings, "vision_model", "") or self.DEFAULT_VISION_MODEL).strip()
        if self._model and not self._model.startswith("models/"):
            self._model = f"models/{self._model}"

    async def describe_image(self, *, image_bytes: bytes, mime_type: str) -> VisionDescription:
        """
        Uses Generative Language v1beta API directly to avoid pulling in extra heavy deps.
        """
        from google.ai.generativelanguage_v1beta.services.generative_service import GenerativeServiceAsyncClient
        from google.ai.generativelanguage_v1beta.types import Blob, Content, Part
        from google.api_core.client_options import ClientOptions

        client = GenerativeServiceAsyncClient(client_options=ClientOptions(api_key=getattr(settings, "gemini_api_key", "")))

        prompt = (
            "Describe this medical image objectively. "
            "Do not diagnose. Focus on visible structures, notable patterns, and uncertainties. "
            "Keep it under 12 bullet points."
        )

        contents = [
            Content(parts=[Part(text=prompt)]),
            Content(parts=[Part(inline_data=Blob(mime_type=mime_type, data=image_bytes))]),
        ]

        try:
            resp = await client.generate_content(model=self._model, contents=contents)
        except Exception as exc:
            # Map provider errors to a single runtime error so routers can return 503.
            msg = str(exc)
            if len(msg) > 500:
                msg = msg[:500] + "..."
            raise RuntimeError(f"Vision API error: {msg}") from exc
        # v1beta returns candidates[0].content.parts[0].text typically.
        text = ""
        if getattr(resp, "candidates", None):
            cand = resp.candidates[0]
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            for p in parts:
                t = getattr(p, "text", "") or ""
                if t:
                    text += t
        text = (text or "").strip()
        if not text:
            raise RuntimeError("Vision model returned empty description")
        return VisionDescription(description=text)

