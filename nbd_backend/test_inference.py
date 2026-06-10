import asyncio
from app.ai.inference.inference import HeatmapGenerator
from pathlib import Path

MODEL_PATH = Path("app/ai/models/best_auc_weights_only.pth").resolve()

async def test():
    try:
        print("Loading generator...")
        gen = HeatmapGenerator(str(MODEL_PATH), 14, 224)
        print("Loaded generator!")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
