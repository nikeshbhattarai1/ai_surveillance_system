# AI Surveillance System (Frontend)

A React + Vite dashboard for the AI Surveillance System, a platform designed to detect violence and potential threats from both live and recorded video.

The frontend can stream webcam or CCTV footage to the backend over WebSockets for real-time detection. It also allows users to upload recorded videos for offline analysis and provides a history of previous detection events. Authentication and protected features are handled using JWT.

This frontend is designed to work with the `ai_surveillance_system` FastAPI backend, which runs the ResNet50 + BiLSTM detection model.

## Features

- **Authentication**: Users can register and log in with their email and password. The application uses JWT access and refresh tokens, with access tokens refreshed automatically through an Axios interceptor. The user's role (`admin`, `operator`, or `viewer`) is also displayed in the navigation bar.

- **Live Feed**: Streams frames from a webcam or RTSP source to the backend through `WS /ws/stream` at 5 FPS. Detection results are displayed in real time, including threat and clear events, along with a running count of detected threats.

- **Video Upload**: Users can upload recorded videos using drag-and-drop or the file picker. MP4, AVI, MOV, and MKV formats are supported. The interface shows upload progress, then monitors the processing job until the analysis is complete and displays the results.

- **Detection History**: Displays a paginated list of previous detection events, including the detection type, confidence score, source, and notification channel. Job IDs can be copied directly to the clipboard. Deleting detection records is restricted to users with the `admin` or `operator` role.


## Tech Stack

| Purpose | Library |
|---|---|
| UI | React 18 |
| Build tool / dev server | Vite 5 |
| Routing | React Router 6 |
| HTTP client | Axios |
| Data fetching | react-query (installed, not wired up app-wide yet) |

## Prerequisites

- Node.js 18+ and npm
- The backend running (see the `ai_surveillance_system` repo). Expected at `http://localhost:8000` by default.

## Getting Started

```bash
# install dependencies
npm install

# start the dev server (http://localhost:3000)
npm run dev

# build for production, outputs to dist/
npm run build

# preview the production build locally
npm run preview
```

## Environment Variables

Set `VITE_API_URL` in a `.env` file if you need to point at a different API host.

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | empty (same origin) | Base URL of the backend API. If left unset, requests use the current origin. This works with the nginx reverse proxy in production and the Vite proxy during development. The WebSocket URL is automatically derived by changing `http` to `ws` (or `https` to `wss`). |

In development, `vite.config.js` already proxies `/api`, `/auth`, and `/ws` to the backend at `http://localhost:8000` and `ws://localhost:8000`. Because of this, you can usually leave `VITE_API_URL` unset when running `npm run dev`.


## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js          # Axios instance, auth header + refresh interceptor, WS_URL
│   │   └── detections.js      # /api/v1/upload, /jobs, /detections endpoints
│   ├── components/
│   │   ├── CameraFeed.jsx     # webcam/RTSP capture + WebSocket streaming UI
│   │   ├── ConfidenceBar.jsx
│   │   ├── DetectionFeed.jsx  # live event list (Live Feed page)
│   │   ├── DetectionResults.jsx
│   │   ├── LoginScreen.jsx    # login / register form
│   │   ├── Navbar.jsx
│   │   └── UploadPanel.jsx    # drag-and-drop video upload
│   ├── context/
│   │   └── AuthContext.jsx    # login/register/logout, token storage, silent refresh
│   ├── hooks/
│   │   ├── useDetections.js   # polling list + optimistic delete
│   │   └── useWebSocket.js    # /ws/stream connection, webcam capture loop
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── LiveFeed.jsx
│   │   ├── VideoUpload.jsx
│   │   └── DetectionHistory.jsx
│   ├── App.jsx                # routes + auth gate
│   ├── main.jsx                # app entry point
│   └── index.css              # theme (CSS variables) + global styles
├── index.html
├── vite.config.js
└── package.json
```

## Backend API Surface Used

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create a user |
| `POST` | `/auth/login` | Get access/refresh tokens |
| `POST` | `/auth/refresh` | Exchange refresh token for a new access token |
| `GET` | `/auth/me` | Fetch current user profile |
| `POST` | `/api/v1/upload` | Upload a video for analysis |
| `GET` | `/api/v1/jobs/{job_id}` | Poll a video job's processing status |
| `GET` | `/api/v1/detections` | List detection events (paginated, filterable) |
| `DELETE` | `/api/v1/detections/{id}` | Delete a detection event (admin/operator only) |
| `WS` | `/ws/stream` | Stream live frames, receive threat/clear/heartbeat events |

---