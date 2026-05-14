import logging
from pathlib import Path

# Logging setup
Path("logs").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] - %(message)s",
    filename="logs/app.log",
    filemode='a'
)

PROJECT_NAME = "ai_surveillance_system"

files = [
    # Core
    f"src/{PROJECT_NAME}/__init__.py",
    f"src/{PROJECT_NAME}/main.py",

    # Core/config
    f"src/{PROJECT_NAME}/core/__init__.py",
    f"src/{PROJECT_NAME}/core/config.py",
    f"src/{PROJECT_NAME}/core/logger.py",
    f"src/{PROJECT_NAME}/core/security.py",

    # API Layer
    f"src/{PROJECT_NAME}/api/__init__.py",
    f"src/{PROJECT_NAME}/api/deps.py",
    f"src/{PROJECT_NAME}/api/routes/__init__.py",
    f"src/{PROJECT_NAME}/api/routes/auth.py",
    f"src/{PROJECT_NAME}/api/routes/upload.py",
    f"src/{PROJECT_NAME}/api/routes/stream.py",
    f"src/{PROJECT_NAME}/api/routes/detections.py",

    # Schemas
    f"src/{PROJECT_NAME}/schemas/__init__.py",
    f"src/{PROJECT_NAME}/schemas/auth.py",
    f"src/{PROJECT_NAME}/schemas/video.py",
    f"src/{PROJECT_NAME}/schemas/detection.py",

    # Database
    f"src/{PROJECT_NAME}/db/__init__.py",
    f"src/{PROJECT_NAME}/db/session.py",
    f"src/{PROJECT_NAME}/db/models.py",

    # Services
    f"src/{PROJECT_NAME}/services/__init__.py",
    f"src/{PROJECT_NAME}/services/auth_service.py",
    f"src/{PROJECT_NAME}/services/video_service.py",
    f"src/{PROJECT_NAME}/services/detection_service.py",
    f"src/{PROJECT_NAME}/services/notification_service.py",

    # ML Pipeline
    f"src/{PROJECT_NAME}/ml/__init__.py",
    f"src/{PROJECT_NAME}/ml/model_loader.py",
    f"src/{PROJECT_NAME}/ml/preprocessing.py",
    f"src/{PROJECT_NAME}/ml/inference.py",
    f"src/{PROJECT_NAME}/ml/postprocessing.py",

    # Realtime
    f"src/{PROJECT_NAME}/realtime/__init__.py",
    f"src/{PROJECT_NAME}/realtime/websocket_manager.py",

    # Workers
    f"src/{PROJECT_NAME}/workers/__init__.py",
    f"src/{PROJECT_NAME}/workers/celery_worker.py",

    # Utils
    f"src/{PROJECT_NAME}/utils/__init__.py",
    f"src/{PROJECT_NAME}/utils/frame_utils.py",
    f"src/{PROJECT_NAME}/utils/file_utils.py",

    # Tests
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_health.py",
    "tests/test_auth.py",
    "tests/test_upload.py",
    "tests/test_detections.py",

    # Alembic migrations
    "alembic/env.py",
    "alembic/script.py.mako",
    "alembic/versions/.gitkeep",

    # Notebooks
    "notebooks/training.ipynb",
    "notebooks/experiments.ipynb",

    # Storage dirs
    "storage/uploads/.gitkeep",
    "storage/frames/.gitkeep",
    "models/.gitkeep",

    # Nginx
    "nginx/nginx.conf",

    # CI/CD
    ".github/workflows/ci.yml",

    # root config files
    "pyproject.toml",
    "alembic.ini",
    ".env",
    ".env.example",
    ".dockerignore",
    ".pre-commit-config.yaml",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
]


for file in files:
    path = Path(file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.touch()
        print(f"Created: {path}")
        logging.info(f"Created: {path}")
    else:
        print(f"Already exists: {path}")
        logging.info(f"Already exists: {path}")

logging.info("All files and folders created successfully.")
print("Project structure created. Check logs/app.log for details.")
