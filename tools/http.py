import httpx
import os
import asyncio
from typing import Dict, Any, Optional

def _handle_httpx_exception(e: Exception) -> Dict[str, Any]:
    if isinstance(e, httpx.ConnectTimeout) or isinstance(e, httpx.ReadTimeout) or isinstance(e, httpx.WriteTimeout) or isinstance(e, httpx.PoolTimeout):
        return {"error": "Connection timeout", "details": str(e)}
    elif isinstance(e, httpx.ConnectError):
        return {"error": "Connection error (DNS failure or network unavailable)", "details": str(e)}
    elif isinstance(e, httpx.TooManyRedirects):
        return {"error": "Redirect loop detected", "details": str(e)}
    elif isinstance(e, httpx.InvalidURL):
        return {"error": "Invalid URL", "details": str(e)}
    elif isinstance(e, httpx.HTTPError):
        return {"error": "HTTP error", "details": str(e)}
    else:
        return {"error": f"Unexpected error: {str(e)}"}

def _format_response(response: httpx.Response) -> Dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    
    body = None
    response_type = "text"
    
    if "application/json" in content_type.lower():
        try:
            body = response.json()
            response_type = "json"
        except Exception:
            body = response.text
    elif content_type.lower().startswith("text/"):
        body = response.text
    elif "application/octet-stream" in content_type.lower() or "image/" in content_type.lower() or "video/" in content_type.lower() or "audio/" in content_type.lower() or "application/zip" in content_type.lower() or "application/pdf" in content_type.lower():
        body = "<binary data>"
        response_type = "binary"
    else:
        try:
            body = response.content.decode('utf-8')
            if '\x00' in body:
                raise ValueError("Binary content")
        except Exception:
            body = "<binary data>"
            response_type = "binary"

    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body,
        "response_type": response_type,
        "url": str(response.url)
    }

async def _async_http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0, allow_redirects: bool = True) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=allow_redirects) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return _format_response(response)
    except Exception as e:
        return _handle_httpx_exception(e)

def http_get(*args, **kwargs) -> Dict[str, Any]:
    """Perform an HTTP GET request."""
    return asyncio.run(_async_http_get(*args, **kwargs))

async def _async_http_post(url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, content: Optional[str] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if content:
                response = await client.post(url, content=content.encode('utf-8'), headers=headers)
            else:
                response = await client.post(url, json=json, data=data, headers=headers)
            response.raise_for_status()
            return _format_response(response)
    except Exception as e:
        return _handle_httpx_exception(e)

def http_post(*args, **kwargs) -> Dict[str, Any]:
    """Perform an HTTP POST request."""
    return asyncio.run(_async_http_post(*args, **kwargs))

async def _async_http_put(url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, content: Optional[str] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if content:
                response = await client.put(url, content=content.encode('utf-8'), headers=headers)
            else:
                response = await client.put(url, json=json, data=data, headers=headers)
            response.raise_for_status()
            return _format_response(response)
    except Exception as e:
        return _handle_httpx_exception(e)

def http_put(*args, **kwargs) -> Dict[str, Any]:
    """Perform an HTTP PUT request."""
    return asyncio.run(_async_http_put(*args, **kwargs))

async def _async_http_delete(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return _format_response(response)
    except Exception as e:
        return _handle_httpx_exception(e)

def http_delete(*args, **kwargs) -> Dict[str, Any]:
    """Perform an HTTP DELETE request."""
    return asyncio.run(_async_http_delete(*args, **kwargs))

async def _async_download_file(url: str, path: str, timeout: float = 60.0, max_size_bytes: Optional[int] = None, overwrite: bool = False) -> Dict[str, Any]:
    if os.path.exists(path) and not overwrite:
        return {"error": f"File {path} already exists. Use overwrite=True to overwrite."}

    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                content_length = response.headers.get("Content-Length")
                if content_length and max_size_bytes and int(content_length) > max_size_bytes:
                    return {"error": f"File size ({content_length} bytes) exceeds maximum allowed size ({max_size_bytes} bytes)."}

                downloaded_size = 0
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        downloaded_size += len(chunk)
                        if max_size_bytes and downloaded_size > max_size_bytes:
                            # Clean up partial file
                            os.remove(path)
                            return {"error": f"Download exceeded maximum allowed size ({max_size_bytes} bytes)."}
                        f.write(chunk)
                        
                return {
                    "success": True,
                    "path": path,
                    "size_bytes": downloaded_size,
                    "content_type": response.headers.get("content-type", "")
                }
    except PermissionError:
        return {"error": f"Permission denied when writing to {path}"}
    except Exception as e:
        return _handle_httpx_exception(e)

def download_file(*args, **kwargs) -> Dict[str, Any]:
    """Download a file from a URL to a local path."""
    return asyncio.run(_async_download_file(*args, **kwargs))

async def _async_upload_file(url: str, path: str, method: str = "POST", field_name: str = "file", headers: Optional[Dict[str, str]] = None, timeout: float = 60.0, raw: bool = False) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"error": f"Local file {path} not found."}
        
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            with open(path, "rb") as f:
                file_content = f.read()
                
            if raw:
                if method.upper() == "PUT":
                    response = await client.put(url, content=file_content, headers=headers)
                else:
                    response = await client.post(url, content=file_content, headers=headers)
            else:
                files = {field_name: (os.path.basename(path), file_content)}
                if method.upper() == "PUT":
                    response = await client.put(url, files=files, headers=headers)
                else:
                    response = await client.post(url, files=files, headers=headers)
                    
            response.raise_for_status()
            return _format_response(response)
    except PermissionError:
        return {"error": f"Permission denied when reading from {path}"}
    except Exception as e:
        return _handle_httpx_exception(e)

def upload_file(*args, **kwargs) -> Dict[str, Any]:
    """Upload a local file to a URL."""
    return asyncio.run(_async_upload_file(*args, **kwargs))
