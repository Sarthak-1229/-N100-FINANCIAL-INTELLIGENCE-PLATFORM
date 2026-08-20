import subprocess
import time
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

def make_request():
    try:
        req = urllib.request.Request('http://localhost:8000/api/v1/screener/')
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            return response.status, len(data)
    except Exception as e:
        return str(e), 0

# Start the server
print("Starting server...")
server = subprocess.Popen(['uvicorn', 'src.api.main:app', '--port', '8000'], 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait for server to start
time.sleep(3)

try:
    print("Running load test: 10 concurrent requests to /api/v1/screener/")
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [future.result() for future in as_completed(futures)]
    end = time.time()

    total_time = end - start
    print(f"Total time: {total_time:.2f} seconds")

    all_ok = True
    for i, (status, count_or_error) in enumerate(results):
        if isinstance(status, int) and status == 200:
            print(f"Request {i}: OK, returned {count_or_error} companies")
        else:
            print(f"Request {i}: FAILED - {status}")
            all_ok = False

    if all_ok and total_time < 10:
        print("Load test PASSED")
    else:
        print("Load test FAILED")
        if not all_ok:
            print("  - Some requests failed")
        if total_time >= 10:
            print(f"  - Total time {total_time:.2f} seconds exceeded 10 seconds")

finally:
    # Kill the server
    print("Stopping server...")
    server.terminate()
    server.wait()
