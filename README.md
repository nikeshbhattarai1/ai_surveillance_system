# AI Surveillance System

AI Surveillance System is an AI-powered video surveillance platform that detects violent activities in uploaded videos and live camera feeds. It monitors video content in real time and identifies potential threats automatically. When violence is detected, the system captures evidence frames and can send alerts through WhatsApp or email.

## Overview

The system uses a deep learning model to classify short video clips as violent or non violent. The model combines a ResNet50 backbone with a BiLSTM network and temporal attention. This lets it look at both individual frames and how they change over time.

There are two ways to analyze video:
- **Offline analysis.** You upload a video. It is saved on the server and a background job is created with Celery. A worker processes the video, runs it through the model, and saves the result to the database.
- **Live stream analysis.** The frontend sends video frames over WebSocket. The server keeps a rolling buffer of recent frames and runs the model on that buffer. Results come back to the frontend in near real time.

The system also handles authentication, role based access, detection history, evidence storage, and notifications.

## Key Features

- **Offline video analysis:** Upload a video and get results once processing finishes. Uploads do not block the API since processing runs in the background.
- **Live stream monitoring:** A WebSocket endpoint accepts a live frame stream and runs inference on a rolling buffer.
- **Role based access control:** JWT authentication with three roles: ADMIN, OPERATOR, and VIEWER. Deleting detection records is restricted to ADMIN and OPERATOR.
- **Evidence capture:** When a threat is confirmed, the first, middle, and last frames of the clip are saved and labeled with the detected class and confidence score.
- **Alerts:** WhatsApp alerts go out through Twilio and email alerts go out through SMTP. A cooldown period stops the system from sending too many alerts for the same event.
- **Detection history:** A filterable, paginated dashboard shows past detections. You can delete records one at a time or in bulk, and copy a job ID with one click.
- **Background processing:** Video analysis runs on Celery workers, backed by Redis, so heavy processing stays off the main API process.

## Architecture

```

                        ┌─────────────┐      ┌───────────┐      ┌──────────────────────────┐
                        │   Browser   │◄────►│   Nginx   │◄────►│      FastAPI (API)       │
                        │ (React SPA) │      │  (Proxy)  │      │  • REST + WebSocket      │
                        └─────────────┘      └───────────┘      │  • JWT authentication    │
                                                                │  • Live stream inference │
                                                                └────────────┬─────────────┘
                                                                             │
                                        ┌────────────────────────────────────┼───────────────────────────────────┐
                                        │                                    │                                   │
                                        ▼                                    ▼                                   ▼
                                ┌─────────────────┐                 ┌───────────────┐                 ┌──────────────────┐
                                │   PostgreSQL    │                 │     Redis     │                 │  Celery Worker   │
                                │                 │                 │               │                 │                  │
                                │ • Jobs          │                 │ • Task broker │                 │ • Video decode   │
                                │ • Users         │                 │ • Result      │                 │ • ResNet50       │
                                │ • Detections    │                 │   backend     │                 │   + BiLSTM       │
                                └─────────────────┘                 └───────────────┘                 │ • Evidence       │
                                                                                                      │   frames         │
                                                                                                      └──────────────────┘


```

## System Workflow

When a video is uploaded, the system saves it to disk and creates a VideoJob record. A Celery task is then added to the processing queue. The worker divides the video into overlapping 32-frame clips and processes them through the AI model in batches. The results from all clips are combined to produce one final verdict for the video. A DetectionEvent record is then created for both threat and clear results.

For live monitoring, the same AI model is used to analyze frames received through a WebSocket connection. Instead of processing a saved video file, the system maintains a rolling buffer of incoming frames and checks them continuously for possible threats.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn, Pydantic v2 |
| ML | PyTorch, torchvision (ResNet50 backbone), OpenCV |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) + Alembic |
| Task queue | Celery + Redis |
| Auth | JWT (python-jose), bcrypt |
| Notifications | Twilio (WhatsApp), SMTP (email) |
| Frontend | React 18, Vite, React Router, Axios |
| Infra | Docker Compose, Nginx |

## ML Model

`ViolenceDetector` (`src/ai_surveillance_system/ml/model_loader.py`):

```
Per-frame ResNet50 (ImageNet backbone, FC head removed)
        │
        ▼
   2-layer BiLSTM (hidden size 256, dropout 0.4)
        │
        ▼
Bahdanau-style temporal attention over the LSTM outputs
        │
        ▼
   FC classifier (512 → 256 → 128 → 2)
```

- **Input:** 32 frame clips, resized to 224x224 and normalized using ImageNet stats.
- **Output classes:** violence, nonviolence.
- **Inference:** the model uses a sliding window to extract clips, with 50% overlap by default. Uploaded videos are processed in batches. Live streams are processed clip by clip from the rolling buffer.
- **Aggregation:** for an uploaded video, each clip gets its own verdict first. If any clip crosses the confidence threshold, the highest confidence threat clip becomes the result for the whole video. Otherwise the video is marked clear.
- **Confidence threshold:** set by the CONFIDENCE_THRESHOLD environment variable. Default is 0.75. A clip has to meet or beat this value to count as a confirmed threat.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- A trained model checkpoint (a .pt file), placed at the path set in MODEL_PATH
- Node.js 20 or higher and Python 3.11 or higher, only if you want to run the frontend or backend outside Docker

### Quick start (Docker)

```bash
git clone https://github.com/nikeshbhattarai1/ai_surveillance_system.git
cd ai_surveillance_system

cp .env.example .env
# edit .env and set SECRET_KEY, DB credentials, MODEL_PATH, etc.

docker compose up --build
```

Once running:

| Service | URL |
|---|---|
| Frontend | http://localhost |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost/health |

### Local development (without Docker)

**Backend:**
```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn ai_surveillance_system.main:app --reload
```

**Celery worker** (run this in a separate terminal, Redis needs to be running first):
```bash
celery -A ai_surveillance_system.workers.celery_worker.celery_app worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Set these in your .env file. Use .env.example as a starting point. None of the example values below are real. Replace all of them, especially SECRET_KEY and the database password before running this anywhere beyond your own machine.

| Variable | Description | Example |
|---|---|---|
| DATABASE_URL | Async Postgres connection string | postgresql+asyncpg://user:pass@postgres:5432/surveillance |
| SECRET_KEY | JWT signing key, at least 32 characters and not a common or weak value | generate your own, for example with openssl rand -hex 32 |
| ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access token lifetime | 30 |
| UPLOAD_DIR / FRAMES_DIR | Storage paths for uploaded videos and evidence frames | storage/uploads, storage/frames |
| MAX_UPLOAD_SIZE_MB | Maximum accepted upload size | 500 |
| MODEL_PATH | Path to the trained .pt checkpoint | models/violence_detector.pt |
| CONFIDENCE_THRESHOLD | Minimum confidence needed to confirm a threat | 0.75 |
| REDIS_URL | Celery broker and result backend | redis://redis:6379/0 |
| TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, ALERT_PHONE_NUMBER | WhatsApp alerting through Twilio | — |
| ALERT_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD | Email alerting | — |

> **Security note:** if your .env file was ever committed to version control with real credentials in it, rotate SECRET_KEY and the database password before deploying anywhere beyond local development. Make sure .env is in your .gitignore going forward. It is already listed in .dockerignore, but that only keeps it out of the Docker image, not out of your git history.

## Project Structure

```
src/ai_surveillance_system/
├── main.py                         # FastAPI app factory, lifespan, health check
├── core/
│   ├── config.py                   # Pydantic settings, loaded from env
│   ├── logger.py                   # Rotating file and console logger
│   └── security.py                 # Password hashing, JWT encode and decode
├── api/
│   ├── deps.py                     # get_current_user, require_role(...)
│   └── routes/
│       ├── auth.py                 # register, login, refresh, me
│       ├── upload.py               # video upload and job status
│       ├── stream.py               # WebSocket live stream inference
│       └── detections.py           # list, get, delete, bulk delete
├── db/
│   ├── models.py                   # VideoJob, DetectionEvent, User, and enums
│   └── session.py                  # async engine, session factory
├── schemas/                        # Pydantic request and response models
├── services/
│   ├── auth_service.py
│   ├── video_service.py            # upload validation, streaming to disk
│   ├── detection_service.py        # CRUD, live stream inference orchestration
│   └── notification_service.py     # WhatsApp and email dispatch, cooldown
├── ml/
│   ├── model_loader.py             # ViolenceDetector architecture, singleton loader
│   ├── preprocessing.py            # frame normalization, clip extraction, stream buffer
│   ├── inference.py                # single and batch forward pass
│   └── postprocessing.py           # threshold gating, evidence frames, aggregation
├── realtime/
│   └── websocket_manager.py        # connection registry, broadcast and send
└── workers/
    └── celery_worker.py            # video processing Celery task

frontend/src/
├── App.jsx
├── main.jsx
├── api/                            # client.js, detections.js
├── context/                        # AuthContext.jsx
├── hooks/                          # useDetections.js, useWebSocket.js
├── components/                     # Navbar, Layout, LoginScreen, UploadPanel,
│                                    # DetectionResults, ConfidenceBar, CameraFeed,
│                                    # DetectionFeed
└── pages/                          # Home, VideoUpload, LiveFeed, DetectionHistory

nginx/nginx.conf                    # reverse proxy for /auth, /api/, /ws/, /health, /frames/, SPA fallback
alembic/                            # DB migrations
tests/                              # pytest suite
.github/workflows/ci.yml            # backend tests, frontend build, docker build

```

## API Reference

Full interactive docs are available at /docs once the app is running. Here is a summary:

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/register | none | Create a user, default role is OPERATOR |
| POST | /auth/login | none | Exchange credentials for an access and refresh token |
| POST | /auth/refresh | none | Exchange a refresh token for a new access token |
| GET | /auth/me | any | Get the current authenticated user |
| POST | /api/v1/upload | any | Upload a video for offline analysis |
| GET | /api/v1/jobs/{job_id} | any | Check a video job's processing status |
| GET | /api/v1/detections | any | List detections, filterable by job_id and event_type, paginated |
| GET | /api/v1/detections/{id} | any | Get one detection |
| DELETE | /api/v1/detections/{id} | ADMIN/OPERATOR | Delete one detection and its evidence frame |
| DELETE | /api/v1/detections | ADMIN/OPERATOR | Bulk delete detections, optionally filtered by job_id or event_type |
| WS | /ws/stream | none | Live frame stream for real time inference |
| GET | /health | none | Check database, Redis, and model load status |

## Data Model

- **VideoStatus:** queued → processing → completed or failed
- **EventType:** violence and normal are used today. anomaly, intrusion, fire, and unknown exist in the schema but are reserved for future model classes.
- **UserRole:** admin, operator, viewer

## Known Limitations / Roadmap

- **No Hot Reload in Docker:** Code changes require rebuilding the affected Docker service because the application is installed during the image build. A development mode with a bind mount and editable installation could make development faster.
- **Logger Name Collision:** The logger currently caches one logger instance and may ignore the module name after the first call. This does not affect system functionality, but it can make it harder to identify the source of log messages.
- **Client-Side Detection History Filters:** Detection history filters currently apply only to the results loaded on the current page. They do not filter the complete dataset on the server, which may cause incomplete results when filtering across multiple pages.
- **Binary Classification:** The current model supports only two classes: violence and nonviolence. Other event types such as anomaly, intrusion, and fire are defined in the system but are not currently detected by the model.
- **Confidence Score for Clear Results:** For videos classified as clear, the system uses the highest confidence score among all processed clips. This can sometimes make the result appear more certain than it is. Future improvements could use an average or minimum confidence score for a more conservative result.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---