import os

folders = [
    "data", "features", "strategies", "risk", "execution",
    "api", "engine", "utils", "ai", "ai/models", "ai/vision",
    "ai/assistant", "ai/dream", "ai/sentiment", "ai/causal", "ai/regime",
    "evolution", "scripts", "frontend/icons", "frontend/assets"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    init_path = os.path.join(folder, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, 'w') as f:
            f.write("# Package marker\n")
        print(f"✅ Created {init_path}")
