# Telemetry Collector Fix

## Problem
The telemetry collector was configured to send data to `http://127.0.0.1:8002`, but:
- The FastAPI server runs on port 8000, not 8002
- Port 8002 doesn't exist, causing continuous connection failures
- The collector was falling back to local buffering instead of sending telemetry

## Solution Applied

### 1. Added Configuration (`backend/app/config.py`)
- Added `COLLECTOR_API_URL` configuration setting
- Default to `http://127.0.0.1:8000` (main FastAPI port)
- Allow override via environment variable for cloud deployments

### 2. Updated Collector (`backend/app/collector/run_collector.py`)
- Changed from hardcoded `http://127.0.0.1:8002` to use `settings.COLLECTOR_API_URL`
- Now uses the correct port by default

### 3. Updated Environment Template (`.env.example`)
- Added `COLLECTOR_API_URL` with default value
- Added documentation for cloud deployment usage

## Required Render Environment Variable

**Add this to your Render environment variables:**
```
COLLECTOR_API_URL=https://aquarack.onrender.com
```

## Why This Fix Works

### Before (Broken):
```
Collector → http://127.0.0.1:8002 → ❌ Connection refused
FastAPI → http://0.0.0.0:8000 → ✅ Running
```

### After (Fixed):
```
Collector → http://127.0.0.1:8000 → ✅ Connected (local)
Collector → https://aquarack.onrender.com → ✅ Connected (cloud)
FastAPI → http://0.0.0.0:8000 → ✅ Running
```

## Deployment Instructions

1. **Add the environment variable** in Render dashboard:
   - Key: `COLLECTOR_API_URL`
   - Value: `https://aquarack.onrender.com`

2. **Redeploy** - The git push will trigger automatic deployment

3. **Verify** - Check logs for successful telemetry ingestion instead of "Buffering reading locally"

## Expected Result After Fix

Instead of:
```
WARNING: Ingestion API unreachable: HTTPConnectionPool(host='127.0.0.1', port=8002)
INFO: Buffering reading locally (API unreachable)
```

You should see:
```
INFO: Telemetry sent successfully to ingestion API
```

## Files Changed
- `backend/app/config.py` - Added COLLECTOR_API_URL setting
- `backend/app/collector/run_collector.py` - Use configured API URL
- `.env.example` - Added documentation and default value