"""
Firebase Cloud Function wrapper for FastAPI backend
This allows deploying the FastAPI application to Firebase Cloud Functions
"""

import os
import sys
import functions_framework
from typing import Callable

# Add parent directory to path to import backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from backend
from backend.main import app


@functions_framework.http
def api(request: functions_framework.Request) -> tuple | str:
    """
    Firebase Cloud Function HTTP handler
    
    Wraps the FastAPI application to work with Google Cloud Functions.
    Routes all HTTP requests through the FastAPI app.
    
    Args:
        request: Google Cloud Functions HTTP request
        
    Returns:
        Response from FastAPI application
    """
    
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600',
        }
        return ('', 204, headers)
    
    # For other requests, use ASGI to handle the request
    from asgiref.sync import sync_to_async
    import asyncio
    
    async def asgi_app(scope, receive, send):
        # Create ASGI scope from Cloud Functions request
        scope['type'] = 'http'
        scope['asgi'] = {'version': '3.0'}
        scope['http_version'] = '1.1'
        scope['method'] = request.method
        scope['scheme'] = 'https'
        scope['path'] = request.path.split('?')[0]
        scope['query_string'] = (request.query_string or '').encode()
        scope['root_path'] = ''
        
        # Headers
        scope['headers'] = [
            (key.lower().encode(), value.encode())
            for key, value in request.headers.items()
        ]
        
        # Client
        scope['client'] = (request.remote_addr or '0.0.0.0', 0)
        
        # Receive body
        body = request.get_data()
        
        # Response data
        response_started = False
        status_code = 200
        response_headers = []
        body_parts = []
        
        async def receive_callable():
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,
            }
        
        async def send_callable(message):
            nonlocal response_started, status_code, response_headers, body_parts
            
            if message['type'] == 'http.response.start':
                response_started = True
                status_code = message['status']
                response_headers = message.get('headers', [])
            elif message['type'] == 'http.response.body':
                body_parts.append(message.get('body', b''))
        
        # Call the app
        await app(scope, receive_callable, send_callable)
        
        # Build response
        response_body = b''.join(body_parts)
        headers_dict = {
            key.decode(): value.decode()
            for key, value in response_headers
        }
        
        # Add CORS headers
        headers_dict['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        headers_dict['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        headers_dict['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return (response_body, status_code, headers_dict)
    
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        body, status, headers = loop.run_until_complete(
            asgi_app(None, None, None)
        )
    finally:
        loop.close()
    
    return (body, status, headers)


# Alternative simpler version (if above doesn't work)
@functions_framework.http
def api_simple(request: functions_framework.Request):
    """
    Simple wrapper - routes through ASGI middleware
    Use this if the above version has issues
    """
    from werkzeug.wrappers import Response
    from werkzeug.exceptions import MethodNotAllowed
    
    # Handle CORS
    if request.method == 'OPTIONS':
        return Response('', status=204, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        })
    
    # Use Starlette's test client approach
    from starlette.testclient import TestClient
    
    client = TestClient(app)
    
    # Build the request URL
    path = request.path
    query_string = request.query_string.decode() if request.query_string else ''
    if query_string:
        path = f"{path}?{query_string}"
    
    # Make request
    response = client.request(
        method=request.method,
        url=path,
        content=request.get_data(),
        headers=dict(request.headers),
    )
    
    # Add CORS headers
    headers = dict(response.headers)
    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    return (response.content, response.status_code, headers)
