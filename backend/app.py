"""
Laoshi Coach Backend - Flask Application

Main entry point for the Flask API server.
"""

from flask import Flask, jsonify
from flask_cors import CORS

from .routes.vocabulary import vocabulary_bp
from .routes.progress import progress_bp
from .routes.practice import practice_bp


def create_app():
    """Application factory for creating the Flask app."""
    app = Flask(__name__)

    # Enable CORS for all routes (for development)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })

    # Register blueprints with /api prefix
    app.register_blueprint(vocabulary_bp, url_prefix='/api')
    app.register_blueprint(progress_bp, url_prefix='/api')
    app.register_blueprint(practice_bp, url_prefix='/api')

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Laoshi Coach API is running'
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app


# Create app instance for running directly
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
