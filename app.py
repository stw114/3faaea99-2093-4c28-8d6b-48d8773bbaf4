import os
import time
import threading
import pandas as pd
import akshare as ak
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime

# --- Configuration ---
RESULTS_DIR = "results"
LATEST_RESULTS_FILE = os.path.join(RESULTS_DIR, "latest.csv")
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Scanner Logic ---
class Scanner:
    def __init__(self):
        self.is_scanning = False
        self.last_scan_time = None
        self.status = "Idle"
        self.progress = 0
        self.total_stocks = 300

    def get_csi300_stocks(self):
        """Fetches the list of CSI300 stocks."""
        try:
            # AkShare function to get CSI300 constituents
            # Note: This API might change, using a standard one
            stock_cons = ak.index_stock_cons(symbol="000300")
            return stock_cons
        except Exception as e:
            print(f"Error fetching CSI300 list: {e}")
            # Fallback mock data if API fails
            return pd.DataFrame({
                "symbol": ["000001", "600519", "000858"],
                "name": ["Ping An Bank", "Kweichow Moutai", "Wuliangye"],
                "exchange": ["SZSE", "SHSE", "SZSE"]
            })

    def analyze_stock(self, code, name):
        """
        Placeholder for the AI/Technical Analysis logic.
        TODO: Replace this with your actual PyTorch model or technical indicators.
        """
        # Mock logic: Random Bull/Bear signal based on hash of code + time
        import random
        signal_score = random.random()
        
        if signal_score > 0.7:
            signal = "Bull"
            confidence = round(signal_score * 100, 2)
        elif signal_score < 0.3:
            signal = "Bear"
            confidence = round((1 - signal_score) * 100, 2)
        else:
            signal = "Neutral"
            confidence = round(random.uniform(40, 60), 2)
            
        return {
            "code": code,
            "name": name,
            "signal": signal,
            "confidence": confidence,
            "price": round(random.uniform(10, 2000), 2), # Mock price
            "change_percent": round(random.uniform(-5, 5), 2) # Mock change
        }

    def run_scan(self):
        if self.is_scanning:
            return
        
        self.is_scanning = True
        self.status = "Scanning..."
        self.progress = 0
        
        try:
            print("Starting CSI300 Scan...")
            stocks = self.get_csi300_stocks()
            results = []
            
            total = len(stocks)
            self.total_stocks = total
            
            for i, row in stocks.iterrows():
                code = row['symbol']
                name = row['name'] if 'name' in row else row['stock_name']
                
                # Simulate analysis time
                time.sleep(0.05) 
                
                result = self.analyze_stock(code, name)
                results.append(result)
                
                self.progress = int((i + 1) / total * 100)
            
            # Save results
            df = pd.DataFrame(results)
            df.to_csv(LATEST_RESULTS_FILE, index=False)
            
            # Also save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_csv(os.path.join(RESULTS_DIR, f"scan_{timestamp}.csv"), index=False)
            
            self.last_scan_time = datetime.now().isoformat()
            self.status = "Completed"
            print("Scan completed.")
            
        except Exception as e:
            print(f"Scan failed: {e}")
            self.status = f"Failed: {str(e)}"
        finally:
            self.is_scanning = False

scanner = Scanner()

# --- FastAPI App ---
app = FastAPI(title="CSI300 AI Scanner")

# Mount static files (Frontend)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

@app.get("/api/status")
async def get_status():
    return {
        "status": scanner.status,
        "progress": scanner.progress,
        "is_scanning": scanner.is_scanning,
        "last_scan": scanner.last_scan_time
    }

@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    if scanner.is_scanning:
        return {"message": "Scan already in progress"}
    
    background_tasks.add_task(scanner.run_scan)
    return {"message": "Scan started"}

@app.get("/api/results")
async def get_results():
    if not os.path.exists(LATEST_RESULTS_FILE):
        return {"results": []}
    
    df = pd.read_csv(LATEST_RESULTS_FILE)
    return {"results": df.to_dict(orient="records")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
