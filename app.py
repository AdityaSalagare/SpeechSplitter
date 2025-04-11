import os
import logging
from flask import Flask, render_template, redirect, url_for

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Register the API blueprint
from api.routes import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# Root routes
@app.route('/')
def index():
    """Render main page with demo"""
    return render_template('index.html')

@app.route('/demo')
def demo():
    """Render demo page"""
    return render_template('demo.html')

@app.route('/docs')
def docs():
    """Render API documentation"""
    return render_template('docs.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
