# Archivo: run.py (en la raíz de mi_proyecto/)
from app import create_app
from flask_debugtoolbar import DebugToolbarExtension


app = create_app()
toolbar = DebugToolbarExtension(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
