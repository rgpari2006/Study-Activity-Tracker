# Study Activity Tracker

A local application for students that records how a study session is spent. It strictly adheres to the core principle:

> **Detect → Record → Display.** It must only OBSERVE and RECORD. It must never judge.

---

## Hard Rules

1. **Never label anything as "productive", "wasted", "distracted", "focused", or "studying".**
2. **Never show trends like "improved", "worse", or "better than last week".** Show numbers only.
3. **Never classify an app or website as educational or entertainment.** Log its executable name and duration only.
4. **If camera detection is not confident, or the activity is outside the defined list, record it as `Undefined`. Do not guess.**
5. **Process everything locally. Never save video or images.** Store only labels, timestamps, and durations.

---

## Architecture

The project runs completely locally in two parts:

- **Backend (Python 3.11+, FastAPI)**:
  - Owns all hardware and OS interactions.
  - Background camera capture with OpenCV and MJPEG streaming at `/video_feed`.
  - Local AI detection with Ultralytics YOLOv8 (pose keypoints + study objects: laptop, book/paper, phone in hand).
  - Multi-activity temporal smoothing (2.0s stability threshold) to eliminate frame-to-frame flicker.
  - Foreground application and window tracking behind an OS-independent interface (Windows via `pywin32` + `psutil`).
  - Persistent SQLite storage (`study_tracker.db`) recording normalized session, activity, and application intervals.
  - WebSocket (`/ws`) pushing real-time session state at 1.0 Hz.
  - REST endpoints for session controls and analytics.

- **Frontend (React, Vite, TypeScript, Tailwind CSS, Recharts)**:
  - UI only with zero detection logic.
  - Receives live session state via WebSocket (`ws://localhost:8000/ws`).
  - Session timer with progress bar, state-aware controls, and live MJPEG preview in a standard `<img>` tag.
  - Neutral activity pills and active application card.
  - Comprehensive Analytics Dashboard with date range filters, plain text duration tables, and Recharts bar charts.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, OpenCV, Ultralytics YOLO (`yolov8n-pose.pt`, `yolov8n.pt`), SQLite (`sqlite3`), `psutil`, `pywin32` |
| **Frontend** | React 19, TypeScript, Vite, React Router, Recharts, Tailwind CSS v4 |
| **Protocols** | HTTP REST, WebSocket, Multipart MJPEG Streaming |

---

## Project Structure

```
study-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py           # Configurable thresholds, models, and DB path
│   │   ├── main.py             # FastAPI app, routes, WebSocket, CORS
│   │   ├── session.py          # Session state machine, timer math, tracker orchestration
│   │   ├── camera/
│   │   │   ├── __init__.py
│   │   │   ├── capture.py      # CameraThread, MJPEG stream generator
│   │   │   ├── detector.py     # PoseDetector & StudyActivityDetector (YOLOv8)
│   │   │   └── smoothing.py    # MultiActivitySmoother (independent ON/OFF debounce)
│   │   ├── tracking/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # BaseWindowTracker abstract interface
│   │   │   ├── windows.py      # WindowsWindowTracker (pywin32 + psutil)
│   │   │   └── tracker.py      # WindowTrackingService (interval merging)
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── db.py           # DatabaseManager (SQLite schema & queries)
│   │   │   └── recorder.py     # CameraActivityRecorder (multi-interval tracking)
│   │   └── analytics/
│   │       ├── __init__.py
│   │       └── service.py      # AnalyticsService (summary, daily, weekly)
│   ├── requirements.txt
│   └── tests_*.py              # Comprehensive automated test suites (Phases 1-7)
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── rest.ts         # Session control REST client
│   │   │   ├── useWebSocket.ts # Live WebSocket hook with auto-reconnect
│   │   │   └── analytics.ts    # Analytics REST client
│   │   ├── components/
│   │   │   ├── NavBar.tsx      # Top navigation
│   │   │   ├── Timer.tsx       # Wall-clock timer with progress bar
│   │   │   ├── CameraPreview.tsx # MJPEG stream with loading state
│   │   │   ├── SessionControls.tsx # Presets & action buttons
│   │   │   ├── ActivityBadge.tsx # Neutral posture & object pills
│   │   │   └── ActiveAppBadge.tsx # Neutral foreground app & window title card
│   │   ├── pages/
│   │   │   ├── SessionPage.tsx # Live study session view
│   │   │   └── AnalyticsPage.tsx # Objective analytics dashboard
│   │   ├── App.tsx             # Root router
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Running with Windows PowerShell (Recommended)

You can launch the entire project automatically with the included PowerShell script, or run the services manually in separate PowerShell terminal tabs.

### Option A: One-Click Launch (`start.ps1`)

In PowerShell, navigate to the project directory and run:

```powershell
# If scripts are restricted on your system, allow execution for this process:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Run the launcher script
.\start.ps1
```
> This opens two dedicated PowerShell windows—one running the FastAPI backend (`http://localhost:8000`) and one running the Vite frontend (`http://localhost:5173`).

---

### Option B: Manual Step-by-Step PowerShell Commands

Open **two** PowerShell windows or tabs:

#### 1. Backend Terminal (PowerShell)

```powershell
# Navigate to the backend folder
cd backend

# If script execution is disabled, allow it for this session:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Create Python virtual environment (if not already created)
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements (first time only)
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Backend will be live at:
- API Root: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`

---

#### 2. Frontend Terminal (PowerShell)

```powershell
# Navigate to the frontend folder
cd frontend

# Install node packages (first time only)
npm install

# Start Vite dev server
npm run dev
```
Open your browser and navigate to:
- **`http://localhost:5173`**

---

### PowerShell Troubleshooting Tips

1. **`Activate.ps1 cannot be loaded because running scripts is disabled on this system`**:
   Run this command in your PowerShell window before activating:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
   *(This safely enables scripts only for the current PowerShell window without altering global system policies).*

2. **Run PowerShell as Administrator (if needed)**:
   Right-click the Windows Start menu or PowerShell icon and select **"Run as administrator"** if you encounter permission errors with system packages or hardware access.

---

## API Reference

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/sessions/start` | Start study session. Body: `{"planned_duration_sec": 1500}` |
| `POST` | `/sessions/pause` | Pause session (stops timer and seals active intervals) |
| `POST` | `/sessions/resume` | Resume session |
| `POST` | `/sessions/stop` | Stop session and persist all events to SQLite |
| `GET` | `/sessions` | List all past sessions |
| `GET` | `/sessions/{id}` | Get session details including activity and app events |
| `GET` | `/analytics/summary` | Query aggregate totals (`?from=<epoch>&to=<epoch>`) |
| `GET` | `/analytics/daily` | Query daily historical summaries (`?limit=30`) |
| `GET` | `/analytics/weekly` | Query weekly historical summaries (`?limit=12`) |
| `GET` | `/video_feed` | Multipart MJPEG camera preview stream |

### WebSocket (`ws://localhost:8000/ws`)

Pushes JSON every second while connected:
```json
{
  "session_state": "running",
  "session_id": 1,
  "elapsed_sec": 420.5,
  "planned_duration_sec": 1500,
  "current_activities": ["sitting", "laptop"],
  "active_app": {
    "name": "Code.exe",
    "title": "main.py - VS Code"
  }
}
```

---

## Running Automated Tests

Run the complete test suite across all 7 phases:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m unittest discover -s . -p "tests_*.py"
```

Typecheck and build the frontend:
```powershell
cd frontend
npx tsc --noEmit
npm run build
```
