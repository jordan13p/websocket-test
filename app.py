#!/usr/bin/env python3
"""
WebSocket Test Service with Health Check

This service provides:
1. Health check endpoint at root path (/)
2. WebSocket server for testing connections
3. Simple echo functionality for WebSocket messages
4. Container/Pod identification for load balancer testing
"""

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime
from typing import Dict, Set

import websockets
from websockets.server import WebSocketServerProtocol
from aiohttp import web, WSMsgType
import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: Set[WebSocketServerProtocol] = set()

class ServiceIdentity:
    """Handle service instance identification"""
    
    def __init__(self):
        self.instance_id = str(uuid.uuid4())[:8]  # Short UUID for identification
        self.hostname = self._get_hostname()
        self.container_ip = self._get_container_ip()
        self.pod_name = self._get_pod_name()
        self.node_name = self._get_node_name()
        self.namespace = self._get_namespace()
        self.service_name = self._get_service_name()
        
        # Create a comprehensive identity
        self.identity = self._create_identity()
        
        logger.info(f"Service Identity: {self.identity}")
    
    def _get_hostname(self) -> str:
        """Get hostname of the container/pod"""
        try:
            return socket.gethostname()
        except Exception as e:
            logger.error(f"Failed to get hostname: {e}")
            return "unknown-host"
    
    def _get_container_ip(self) -> str:
        """Get container IP address"""
        try:
            # Try to get IP by connecting to a dummy address
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception as e:
            logger.error(f"Failed to get container IP: {e}")
            return "unknown-ip"
    
    def _get_pod_name(self) -> str:
        """Get Kubernetes Pod name from environment"""
        return os.environ.get('POD_NAME', os.environ.get('HOSTNAME', ''))
    
    def _get_node_name(self) -> str:
        """Get Kubernetes Node name from environment"""
        return os.environ.get('NODE_NAME', '')
    
    def _get_namespace(self) -> str:
        """Get Kubernetes namespace from environment"""
        return os.environ.get('POD_NAMESPACE', '')
    
    def _get_service_name(self) -> str:
        """Get service name from environment or use default"""
        return os.environ.get('SERVICE_NAME', 'websocket-test-service')
    
    def _create_identity(self) -> Dict:
        """Create comprehensive service identity"""
        return {
            "instance_id": self.instance_id,
            "hostname": self.hostname,
            "container_ip": self.container_ip,
            "pod_name": self.pod_name,
            "node_name": self.node_name,
            "namespace": self.namespace,
            "service_name": self.service_name,
            "environment": self._detect_environment(),
            "display_name": self._get_display_name()
        }
    
    def _detect_environment(self) -> str:
        """Detect if running in Kubernetes, Docker, or local"""
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            return "kubernetes"
        elif os.path.exists('/.dockerenv'):
            return "docker"
        else:
            return "local"
    
    def _get_display_name(self) -> str:
        """Get a user-friendly display name for the service instance"""
        if self.pod_name:
            return f"{self.service_name}-{self.pod_name}"
        elif self.hostname != "unknown-host":
            return f"{self.service_name}-{self.hostname}"
        else:
            return f"{self.service_name}-{self.instance_id}"
    
    def get_info(self) -> Dict:
        """Get service identity information"""
        return self.identity.copy()

# Initialize service identity
service_identity = ServiceIdentity()

class WebSocketHandler:
    """Handle WebSocket connections and messages"""
    
    @staticmethod
    async def handle_websocket(websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        logger.info(f"New WebSocket connection from {client_ip} on path: {path}")
        
        # Add connection to active set
        active_connections.add(websocket)
        
        try:
            # Send welcome message with service identity
            welcome_msg = {
                "type": "welcome",
                "message": f"Connected to {service_identity.identity['display_name']}",
                "timestamp": datetime.utcnow().isoformat(),
                "client_ip": client_ip,
                "service_identity": service_identity.get_info()
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Handle messages
            async for message in websocket:
                # Log all received messages
                logger.info(f"WebSocket message from {client_ip}: {message}")
                
                try:
                    # Try to parse as JSON
                    data = json.loads(message)
                    # Check if parsed data is a dictionary (JSON object)
                    if isinstance(data, dict):
                        await WebSocketHandler.handle_json_message(websocket, data)
                    else:
                        # If it's a valid JSON but not an object (e.g., number, string, array)
                        # treat it as plain text
                        await WebSocketHandler.handle_text_message(websocket, message)
                except json.JSONDecodeError:
                    # Handle as plain text
                    await WebSocketHandler.handle_text_message(websocket, message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for {client_ip}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
        finally:
            # Remove connection from active set
            active_connections.discard(websocket)
    
    @staticmethod
    async def handle_json_message(websocket: WebSocketServerProtocol, data: Dict):
        """Handle JSON message from client"""
        message_type = data.get("type", "unknown")
        
        if message_type == "ping":
            # Respond to ping with pong
            response = {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat(),
                "original_data": data
            }
        elif message_type == "echo":
            # Echo the message back
            response = {
                "type": "echo_response",
                "timestamp": datetime.utcnow().isoformat(),
                "echoed_data": data
            }
        elif message_type == "broadcast":
            # Broadcast message to all connected clients
            broadcast_msg = {
                "type": "broadcast",
                "timestamp": datetime.utcnow().isoformat(),
                "message": data.get("message", ""),
                "sender": websocket.remote_address[0] if websocket.remote_address else "unknown"
            }
            await WebSocketHandler.broadcast_message(broadcast_msg)
            response = {
                "type": "broadcast_confirmation",
                "timestamp": datetime.utcnow().isoformat(),
                "recipients": len(active_connections)
            }
        else:
            # Unknown message type
            response = {
                "type": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Unknown message type: {message_type}",
                "received_data": data
            }
        
        await websocket.send(json.dumps(response))
    
    @staticmethod
    async def handle_text_message(websocket: WebSocketServerProtocol, message: str):
        """Handle plain text message from client"""
        response = {
            "type": "text_echo",
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": message,
            "message_length": len(message)
        }
        await websocket.send(json.dumps(response))
    
    @staticmethod
    async def broadcast_message(message: Dict):
        """Broadcast message to all active connections"""
        if not active_connections:
            return
        
        message_str = json.dumps(message)
        # Send message to all active connections
        disconnected = set()
        
        for connection in active_connections:
            try:
                await connection.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            active_connections.discard(conn)

class HTTPHandler:
    """Handle HTTP requests"""
    
    @staticmethod
    async def health_check(request):
        """Health check endpoint"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_websocket_connections": len(active_connections),
            "service": "websocket-test-service",
            "version": "1.0.0",
            "service_identity": service_identity.get_info()
        }
        return web.json_response(health_data, status=200)
    
    @staticmethod
    async def websocket_endpoint(request):
        """HTTP to WebSocket upgrade endpoint"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        client_ip = request.remote
        logger.info(f"HTTP WebSocket connection from {client_ip}")
        
        try:
            # Send welcome message with service identity
            welcome_msg = {
                "type": "welcome",
                "message": f"Connected to {service_identity.identity['display_name']} via HTTP WebSocket",
                "timestamp": datetime.utcnow().isoformat(),
                "client_ip": client_ip,
                "service_identity": service_identity.get_info()
            }
            await ws.send_str(json.dumps(welcome_msg))
            
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Log all received messages
                    logger.info(f"HTTP WebSocket message from {client_ip}: {msg.data}")
                    
                    try:
                        data = json.loads(msg.data)
                        response = {
                            "type": "http_echo",
                            "timestamp": datetime.utcnow().isoformat(),
                            "echoed_data": data
                        }
                        await ws.send_str(json.dumps(response))
                    except json.JSONDecodeError:
                        response = {
                            "type": "text_echo",
                            "timestamp": datetime.utcnow().isoformat(),
                            "original_message": msg.data
                        }
                        await ws.send_str(json.dumps(response))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"Error in HTTP WebSocket handler: {e}")
        
        return ws

async def create_app():
    """Create and configure the web application"""
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_get('/', HTTPHandler.health_check)
    app.router.add_get('/health', HTTPHandler.health_check)
    app.router.add_get('/ws', HTTPHandler.websocket_endpoint)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

async def start_websocket_server(host: str = "0.0.0.0", port: int = 8765):
    """Start the standalone WebSocket server"""
    logger.info(f"Starting WebSocket server on {host}:{port}")
    
    server = await websockets.serve(
        WebSocketHandler.handle_websocket,
        host,
        port,
        ping_interval=30,
        ping_timeout=10
    )
    
    return server

async def start_http_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the HTTP server"""
    app = await create_app()
    
    # Disable access log for health check endpoints
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"HTTP server started on {host}:{port}")
    logger.info(f"WebSocket endpoint available at: ws://{host}:{port}/ws")
    
    return runner

async def main():
    """Main application entry point"""
    logger.info("Starting WebSocket Test Service...")
    
    # Start both servers
    websocket_server = await start_websocket_server()
    http_runner = await start_http_server()
    
    logger.info("=== WebSocket Test Service Started ===")
    logger.info(f"Service Instance: {service_identity.identity['display_name']}")
    logger.info(f"Environment: {service_identity.identity['environment']}")
    logger.info("Available endpoints:")
    logger.info("  - Health Check: http://localhost:8080/")
    logger.info("  - HTTP WebSocket: ws://localhost:8080/ws")
    logger.info("  - Standalone WebSocket: ws://localhost:8765/")
    logger.info("=======================================")
    
    try:
        # Keep servers running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()
        await http_runner.cleanup()
        logger.info("Servers stopped.")

if __name__ == "__main__":
    asyncio.run(main())
