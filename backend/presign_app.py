# presign_app.py
import os, time, uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import boto3

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BUCKET = os.getenv("S3_BUCKET", "vittcott-uploads-xyz123")   # ← replace if needed
DDB_TABLE = os.getenv("DDB_TABLE", "user_files")  # optional

s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

app = FastAPI()
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:8501",
    "http://127.0.0.1:8000",
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PresignReq(BaseModel):
    filename: str
    content_type: str
    username: str

@app.post("/presign")
def presign(req: PresignReq):
    key = f"users/{req.username}/{int(time.time())}_{uuid.uuid4().hex}_{req.filename}"
    # limit file size to 10 MB — change if you want
    conditions = [
        ["content-length-range", 0, 10 * 1024 * 1024],
        {"Content-Type": req.content_type},
    ]
    fields = {"Content-Type": req.content_type}
    try:
        presigned = s3.generate_presigned_post(
            Bucket=BUCKET,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"url": presigned["url"], "fields": presigned["fields"], "key": key}

@app.post("/register")
def register(payload: dict):
    try:
        username = payload["username"]
        s3_key = payload["s3_key"]
        filename = payload.get("filename", "")
        size = int(payload.get("size", 0))
    except Exception:
        raise HTTPException(status_code=400, detail="missing fields")

    item = {
        "username": username,
        "uploaded_at": int(time.time()),
        "s3_key": s3_key,
        "filename": filename,
        "size": size
    }

    # write to DynamoDB if table available (safe to skip in dev)
    try:
        table = dynamodb.Table(DDB_TABLE)
        table.put_item(Item=item)
    except Exception as e:
        print("DynamoDB write error (ignored in dev):", e)

    # presigned GET for convenience
    try:
        download_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": s3_key},
            ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"couldn't make download url: {e}")

    return {"ok": True, "download_url": download_url, "s3_key": s3_key}
