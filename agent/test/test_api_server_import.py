# agent/test/test_api_server_import.py
print("Attempting to import FastAPI app from agent.api_server...")
try:
    from agent.api_server import app
    print("Successfully imported 'app' from agent.api_server.")
    print(f"FastAPI app title: {app.title}")
    # You could add more checks here, e.g., listing routes if FastAPI makes that easy offline
    # for route in app.routes:
    #     print(f"Route: {route.path} Methods: {route.methods}")
except SyntaxError as se:
    print(f"SyntaxError during import: {se}")
    raise
except ImportError as ie:
    print(f"ImportError during import: {ie}")
    raise
except Exception as e:
    print(f"An unexpected error occurred during import: {e}")
    raise

print("API server import test complete.")
