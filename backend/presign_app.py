# presign_app.py
import os
import time
import uuid
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import boto3
from botocore.config import Config

# ---- CONFIG / LOGGING ----
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Force region defaults for the running process (important)
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
os.environ.setdefault("AWS_DEFAULT_REGION", AWS_REGION)

BUCKET = os.getenv("S3_BUCKET", "vittcott-uploads-xyz123")
DDB_TABLE = os.getenv("DDB_TABLE", "user_files")

# Ensure SigV4 and explicit region
boto_config = Config(region_name=AWS_REGION, signature_version="s3v4")
s3 = boto3.client("s3", region_name=AWS_REGION, config=boto_config)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

# ---- FASTAPI APP ----
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
        log.exception("Error generating presigned POST")
        raise HTTPException(status_code=500, detail=str(e))

    # DEBUG: log the returned url and credential so you can inspect region in the signature
    log.info("presign url: %s", presigned.get("url"))
    # X-Amz-Credential may appear under keys like "X-Amz-Credential" or "x-amz-credential"
    x_cred = presigned.get("fields", {}).get("X-Amz-Credential") \
             or presigned.get("fields", {}).get("x-amz-credential")
    log.info("presign X-Amz-Credential: %s", x_cred)

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
        log.warning("DynamoDB write error (ignored in dev): %s", e)

    # presigned GET for convenience
    try:
        download_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": s3_key},
            ExpiresIn=3600
        )
    except Exception as e:
        log.exception("Error generating download URL")
        raise HTTPException(status_code=500, detail=f"couldn't make download url: {e}")

    return {"ok": True, "download_url": download_url, "s3_key": s3_key}

# ---- TEMP DEBUG ENDPOINT (safe: no secrets) ----
@app.get("/_aws_debug")
def aws_debug():
    import boto3
    sess = boto3.session.Session()
    creds = sess.get_credentials()
    cred_id_masked = None
    if creds and creds.access_key:
        ak = creds.access_key
        cred_id_masked = ak[:4] + "..." + ak[-4:]
    return {
        "env_AWS_REGION": os.getenv("AWS_REGION"),
        "env_AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
        "boto3_session_region": sess.region_name,
        "aws_access_key_id_masked": cred_id_masked
    }
