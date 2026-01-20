from flask import Flask
from app.config.settings import config
from app.api.middleware.cors import init_cors, add_security_headers
from app.api.routes.agent_routes import api_bp
from app.api.routes.tool_routes import tools_bp
from app.mcp.transport.http_transport import mcp_bp
from app.utils.logger import logger


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Initialize CORS
    init_cors(app)

    # Add security headers
    add_security_headers(app)

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(mcp_bp)

    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'THz Agent'}

    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': 'THz Agent API',
            'version': '1.0.0',
            'endpoints': {
                'chat': '/api/v1/agent/chat',
                'tools': '/api/v1/tools/list',
                'mcp': '/mcp/v1/call'
            }
        }

    return app


def main():
    """Main entry point for the application"""
    app = create_app()

    logger.info(f"Starting THz Agent API on {config.server.host}:{config.server.port}")

    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug
    )


if __name__ == '__main__':
    main()