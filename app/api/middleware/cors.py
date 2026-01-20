from flask import Flask
from flask_cors import CORS


def init_cors(app: Flask):
    """Initialize CORS for the Flask app"""
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],  # In production, restrict this to specific origins
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })


def add_security_headers(app: Flask):
    """Add security headers to responses"""
    @app.after_request
    def after_request(response):
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        return response