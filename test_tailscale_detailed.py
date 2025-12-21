"""
test_tailscale_detailed.py
==========================
Test và monitor chi tiết kết nối qua Tailscale
Hiển thị logs real-time của cả caller API và local server
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional
import sys

# Config
CALLER_API_URL = "http://localhost:8000"
LOCAL_SERVER_URL = "http://100.125.241.20:8003"

class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title: str, color: str = Colors.CYAN):
    """In section header đẹp"""
    print(f"\n{color}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_log(source: str, message: str, level: str = "INFO"):
    """In log với format đẹp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    if level == "INFO":
        color = Colors.GREEN
    elif level == "WARNING":
        color = Colors.YELLOW
    elif level == "ERROR":
        color = Colors.RED
    else:
        color = Colors.BLUE
    
    print(f"{color}[{timestamp}] [{source:15s}] {level:8s}: {message}{Colors.ENDC}")

async def test_direct_local_server():
    """Test 1: Kết nối trực tiếp đến local server qua Tailscale"""
    print_section("TEST 1: Direct Connection to Local Server via Tailscale", Colors.BLUE)
    
    try:
        print_log("CLIENT", f"Sending request to {LOCAL_SERVER_URL}/api/sign/health")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = datetime.now()
            
            response = await client.get(f"{LOCAL_SERVER_URL}/api/sign/health")
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            print_log("CLIENT", f"Response received in {elapsed:.2f}ms", "INFO")
            print_log("LOCAL_SERVER", f"Status: {response.status_code}", "INFO")
            
            if response.status_code == 200:
                data = response.json()
                print_log("LOCAL_SERVER", f"Response: {json.dumps(data, indent=2)}", "INFO")
                
                print(f"\n{Colors.GREEN}✅ Direct Tailscale connection: SUCCESS{Colors.ENDC}")
                print(f"   📍 Tailscale IP: 100.125.241.20")
                print(f"   🔌 Port: 8003")
                print(f"   ⏱️  Response time: {elapsed:.2f}ms")
                return True
            else:
                print_log("LOCAL_SERVER", f"Unexpected status: {response.status_code}", "ERROR")
                return False
                
    except httpx.ConnectError as e:
        print_log("CLIENT", f"Connection failed: {e}", "ERROR")
        print(f"\n{Colors.RED}❌ Cannot connect to local server via Tailscale{Colors.ENDC}")
        print(f"\n{Colors.YELLOW}💡 Troubleshooting:{Colors.ENDC}")
        print("   1. Check if run_service.py is running")
        print("   2. Verify Tailscale is connected: tailscale status")
        print("   3. Check firewall on local machine")
        return False
    except Exception as e:
        print_log("CLIENT", f"Error: {e}", "ERROR")
        return False

async def test_via_caller_api():
    """Test 2: Kết nối qua Caller API (proxy)"""
    print_section("TEST 2: Connection via Caller API (Proxy)", Colors.BLUE)
    
    try:
        print_log("CLIENT", f"Sending request to {CALLER_API_URL}/health")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = datetime.now()
            
            response = await client.get(f"{CALLER_API_URL}/health")
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            print_log("CLIENT", f"Response received in {elapsed:.2f}ms", "INFO")
            print_log("CALLER_API", f"Status: {response.status_code}", "INFO")
            
            if response.status_code == 200:
                data = response.json()
                print_log("CALLER_API", f"Response: {json.dumps(data, indent=2)}", "INFO")
                
                # Analyze response
                overall_status = data.get("overall_status")
                local_servers = data.get("local_servers", [])
                
                print(f"\n{Colors.GREEN}✅ Caller API proxy: SUCCESS{Colors.ENDC}")
                print(f"   📡 Overall Status: {overall_status}")
                
                for server in local_servers:
                    server_url = server.get("server")
                    healthy = server.get("healthy")
                    details = server.get("details", {})
                    
                    status_icon = "✅" if healthy else "❌"
                    print(f"\n   {status_icon} Server: {server_url}")
                    print(f"      Status: {details.get('status')}")
                    print(f"      Response Time: {details.get('response_time_ms', 0):.2f}ms")
                    print(f"      Last Check: {details.get('last_check')}")
                
                return overall_status == "healthy"
            else:
                print_log("CALLER_API", f"Unexpected status: {response.status_code}", "ERROR")
                return False
                
    except Exception as e:
        print_log("CLIENT", f"Error: {e}", "ERROR")
        return False

async def test_full_pipeline():
    """Test 3: Test full pipeline với test-gloss"""
    print_section("TEST 3: Full Pipeline Test (test-gloss)", Colors.BLUE)
    
    test_text = "xin chào"
    
    try:
        print_log("CLIENT", f"Testing with text: '{test_text}'")
        print_log("CLIENT", f"POST {CALLER_API_URL}/api/test-gloss")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = datetime.now()
            
            response = await client.post(
                f"{CALLER_API_URL}/api/test-gloss",
                json={"text": test_text}
            )
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            print_log("CLIENT", f"Response received in {elapsed:.2f}ms", "INFO")
            
            if response.status_code == 200:
                data = response.json()
                
                print_log("CALLER_API", "Request forwarded to local server", "INFO")
                print_log("LOCAL_SERVER", "Processing request...", "INFO")
                print_log("LOCAL_SERVER", f"Response: {json.dumps(data, indent=2)}", "INFO")
                
                # Analyze result
                success = data.get("success", False)
                glosses = data.get("glosses", [])
                total_prims = data.get("total_primitives", 0)
                
                print(f"\n{Colors.GREEN}✅ Full pipeline: SUCCESS{Colors.ENDC}")
                print(f"   📝 Input: {test_text}")
                print(f"   🔤 Glosses: {glosses}")
                print(f"   🎯 Total Primitives: {total_prims}")
                print(f"   ⏱️  Total Time: {elapsed:.2f}ms")
                
                # Trace route
                print(f"\n{Colors.CYAN}📊 Request Flow Trace:{Colors.ENDC}")
                print(f"   1. CLIENT → CALLER_API (localhost:8000)")
                print(f"   2. CALLER_API → LOCAL_SERVER via Tailscale (100.125.241.20:8003)")
                print(f"   3. LOCAL_SERVER → MongoDB (load data)")
                print(f"   4. LOCAL_SERVER → CALLER_API (response)")
                print(f"   5. CALLER_API → CLIENT (final response)")
                
                return success
            else:
                print_log("CALLER_API", f"Error: {response.status_code}", "ERROR")
                print_log("CALLER_API", f"Response: {response.text}", "ERROR")
                return False
                
    except Exception as e:
        print_log("CLIENT", f"Error: {e}", "ERROR")
        return False

async def monitor_network_path():
    """Test 4: Monitor network path details"""
    print_section("TEST 4: Network Path Analysis", Colors.BLUE)
    
    try:
        print_log("ANALYZER", "Checking network configuration...")
        
        # Check caller API
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{CALLER_API_URL}/")
                caller_info = resp.json()
                print_log("ANALYZER", f"Caller API found: {caller_info.get('service')}", "INFO")
                print_log("ANALYZER", f"Configured servers: {caller_info.get('local_servers')}", "INFO")
            except Exception as e:
                print_log("ANALYZER", f"Caller API not accessible: {e}", "ERROR")
                return False
        
        # Check local server
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{LOCAL_SERVER_URL}/")
                local_info = resp.json()
                print_log("ANALYZER", f"Local server found: {local_info.get('service')}", "INFO")
                print_log("ANALYZER", f"Data source: {local_info.get('data_source')}", "INFO")
                print_log("ANALYZER", f"Stats: {local_info.get('stats')}", "INFO")
            except Exception as e:
                print_log("ANALYZER", f"Local server not accessible: {e}", "ERROR")
                return False
        
        print(f"\n{Colors.GREEN}✅ Network path verified{Colors.ENDC}")
        print(f"\n{Colors.CYAN}🌐 Network Topology:{Colors.ENDC}")
        print(f"""
        ┌─────────────────┐
        │   Your Client   │
        │  (Test Script)  │
        └────────┬────────┘
                 │
                 │ HTTP (localhost:8000)
                 ▼
        ┌─────────────────┐
        │   Caller API    │
        │  FastAPI Proxy  │
        └────────┬────────┘
                 │
                 │ Tailscale VPN (100.125.241.20:8003)
                 ▼
        ┌─────────────────┐
        │  Local Server   │
        │  (run_service)  │
        └────────┬────────┘
                 │
                 │ MongoDB URI
                 ▼
        ┌─────────────────┐
        │  MongoDB Atlas  │
        │   (Cloud DB)    │
        └─────────────────┘
        """)
        
        return True
        
    except Exception as e:
        print_log("ANALYZER", f"Error: {e}", "ERROR")
        return False

async def main():
    """Run all tests"""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("  TAILSCALE CONNECTION MONITOR")
    print("  Testing Caller API ↔ Local Server Communication")
    print("=" * 70)
    print(f"{Colors.ENDC}")
    
    results = {
        "direct_connection": False,
        "caller_api": False,
        "full_pipeline": False,
        "network_analysis": False
    }
    
    # Run tests
    results["direct_connection"] = await test_direct_local_server()
    await asyncio.sleep(1)
    
    results["caller_api"] = await test_via_caller_api()
    await asyncio.sleep(1)
    
    results["full_pipeline"] = await test_full_pipeline()
    await asyncio.sleep(1)
    
    results["network_analysis"] = await monitor_network_path()
    
    # Summary
    print_section("TEST SUMMARY", Colors.HEADER)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        
        test_display = test_name.replace("_", " ").title()
        print(f"   {icon} {color}{test_display:30s} {status}{Colors.ENDC}")
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}")
        print("🎉 ALL TESTS PASSED!")
        print("Your Tailscale connection is working perfectly!")
        print(f"{Colors.ENDC}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}")
        print("❌ SOME TESTS FAILED")
        print("Check the logs above for details")
        print(f"{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.ENDC}")
        sys.exit(1)