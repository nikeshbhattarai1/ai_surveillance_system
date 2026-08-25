import logging
from pathlib import Path

# Logging Setup
Path("logs").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] - %(message)s",
    filename="logs/frontend_setup.log",
    filemode="a"
)

# Frontend Project Structure
files = [

    # Root Configuration
    "package.json",
    "vite.config.js",
    "index.html",
    ".gitignore",
    ".env",
    ".env.example",
    "README.md",

    # Public
    "public/.gitkeep",

    # React Entry Files
    "src/main.jsx",
    "src/App.jsx",
    "src/index.css",

    # Assets
    "src/assets/.gitkeep",

    # Pages
    "src/pages/Home.jsx",
    "src/pages/LiveFeed.jsx",
    "src/pages/VideoUpload.jsx",
    "src/pages/DetectionHistory.jsx",

    # Components
    "src/components/Navbar.jsx",
    "src/components/Layout.jsx",

    "src/components/CameraFeed.jsx",
    "src/components/DetectionFeed.jsx",
    "src/components/DetectionHistory.jsx",
    "src/components/UploadPanel.jsx",
    "src/components/ConfidenceBar.jsx",

    # API
    "src/api/client.js",
    "src/api/detections.js",

    # Custom Hooks
    "src/hooks/useWebSocket.js",
    "src/hooks/useDetections.js",

    # Styles
    "src/styles/.gitkeep",

    # Utilities (optional)
    "src/utils/.gitkeep",
]

# Create Files & Directories
for file in files:
    path = Path(file)

    # Create parent folders
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create file only if it doesn't exist
    if not path.exists():
        path.touch()
        print(f"Created: {path}")
        logging.info(f"Created: {path}")
    else:
        print(f"Already exists: {path}")
        logging.info(f"Already exists: {path}")

# Finished
logging.info("Frontend project structure created successfully.")
print("\nFrontend project structure created successfully.")
print("Check logs/frontend_setup.log for details.")