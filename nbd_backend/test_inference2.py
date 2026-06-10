import asyncio
from app.ai.inference.inference import HeatmapGenerator
from pathlib import Path
import numpy as np
from PIL import Image

MODEL_PATH = Path("app/ai/models/best_auc_weights_only.pth").resolve()

# create dummy image
dummy_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
Image.fromarray(dummy_img).save("dummy.png")

async def test():
    try:
        gen = HeatmapGenerator(str(MODEL_PATH), 14, 224)
        print("Testing predict...")
        probs = gen.predict("dummy.png")
        print("Probs:", probs)
        
        print("Testing generate...")
        heatmap_img, bbox_img, crop_img = gen.generate("dummy.png")
        print("Heatmap generated:", heatmap_img.shape)
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
