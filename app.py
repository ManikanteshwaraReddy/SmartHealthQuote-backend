print("LOADING app.py!")
from backend.app import create_app

print("Calling create_app...")
app_instance = create_app()
print("App created successfully")

# Export it as application so gunicorn can find it
application = app_instance
app = app_instance

if __name__ == "__main__":
    app_instance.run()
