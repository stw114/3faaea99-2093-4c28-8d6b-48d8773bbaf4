# Implementation Plan - CSI300 AI Scanner Web App

# Goal Description
Convert the existing local Python script `csi300_scanner.py` into a modern, premium-looking web application. The app will allow users to view the latest analysis results (Bull/Bear signals) in a dashboard format and trigger new scans.

## User Review Required
> [!IMPORTANT]
> The scanning process is time-consuming (fetching data for 300 stocks). The web app will primarily display the *latest* available result. A "Scan Now" feature will run in the background, but users should not expect instant results.

## Proposed Changes

### Project Structure
I will create a new project at `/Users/ag9172/.gemini/antigravity/scratch/csi300_web` with the following structure:

```
csi300_web/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── scanner.py       # Refactored logic from csi300_scanner.py
│   └── requirements.txt # Dependencies
├── frontend/
│   ├── index.html       # Main dashboard
│   ├── style.css        # Premium styling
│   └── script.js        # Frontend logic
└── results/             # Directory to store CSV results
```

### Backend
#### [NEW] [scanner.py](file:///Users/ag9172/.gemini/antigravity/scratch/csi300_web/backend/scanner.py)
- Adapt the existing `csi300_scanner.py` logic.
- Expose a `run_scan_async()` function that runs in a separate thread/process.
- Save results to `results/latest.csv` and a timestamped file.

#### [NEW] [main.py](file:///Users/ag9172/.gemini/antigravity/scratch/csi300_web/backend/main.py)
- **FastAPI** app.
- `GET /api/results`: Returns the JSON data from the latest CSV.
- `POST /api/scan`: Triggers a new scan (if not already running).
- `GET /api/status`: Returns current scan status (Idle/Scanning, Progress).
- Serve static files from `../frontend`.

### Frontend
#### [NEW] [index.html](file:///Users/ag9172/.gemini/antigravity/scratch/csi300_web/frontend/index.html)
- Dashboard layout.
- **Header**: Title and "Scan Now" button.
- **Stats Cards**: Summary of market sentiment (Bull vs Bear count).
- **Data Table**: List of stocks with "Bull" signals highlighted.

#### [NEW] [style.css](file:///Users/ag9172/.gemini/antigravity/scratch/csi300_web/frontend/style.css)
- **Theme**: Dark, modern, financial terminal aesthetic.
- **Colors**: Deep blues/blacks for background, neon green/red for signals.
- **Effects**: Glassmorphism, hover effects, smooth transitions.

#### [NEW] [script.js](file:///Users/ag9172/.gemini/antigravity/scratch/csi300_web/frontend/script.js)
- Fetch data from `/api/results` on load.
- Render table and charts/cards.
- Handle "Scan Now" button click and poll `/api/status`.

## Verification Plan

### Automated Tests
- None planned for this rapid prototype, as it relies on external live financial data (AkShare) which is flaky to mock in this context.

### Manual Verification
1. **Setup**: Install dependencies (`fastapi`, `uvicorn`, `pandas`, `torch`, `akshare`).
2. **Run**: Start server with `uvicorn backend.main:app --reload`.
3. **View**: Open `http://localhost:8000`.
4. **Test Data Display**: Ensure mock/real data loads in the table.
5. **Test Scanning**: Click "Scan Now", check terminal for logs, wait for completion (or test with a small subset of stocks for speed), and verify UI updates.
