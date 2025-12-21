"""
caller_api.py - PRODUCTION READY VERSION
Cloud API Server for Render Deployment
======================================================
API riêng để nhận request từ frontend, gửi về local server qua Tailscale
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging
import os
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

# ===== Configuration =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ FIX: Thêm port 8003 vào URL
LOCAL_SERVERS = os.getenv("LOCAL_SERVERS", "").split(",")
if not LOCAL_SERVERS or LOCAL_SERVERS == [""]:
    LOCAL_SERVERS = [
        "http://100.125.241.20:8003"  # ✅ Phải có :8003
    ]

# Request timeout
REQUEST_TIMEOUT = 180.0  # 3 phút cho việc generate GLB
HEALTH_CHECK_TIMEOUT = 5.0  # 5s cho health check

# ===== Request Models =====
class SignRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

class ServerStatus(BaseModel):
    url: str
    status: str
    response_time_ms: Optional[float] = None
    last_check: str
    error: Optional[str] = None

# ===== Server Health Tracking =====
server_health: dict[str, ServerStatus] = {}
current_server_index = 0

async def check_server_health(server_url: str) -> bool:
    """Kiểm tra health của local server"""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            start = datetime.now()
            
            # ✅ Gọi đúng endpoint
            response = await client.get(f"{server_url}/api/sign/health")
            
            elapsed_ms = (datetime.now() - start).total_seconds() * 1000
            
            if response.status_code == 200:
                server_health[server_url] = ServerStatus(
                    url=server_url,
                    status="healthy",
                    response_time_ms=elapsed_ms,
                    last_check=datetime.now().isoformat()
                )
                logger.info(f"✅ Server {server_url} is healthy ({elapsed_ms:.0f}ms)")
                return True
            
            server_health[server_url] = ServerStatus(
                url=server_url,
                status="unhealthy",
                last_check=datetime.now().isoformat(),
                error=f"Status code: {response.status_code}"
            )
            logger.warning(f"⚠️ Server {server_url} unhealthy: {response.status_code}")
            return False
            
    except httpx.TimeoutException:
        logger.error(f"⏱️ Server {server_url} timeout")
        server_health[server_url] = ServerStatus(
            url=server_url,
            status="timeout",
            last_check=datetime.now().isoformat(),
            error="Health check timeout"
        )
        return False
        
    except httpx.ConnectError as e:
        logger.error(f"🔌 Server {server_url} connection failed: {e}")
        server_health[server_url] = ServerStatus(
            url=server_url,
            status="unreachable",
            last_check=datetime.now().isoformat(),
            error=f"Connection error: {str(e)}"
        )
        return False
        
    except Exception as e:
        logger.error(f"❌ Server {server_url} health check failed: {e}")
        server_health[server_url] = ServerStatus(
            url=server_url,
            status="down",
            last_check=datetime.now().isoformat(),
            error=str(e)
        )
        return False

async def get_healthy_server() -> Optional[str]:
    """Lấy server khỏe mạnh đầu tiên"""
    global current_server_index
    
    # Round-robin qua các servers
    for i in range(len(LOCAL_SERVERS)):
        server_url = LOCAL_SERVERS[(current_server_index + i) % len(LOCAL_SERVERS)]
        
        if await check_server_health(server_url):
            current_server_index = (current_server_index + i) % len(LOCAL_SERVERS)
            logger.info(f"✅ Using server: {server_url}")
            return server_url
    
    logger.error("❌ No healthy servers available")
    return None

async def proxy_to_local_server(
    endpoint: str,
    method: str = "POST",
    **kwargs
) -> httpx.Response:
    """Proxy request đến local server qua Tailscale"""
    
    # Tìm server khỏe mạnh
    server_url = await get_healthy_server()
    
    if not server_url:
        raise HTTPException(
            status_code=503,
            detail="All local servers are unavailable"
        )
    
    url = f"{server_url}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            logger.info(f"📡 Proxying to: {url}")
            
            if method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "GET":
                response = await client.get(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            logger.info(f"✅ Response: {response.status_code}")
            return response
            
    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout connecting to {url}")
        raise HTTPException(status_code=504, detail="Local server timeout")
    
    except httpx.RequestError as e:
        logger.error(f"❌ Connection error to {url}: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to local server: {str(e)}")

# ===== Lifespan Management (✅ FIXED: Use modern lifespan) =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("🚀 Cloud API starting up...")
    logger.info(f"📍 Local servers: {LOCAL_SERVERS}")
    
    # Kiểm tra health ban đầu
    tasks = [check_server_health(server_url) for server_url in LOCAL_SERVERS]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    yield
    
    # Shutdown
    logger.info("👋 Cloud API shutting down...")

# ===== FastAPI App =====
app = FastAPI(
    title="Sign Language Cloud API",
    description="Cloud API Gateway to Local Sign Motion Servers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # ✅ FIXED: Use lifespan instead of on_event
)

# CORS - Cho phép frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: thay bằng domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== API Endpoints =====

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Sign Language Cloud API",
        "version": "1.0.0",
        "status": "running",
        "local_servers": LOCAL_SERVERS,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check cho cloud API và local servers"""
    
    # Kiểm tra tất cả servers
    health_checks = []
    for server_url in LOCAL_SERVERS:
        is_healthy = await check_server_health(server_url)
        health_checks.append({
            "server": server_url,
            "healthy": is_healthy,
            "details": server_health.get(server_url).dict() if server_url in server_health else None
        })
    
    any_healthy = any(check["healthy"] for check in health_checks)
    
    return {
        "caller_api": "healthy",
        "local_servers": health_checks,
        "overall_status": "healthy" if any_healthy else "degraded",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/generate-sign")
async def generate_sign(request: SignRequest):
    """
    Generate sign language animation
    Proxy request đến local server qua Tailscale
    
    Response: GLB file stream
    """
    try:
        logger.info(f"📥 Received request: {request.text}")
        
        # Proxy đến local server
        response = await proxy_to_local_server(
            endpoint="/api/sign/render-stream",
            method="POST",
            json={
                "text": request.text
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Local server error: {response.text}"
            )
        
        # Stream GLB về frontend
        logger.info("✅ Streaming GLB to frontend")
        
        return StreamingResponse(
            response.iter_bytes(),
            media_type="model/gltf-binary",
            headers={
                "Content-Disposition": response.headers.get(
                    "Content-Disposition", 
                    'attachment; filename="sign.glb"'
                ),
                "X-Duration": response.headers.get("X-Duration", "0"),
                "X-Glosses": response.headers.get("X-Glosses", ""),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-sign-metadata")
async def generate_sign_metadata(request: SignRequest):
    """
    Generate sign và trả về metadata (không stream file)
    Phù hợp cho việc tracking và logging
    """
    try:
        logger.info(f"📥 Metadata request: {request.text}")
        
        response = await proxy_to_local_server(
            endpoint="/api/sign/render",
            method="POST",
            json={
                "text": request.text
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Local server error: {response.text}"
            )
        
        return response.json()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Metadata generation failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/servers/status")
async def get_servers_status():
    """Xem trạng thái của tất cả local servers"""
    
    statuses = []
    for server_url in LOCAL_SERVERS:
        await check_server_health(server_url)
        status_obj = server_health.get(server_url)
        if status_obj:
            statuses.append(status_obj.dict())
    
    healthy_count = sum(1 for s in statuses if s.get("status") == "healthy")
    
    return {
        "servers": statuses,
        "total_servers": len(LOCAL_SERVERS),
        "healthy_servers": healthy_count,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/test-gloss")
async def test_gloss(request: SignRequest):
    """
    Test gloss có tồn tại không (proxy to local server)
    """
    try:
        response = await proxy_to_local_server(
            endpoint="/api/sign/test-gloss",
            method="POST",
            json={"text": request.text}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Local server error: {response.text}"
            )
        
        return response.json()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Test gloss failed")
        raise HTTPException(status_code=500, detail=str(e))

# ===== Run Server =====
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("🚀 Sign Language Cloud API")
    print("=" * 60)
    print(f"📍 Port: {port}")
    print(f"🌐 Local Servers (Tailscale):")
    for server in LOCAL_SERVERS:
        print(f"   - {server}")
    print(f"📖 Docs: http://localhost:{port}/docs")
    print("=" * 60)
    
    uvicorn.run(
        "caller_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )