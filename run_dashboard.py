import webbrowser
import os
import http.server
import socketserver
import threading

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Dashboard serving at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start server in a thread
    threading.Thread(target=start_server, daemon=True).start()
    
    # Open browser
    webbrowser.open(f"http://localhost:{PORT}/index.html")
    
    print("Press Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping dashboard...")
