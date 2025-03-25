from flask import Flask, request, jsonify
import requests
import os
import re
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_terabox_url(url):
    """
    Validate Terabox URL format
    """
    terabox_pattern = re.compile(r'^https?://.*terabox\.com/.*$', re.IGNORECASE)
    return terabox_pattern.match(url) is not None

# Root endpoint
@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "message": "Terabox Downloader API",
        "endpoints": {
            "/download": {
                "method": "POST",
                "description": "Download Terabox link",
                "required_body": {
                    "url": "The Terabox URL to download"
                }
            }
        }
    })

# Download endpoint
@app.route('/download', methods=['POST'])
def download():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate request
        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL is required in request body"
            }), 400
        
        # Extract and validate Terabox link
        terabox_link = data['url'].strip()
        if not validate_terabox_url(terabox_link):
            return jsonify({
                "status": "error",
                "message": "Invalid Terabox URL"
            }), 400

        # API endpoint for TeraBox downloader
        api_url = "https://ytshorts.savetube.me/api/v1/terabox-downloader"
        
        # Request payload
        payload = {"url": terabox_link}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # Send POST request to the ytshort API with timeout
            response = requests.post(
                api_url, 
                json=payload, 
                headers=headers, 
                timeout=10  # 10-second timeout
            )
            
            # Check if the response was successful
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Validate response structure
            if not data or 'response' not in data or not data['response']:
                return jsonify({
                    "status": "error",
                    "message": "No download information found"
                }), 404
            
            video_data = data['response'][0]
            
            # Prepare output data with robust error handling
            output_data = {
                "status": "success",
                "data": {
                    "title": video_data.get('title', 'Untitled'),
                    "thumbnail": video_data.get('thumbnail', ''),
                    "resolutions": {
                        "Fast Download": video_data.get('resolutions', {}).get('Fast Download', ''),
                        "HD Video": video_data.get('resolutions', {}).get('HD Video', '')
                    }
                }
            }
            
            return jsonify(output_data)
        
        except requests.exceptions.RequestException as e:
            # Handle various request-related exceptions
            logger.error(f"API request error: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Failed to fetch download information"
            }), 503
        
        except ValueError as e:
            # JSON parsing error
            logger.error(f"JSON parsing error: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Invalid response from download service"
            }), 500

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

# Disable debug mode in production
app.config['DEBUG'] = False

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
