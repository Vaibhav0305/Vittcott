# test_upload.py (safe re-run)
import requests, os
from openpyxl import Workbook

PRESIGN = "http://127.0.0.1:8000/presign"
REGISTER = "http://127.0.0.1:8000/register"
USERNAME = "testuser"
FNAME = "sample_portfolio.xlsx"

# create Excel again if missing
if not os.path.exists(FNAME):
    wb = Workbook()
    ws = wb.active
    ws.title = "Portfolio"
    ws.append(["symbol","qty","price"])
    ws.append(["RELI", 10, 2350])
    ws.append(["TCS", 5, 3200])
    wb.save(FNAME)
    print("Created:", FNAME)

print("Requesting presigned POST...")
resp = requests.post(PRESIGN, json={
    "filename": FNAME,
    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "username": USERNAME
})
print("presign status:", resp.status_code)
print(resp.text)
resp.raise_for_status()
presign = resp.json()

print("Uploading to S3 (this may return 204)...")
with open(FNAME, "rb") as f:
    files = {"file": (FNAME, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = presign["fields"]
    r = requests.post(presign["url"], data=data, files=files)
print("S3 upload status code:", r.status_code)
if r.status_code not in (200,201,204):
    print("S3 upload response body:", r.text)
    raise SystemExit("Upload failed")

print("Registering metadata...")
reg = requests.post(REGISTER, json={
    "username": USERNAME,
    "s3_key": presign["key"],
    "filename": FNAME,
    "size": os.path.getsize(FNAME)
})
print("register status:", reg.status_code)
print(reg.text)
reg.raise_for_status()
print("Done. Download URL (from register):", reg.json().get("download_url"))
