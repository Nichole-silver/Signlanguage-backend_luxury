"""
test_connection.py
Test kết nối Cloud API → Local Server qua Tailscale

"""

import httpx
import asyncio
from pathlib import Path

# ===== Config =====
CLOUD_API_URL = "http://localhost:8000"  # Khi test local
# CLOUD_API_URL = "https://your-app.onrender.com"  # Khi deploy

async def test_health():
    """Test health check"""
    print("\n🔍 Testing Health Check...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{CLOUD_API_URL}/health")
            print(f"✅ Status: {response.status_code}")
            print(f"📊 Response: {response.json()}")
            return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False

async def test_servers_status():
    """Test server status endpoint"""
    print("\n🔍 Testing Servers Status...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{CLOUD_API_URL}/api/servers/status")
            print(f"✅ Status: {response.status_code}")
            
            data = response.json()
            print(f"📊 Total Servers: {data['total_servers']}")
            print(f"✅ Healthy Servers: {data['healthy_servers']}")
            
            for server in data['servers']:
                status_icon = "✅" if server.get("status") == "healthy" else "❌"
                print(f"   {status_icon} {server.url}: {server.get("status")}")
            
            return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False

async def test_generate_sign(text: str = "hello world"):
    """Test sign generation"""
    print(f"\n🔍 Testing Sign Generation: '{text}'...")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                f"{CLOUD_API_URL}/api/generate-sign",
                json={"text": text}
            )
            
            if response.status_code == 200:
                print(f"✅ Generation successful!")
                
                # Lấy metadata từ headers
                duration = response.headers.get('X-Duration')
                glosses = response.headers.get('X-Glosses')
                content_disp = response.headers.get('Content-Disposition')
                
                print(f"⏱️  Duration: {duration}s")
                print(f"📝 Glosses: {glosses}")
                print(f"📦 Filename: {content_disp}")
                
                # Lưu file GLB
                output_file = Path(f"test_output_{text.replace(' ', '_')}.glb")
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                file_size_kb = output_file.stat().st_size / 1024
                print(f"💾 Saved to: {output_file} ({file_size_kb:.1f} KB)")
                
                return True
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False

async def test_generate_metadata(text: str = "hello"):
    """Test metadata-only generation"""
    print(f"\n🔍 Testing Metadata Generation: '{text}'...")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                f"{CLOUD_API_URL}/api/generate-sign-metadata",
                json={"text": text}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(f"📝 Glosses: {data['glosses']}")
                print(f"⏱️  Duration: {data['duration']}s")
                print(f"🗄️  MongoDB ID: {data['mongodb_id']}")
                return True
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False

async def run_all_tests():
    """Chạy tất cả tests"""
    print("=" * 60)
    print("🧪 Sign Language Cloud API - Connection Tests")
    print("=" * 60)
    print(f"🌐 API URL: {CLOUD_API_URL}")
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", await test_health()))
    
    # Test 2: Server Status
    results.append(("Server Status", await test_servers_status()))
    
    # Test 3: Generate Sign (Stream)
    results.append(("Generate Sign", await test_generate_sign("hello world")))
    
    # Test 4: Generate Metadata
    results.append(("Generate Metadata", await test_generate_metadata("hello")))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check logs above.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())