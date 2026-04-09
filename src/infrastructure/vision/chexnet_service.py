from __future__ import annotations

from pathlib import Path

from src.domain.interfaces.vision_service import ClassificationResult, IVisionService


class CheXNetVisionService(IVisionService):
    """Loads torchxrayvision when torch is available; otherwise returns a safe placeholder."""

    def classify(self, image_path: str) -> ClassificationResult:
        path = Path(image_path)
        if not path.is_file():
            return ClassificationResult(
                label="error",
                confidence=0.0,
                findings=["Image file not found."],
            )
        try:
            import numpy as np
            import torch
            import torchvision.transforms as transforms
            from PIL import Image
            import torchxrayvision as xrv

            img = Image.open(path).convert("RGB")
            transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
            tensor = transform(img).unsqueeze(0)
            model = xrv.models.DenseNet(weights="densenet121-res224-all")
            model.eval()
            with torch.no_grad():
                out = model(tensor)
                probs = torch.sigmoid(out)[0].numpy()
            threshold = 0.5
            pathology_names = model.pathologies
            active = [
                f"{pathology_names[i]} ({probs[i]:.2f})"
                for i in range(len(pathology_names))
                if probs[i] >= threshold
            ]
            top_i = int(np.argmax(probs))
            label = pathology_names[top_i]
            confidence = float(probs[top_i])
            findings = active[:8] if active else ["No high-confidence pathology labels above threshold."]
            return ClassificationResult(label=label, confidence=confidence, findings=findings)
        except Exception as exc:  # pragma: no cover
            return ClassificationResult(
                label="unavailable",
                confidence=0.0,
                findings=[
                    "Medical image classification requires PyTorch + torchxrayvision.",
                    f"Details: {exc!s}",
                ],
            )
