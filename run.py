import os
import sys
import subprocess
import http.server
import socketserver
import webbrowser
import threading

PORT = 8000
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
BACKEND_REFRESH_SCRIPT = os.path.join(os.path.dirname(__file__), "backend", "refresh.py")

# Ensure frontend directory exists
os.makedirs(FRONTEND_DIR, exist_ok=True)

class PortalHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Override the directory served to be the frontend folder
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/refresh":
            print("\n[Server] Received API request to refresh news...")
            try:
                # Execute the scraper script
                # Run python using the current python executable to ensure environment matches
                result = subprocess.run(
                    [sys.executable, BACKEND_REFRESH_SCRIPT],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print("[Server] Scraper output:")
                print(result.stdout)
                
                # Respond with success
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                response_data = '{"status": "success", "message": "News refreshed successfully"}'
                self.wfile.write(response_data.encode("utf-8"))
                print("[Server] Refresh complete. Sent response.")
                
            except subprocess.CalledProcessError as err:
                print(f"[Server] Scraper failed with code {err.returncode}:")
                print(err.stderr)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response_data = f'{{"status": "error", "message": "Scraper error: {err.stderr.strip()}"}}'
                self.wfile.write(response_data.encode("utf-8"))
            except Exception as e:
                print(f"[Server] Server error during refresh: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response_data = f'{{"status": "error", "message": "Server error: {str(e)}"}}'
                self.wfile.write(response_data.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def open_browser():
    print(f"[Launcher] Opening browser to http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")

def main():
    # If the user has never run the scraper, run it once on startup so they have initial data
    news_data_file = os.path.join(FRONTEND_DIR, "news_data.json")
    if not os.path.exists(news_data_file):
        print("[Launcher] news_data.json not found. Running initial scraper...")
        try:
            subprocess.run([sys.executable, BACKEND_REFRESH_SCRIPT], check=True)
            print("[Launcher] Initial scrape successful.")
        except Exception as e:
            print(f"[Launcher] Initial scrape failed: {e}")
            print("[Launcher] Creating empty placeholder data file.")
            with open(news_data_file, "w") as f:
                f.write("[]")

    # Start the local server
    handler = PortalHTTPHandler
    # Allow reuse of address to prevent "port already in use" errors during quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n=======================================================")
        print(f" US IMMIGRATION PORTAL SERVER RUNNING")
        print(f" URL: http://localhost:{PORT}")
        print(f" Serving folder: {FRONTEND_DIR}")
        print(f" Press Ctrl+C in terminal to stop the server.")
        print(f"=======================================================\n")
        
        # Open the browser in a separate thread after server starts
        threading.Timer(1.5, open_browser).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Launcher] Shutting down server. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
