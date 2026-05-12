import os
import numpy as np
import cv2
from PIL import Image

import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
import matplotlib.pyplot as plt


# =========================
# 1. RESHAPE TRANSFORM
# =========================
def reshape_transform(tensor):
    if tensor.dim() == 3:
        B, L, C = tensor.shape
        H = W = int(L ** 0.5)
        return tensor.reshape(B, H, W, C).permute(0, 3, 1, 2)

    elif tensor.dim() == 4:
        # detect format
        if tensor.shape[1] < 10:  # likely (B,H,W,C)
            return tensor.permute(0, 3, 1, 2)
        else:
            return tensor  # already (B,C,H,W)

    else:
        raise ValueError(f"Unsupported shape: {tensor.shape}")


# =========================
# 2. EIGEN-CAM CLASS
# =========================
class EigenCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.activations = None

        target_layer.register_forward_hook(self.forward_hook)

    def forward_hook(self, module, input, output):
        self.activations = output.detach()

    def __call__(self, input_tensor):
        with torch.no_grad():
            _ = self.model(input_tensor)

        activations = reshape_transform(self.activations)  # (B, C, H, W)

        B, C, H, W = activations.shape

        # flatten: (C, H*W)
        A = activations[0].reshape(C, -1)

        # ===== PCA via SVD =====
        # A = U S V^T
        U, S, V = torch.linalg.svd(A, full_matrices=False)

        # principal component
        cam = V[0].reshape(H, W)

        cam = cam.cpu().numpy()
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)

        return cam


# =========================
# 3. MAIN GENERATOR
# =========================
class HeatmapGenerator:
    def __init__(self, pathModel, nnClassCount, transCrop, device=None):
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.transCrop = transCrop

        # Load Swin
        model = models.swin_t(weights=None)
        num_ftrs = model.head.in_features
        model.head = nn.Linear(num_ftrs, nnClassCount)

        # Try weights-only load first (safe with PyTorch >=2.6 behavior). If it fails,
        # fall back to loading full checkpoint (may require allowing numpy scalar global).
        checkpoint = None
        used_weights_only = False
        try:
            checkpoint = torch.load(pathModel, map_location=self.device, weights_only=True)
            used_weights_only = True
        except Exception as e_weights:
            try:
                # Try to allow the numpy scalar global if available
                scalar_obj = None
                try:
                    scalar_obj = getattr(np, '_core').multiarray.scalar
                except Exception:
                    scalar_obj = None

                if scalar_obj is not None and hasattr(torch.serialization, 'safe_globals'):
                    with torch.serialization.safe_globals([scalar_obj]):
                        checkpoint = torch.load(pathModel, map_location=self.device, weights_only=False)
                elif scalar_obj is not None and hasattr(torch.serialization, 'add_safe_globals'):
                    torch.serialization.add_safe_globals([scalar_obj])
                    checkpoint = torch.load(pathModel, map_location=self.device, weights_only=False)
                else:
                    # Last resort: load full checkpoint without safe context. Only do if file trusted.
                    checkpoint = torch.load(pathModel, map_location=self.device, weights_only=False)
            except Exception as e_full:
                raise RuntimeError(f"Failed to load checkpoint {pathModel}: {e_full}\nOriginal error: {e_weights}") from e_full

        # Extract state dict from common checkpoint formats (full checkpoint or weights-only)
        if isinstance(checkpoint, dict):
            if 'model_state' in checkpoint:
                checkpoint_state = checkpoint['model_state']
            elif 'state_dict' in checkpoint:
                checkpoint_state = checkpoint['state_dict']
            elif 'model_state_dict' in checkpoint:
                checkpoint_state = checkpoint['model_state_dict']
            elif 'model' in checkpoint and isinstance(checkpoint['model'], dict):
                checkpoint_state = checkpoint['model']
            else:
                # Heuristic: if values are tensors assume it's already a state_dict
                if all(isinstance(v, torch.Tensor) for v in checkpoint.values()):
                    checkpoint_state = checkpoint
                else:
                    # Try to find a nested dict that looks like a state_dict
                    found = None
                    for v in checkpoint.values():
                        if isinstance(v, dict) and all(isinstance(x, torch.Tensor) for x in v.values()):
                            found = v
                            break
                    checkpoint_state = found if found is not None else checkpoint
        else:
            checkpoint_state = checkpoint

        # --- Diagnostics: analyze key correspondence ---
        model_state = model.state_dict()

        # Build cleaned map for checkpoint keys -> original key in checkpoint
        ck_clean = {}
        for k in checkpoint_state.keys():
            ck = k
            if isinstance(k, str) and k.startswith('module.'):
                ck = k[len('module.'):]
            ck_clean[ck] = k

        matched = []
        mismatched_shape = []
        for k, v in model_state.items():
            if k in ck_clean:
                ck_k = ck_clean[k]
                v_ck = checkpoint_state[ck_k]
                if v.shape == v_ck.shape:
                    matched.append(k)
                else:
                    mismatched_shape.append((k, v.shape, v_ck.shape))

        missing = [k for k in model_state.keys() if k not in ck_clean]
        unexpected = [k for k in checkpoint_state.keys() if (k.startswith('module.') and k[len('module.'):] not in model_state) or (not k.startswith('module.') and k not in model_state)]

        print(f"[Checkpoint loader] path={pathModel}")
        print(f"  Format: {'weights-only' if used_weights_only else 'full-checkpoint/fallback'}")
        print(f"  Model params : {len(model_state)}")
        print(f"  Checkpoint params: {len(checkpoint_state)}")
        print(f"  Matched tensors: {len(matched)}")
        print(f"  Missing model keys (not found in checkpoint): {len(missing)}")
        if len(missing) > 0:
            print("    Examples:", missing[:8])
        print(f"  Shape-mismatched keys: {len(mismatched_shape)}")
        if len(mismatched_shape) > 0:
            print("    Examples:", mismatched_shape[:6])
        print(f"  Unexpected checkpoint keys: {len(unexpected)}")
        if len(unexpected) > 0:
            print("    Examples:", unexpected[:8])

        # Now build compatible_state using same cleaning logic, prefer matched shapes
        compatible_state = {}
        for ck_cleaned, orig_ck in ck_clean.items():
            if ck_cleaned in model_state and isinstance(checkpoint_state[orig_ck], torch.Tensor) and model_state[ck_cleaned].shape == checkpoint_state[orig_ck].shape:
                compatible_state[ck_cleaned] = checkpoint_state[orig_ck]

        # If we found compatible parameters, merge them; otherwise attempt a direct strict load
        if len(compatible_state) > 0:
            merged_state = model_state.copy()
            merged_state.update(compatible_state)
            model.load_state_dict(merged_state, strict=False)
            print(f"[Checkpoint loader] Loaded {len(compatible_state)} tensors into model (partial/lenient)")
        else:
            try:
                model.load_state_dict(checkpoint_state, strict=True)
                print("[Checkpoint loader] Loaded checkpoint with strict=True")
            except Exception as e:
                model.load_state_dict(model_state, strict=False)
                print(f"[Checkpoint loader] Strict load failed: {e}. Using model default state (no tensors loaded)")

        self.model = model.to(self.device).eval()

        # 🔥 Eigen-CAM dùng layer cuối
        target_layer = self.model.norm
        self.cam = EigenCAM(self.model, target_layer)

        # Transform
        self.transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.Resize((transCrop, transCrop)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225])
        ])

    def _prepare_image(self, path):
        return Image.open(path).convert('RGB')

    def predict(self, path):
        image = self._prepare_image(path)
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.sigmoid(logits)[0]

        return probs.cpu().numpy()

    def generate(self, path):
        image = self._prepare_image(path)
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        cam = self.cam(tensor)
        cam = cv2.resize(cam, (self.transCrop, self.transCrop))

        # original image
        img = cv2.imread(path)
        img = cv2.resize(img, (self.transCrop, self.transCrop))

        # heatmap
        heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(img, 0.5, heatmap, 0.5, 0)

        # ===== BBOX =====
        cam_uint8 = np.uint8(cam * 255)
        thresh_val = int(cam_uint8.max() * 0.6)
        _, th = cv2.threshold(cam_uint8, thresh_val, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bbox_img = img.copy()
        crop_img = None

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(bbox_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            crop_img = img[y:y + h, x:x + w]

        return overlay[:, :, ::-1], bbox_img[:, :, ::-1], crop_img


if __name__ == "__main__":
    # =========================
    # 4. RUN TEST
    # =========================
    pathInputImage = '/kaggle/input/datasets/khanfashee/nih-chest-x-ray-14-224x224-resized/images-224/images-224/00000001_001.png'
    pathModel = '/kaggle/input/datasets/anhquocnguyen123/swin-tiny-only-weight/best_auc_weights_only.pth'

    class_names = ['Atelectasis','Cardiomegaly','Consolidation','Edema','Effusion','Emphysema','Fibrosis','Hernia',
                   'Infiltration','Mass','Nodule','Pleural_Thickening','Pneumonia','Pneumothorax']

    h = HeatmapGenerator(pathModel, 14, 224)

    probs = h.predict(pathInputImage)
    sorted_idx = np.argsort(-probs)

    print("Top dự đoán:")
    for idx in sorted_idx[:5]:
        print(f"{class_names[idx]}: {probs[idx]*100:.2f}%")

    heatmap_img, bbox_img, crop_img = h.generate(pathInputImage)

    plt.figure(figsize=(15,5))

    plt.subplot(1,3,1)
    plt.title("Eigen-CAM")
    plt.imshow(heatmap_img)
    plt.axis('off')

    plt.subplot(1,3,2)
    plt.title("BBox")
    plt.imshow(bbox_img)
    plt.axis('off')

    if crop_img is not None:
        plt.subplot(1,3,3)
        plt.title("ROI")
        plt.imshow(crop_img)
        plt.axis('off')
    else:
        print("⚠ Không phát hiện bbox")