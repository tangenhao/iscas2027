"""Portable STDiT-3 FP16 timing configuration."""

import os

BUNDLE_ROOT = os.environ.get("STDIT_BUNDLE_ROOT")
if not BUNDLE_ROOT:
    raise RuntimeError("STDIT_BUNDLE_ROOT must be set by run_stdit_timing.sh")
PROJECT_ROOT = os.path.join(BUNDLE_ROOT, "project", "ViDiT-Q")
EXAMPLE_ROOT = os.path.join(PROJECT_ROOT, "examples", "opensora1.2")
MODEL_ROOT = os.path.join(EXAMPLE_ROOT, "ckpts", "hpcai-tech", "OpenSora-STDiT-v3")

resolution = "512"
aspect_ratio = "1:1"
num_frames = 512
fps = 24
frame_interval = 1
save_fps = 24
seed = 42
batch_size = 1
multi_resolution = "STDiT2"
dtype = "fp16"
condition_frame_length = 5
align = 5

model = dict(type="STDiT3-XL/2", from_pretrained=MODEL_ROOT, qk_norm=True,
             enable_flash_attn=False, enable_layernorm_kernel=False)
vae = dict(type="OpenSoraVAE_V1_2", from_pretrained="hpcai-tech/OpenSora-VAE-v1.2",
           micro_frame_size=17, micro_batch_size=4)
text_encoder = dict(type="t5", from_pretrained="DeepFloyd/t5-v1_1-xxl", model_max_length=300)
scheduler = dict(type="rflow", use_timestep_transform=True, num_sampling_steps=30, cfg_scale=7.0)
aes = 6.5
flow = None
precompute_text_embeds = False
prompt_path = os.path.join(EXAMPLE_ROOT, "prompts.txt")
save_dir = os.environ.get("STDIT_DEFAULT_OUTPUT", os.path.join(BUNDLE_ROOT, "runs", "stdit_fp"))
hardware = False
shape_logging = dict(enabled=False, filename="stdit_shapes.jsonl")
timing = dict(enabled=True)
teacache = dict(enabled=False)
