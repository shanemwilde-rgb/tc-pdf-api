# TC PDF API

Flask API that fills the Utah Addendum to REPC PDF with transaction data.

## Deploy to Render (free)

1. Create a free account at render.com
2. Click **New** → **Web Service**
3. Choose **"Deploy from existing repository"** → connect GitHub
   OR choose **"Manual deploy"** and upload this folder as a zip
4. Settings:
   - **Name**: tc-pdf-api
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
   - **Instance type**: Free
5. Click **Deploy**
6. Your API URL will be: `https://tc-pdf-api.onrender.com`

## Endpoints

### GET /health
Returns `{"status": "ok"}` — use to verify deployment.

### POST /fill-addendum
Fills the blank Addendum to REPC PDF and returns a filled PDF.

**Request body (JSON):**
```json
{
  "addendum_no": "1",
  "buyer": "Chase & Olive Nielsen",
  "seller": "John & Jane Smith",
  "property": "123 Main St, Fairview, UT 84629",
  "offer_date": "February 11, 2026",
  "terms": "Buyer and Seller agree to extend the Due Diligence Deadline by 5 days...",
  "response_date": "March 24, 2026",
  "response_time": "5:00 PM",
  "response_party": "Seller"
}
```

**Response:** PDF file (application/pdf)
