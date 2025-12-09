# How to Share Your CSI300 Web App

Currently, your app is running locally on your computer (`localhost`). To let others access it over the internet, you have two main options:

## Option 1: Quick Sharing with `ngrok` (Recommended for Demos)
This is the easiest way to temporarily share your running app with a friend or colleague.

### Steps
1.  **Install ngrok**:
    - Go to [ngrok.com](https://ngrok.com) and sign up (it's free).
    - Download and install ngrok for your OS.
    - Connect your account: `ngrok config add-authtoken <YOUR_TOKEN>`

2.  **Start your App**:
    Ensure your FastAPI app is running locally:
    ```bash
    cd /Users/ag9172/.gemini/antigravity/scratch/csi300_web/backend
    python3 -m uvicorn main:app --reload --port 8000
    ```

3.  **Expose to Internet**:
    Open a *new* terminal window and run:
    ```bash
    ngrok http 8000
    ```

4.  **Share the Link**:
    ngrok will generate a URL like `https://a1b2-c3d4.ngrok-free.app`. Send this URL to anyone, and they can access your app!

> [!NOTE]
> This link only works as long as your computer is on and the `ngrok` command is running.

---

## Option 2: Permanent Cloud Hosting (Recommended for Production)
If you want the app to be available 24/7 without your computer running, you should deploy it to a cloud provider like **Render** or **Railway**.

### Steps for Render.com (Free Tier available)

1.  **Push Code to GitHub**:
    - Create a GitHub repository.
    - Push your `csi300_web` folder to it.

2.  **Create Web Service on Render**:
    - Sign up at [render.com](https://render.com).
    - Click "New +", select "Web Service".
    - Connect your GitHub repo.

3.  **Configure Settings**:
    - **Runtime**: Python 3
    - **Build Command**: `pip install -r backend/requirements.txt`
    - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

4.  **Deploy**:
    - Click "Create Web Service". Render will build and deploy your app.
    - You will get a permanent URL like `https://csi300-scanner.onrender.com`.

> [!IMPORTANT]
> Since your app saves data to a local CSV file (`results/latest.csv`), on free cloud tiers (which restart often), **you will lose historical data** on every restart. For a production app, you should use a database (like PostgreSQL) or cloud storage (like AWS S3) to save the results.
