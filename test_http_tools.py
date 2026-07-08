import os
import time
import threading
import pytest
from tools.http import (
    http_get,
    http_post,
    http_put,
    http_delete,
    download_file,
    upload_file
)
import uvicorn
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import Response, JSONResponse

app = FastAPI()

@app.get("/")
def get_root():
    return {"status": "ok"}

@app.get("/query")
def get_query(q: str):
    return {"q": q}

@app.get("/timeout")
def get_timeout():
    time.sleep(2.0)
    return {"status": "ok"}

@app.get("/binary")
def get_binary():
    return Response(content=b"\x00\x01\x02\x03", media_type="application/octet-stream")

@app.post("/post")
async def post_data(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return {"received": await request.json()}
    else:
        return {"received": (await request.body()).decode()}

@app.put("/put")
async def put_data(request: Request):
    return {"received": (await request.body()).decode()}

@app.delete("/delete")
def delete_data():
    return {"deleted": True}

@app.get("/404")
def not_found():
    return Response(status_code=404)

@app.get("/500")
def internal_error():
    return Response(status_code=500)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}

@app.put("/upload_raw")
async def upload_raw(request: Request):
    content = await request.body()
    return {"size": len(content)}

@pytest.fixture(scope="module", autouse=True)
def test_server():
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8123, log_level="critical")
        
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(1.0) # give server time to start
    yield

def test_http_get():
    res = http_get("http://127.0.0.1:8123/")
    assert res.get("status_code") == 200
    assert res.get("response_type") == "json"
    assert res.get("body") == {"status": "ok"}

def test_http_get_query():
    res = http_get("http://127.0.0.1:8123/query", params={"q": "hello"})
    assert res.get("status_code") == 200
    assert res.get("body") == {"q": "hello"}

def test_http_get_binary():
    res = http_get("http://127.0.0.1:8123/binary")
    assert res.get("status_code") == 200
    assert res.get("response_type") == "binary"

def test_http_get_404():
    res = http_get("http://127.0.0.1:8123/404")
    assert res.get("error") == "HTTP error"

def test_http_timeout():
    res = http_get("http://127.0.0.1:8123/timeout", timeout=0.5)
    assert "timeout" in res.get("error", "").lower()

def test_invalid_url():
    res = http_get("http://invalid.domain.that.doesnt.exist.com.123")
    assert "error" in res

def test_http_post_json():
    res = http_post("http://127.0.0.1:8123/post", json={"hello": "world"})
    assert res.get("status_code") == 200
    assert res.get("body") == {"received": {"hello": "world"}}

def test_http_put():
    res = http_put("http://127.0.0.1:8123/put", content="raw text")
    assert res.get("status_code") == 200
    assert res.get("body") == {"received": "raw text"}

def test_http_delete():
    res = http_delete("http://127.0.0.1:8123/delete")
    assert res.get("status_code") == 200
    assert res.get("body") == {"deleted": True}

def test_download_file(tmp_path):
    target = str(tmp_path / "downloaded.bin")
    res = download_file("http://127.0.0.1:8123/binary", target)
    assert res.get("success") is True
    assert res.get("size_bytes") == 4
    assert os.path.exists(target)
    with open(target, "rb") as f:
        assert f.read() == b"\x00\x01\x02\x03"

def test_download_file_max_size(tmp_path):
    target = str(tmp_path / "downloaded.bin")
    res = download_file("http://127.0.0.1:8123/binary", target, max_size_bytes=2)
    assert "exceeds maximum" in res.get("error", "").lower() or "exceeded maximum" in res.get("error", "").lower()

def test_download_file_no_overwrite(tmp_path):
    target = str(tmp_path / "downloaded.bin")
    with open(target, "wb") as f:
        f.write(b"existing")
        
    res = download_file("http://127.0.0.1:8123/binary", target)
    assert "already exists" in res.get("error", "")

def test_upload_file(tmp_path):
    source = str(tmp_path / "to_upload.txt")
    with open(source, "w") as f:
        f.write("hello upload")
        
    res = upload_file("http://127.0.0.1:8123/upload", source)
    assert res.get("status_code") == 200
    assert res.get("body").get("size") == 12
    assert res.get("body").get("filename") == "to_upload.txt"

def test_upload_file_raw(tmp_path):
    source = str(tmp_path / "to_upload.txt")
    with open(source, "w") as f:
        f.write("hello upload raw")
        
    res = upload_file("http://127.0.0.1:8123/upload_raw", source, method="PUT", raw=True)
    assert res.get("status_code") == 200
    assert res.get("body").get("size") == 16
