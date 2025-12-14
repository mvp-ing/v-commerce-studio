import os
import logging
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from video_generator import VideoGenerator

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config

# Set service name before patching
config.service = "video-generation"
config.flask["service_name"] = "video-generation"

# Initialize Datadog tracing (auto-patches flask, requests, etc.)
patch_all()

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "video-generation", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger(__name__)

def emit_video_metrics(generation_duration_ms: float = None, queue_depth: int = None, 
                       product_id: str = None, status: str = None):
    """Emit custom video generation metrics to Datadog"""
    span = tracer.current_span()
    if span:
        if generation_duration_ms is not None:
            span.set_tag("video.generation.duration_ms", generation_duration_ms)
        if queue_depth is not None:
            span.set_tag("video.queue.depth", queue_depth)
        if product_id:
            span.set_tag("video.product_id", product_id)
        if status:
            span.set_tag("video.status", status)

# ============================================

app = Flask(__name__)
CORS(app)

# Initialize video generator
try:
    video_generator = VideoGenerator()
    logger.info("Video generation service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize video generator: {e}")
    video_generator = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/products/search', methods=['GET'])
def search_products():
    """Search products for video generation"""
    try:
        query = request.args.get('q', '')
        if not video_generator:
            return jsonify({'error': 'Video generator not initialized'}), 500
        
        if query:
            products = video_generator.catalog_client.search_products(query)
        else:
            products = video_generator.catalog_client.list_products()
        
        # Format products for frontend
        formatted_products = []
        for product in products:
            price_usd = product.get('price_usd', {})
            price_value = None
            if 'units' in price_usd and 'nanos' in price_usd:
                # Convert price to a float for frontend processing
                price_value = float(f"{price_usd['units']}.{price_usd['nanos']:09d}")
            
            formatted_products.append({
                'id': product['id'],
                'name': product['name'],
                'description': product['description'],
                'price': price_value, # Send as float or None
                'categories': product.get('categories', []),
                'picture': product.get('picture', '')
            })
        
        return jsonify({'products': formatted_products})
    
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        return jsonify({'error': 'Failed to search products'}), 500

@app.route('/generate-ad', methods=['POST'])
def generate_ad():
    """Start video advertisement generation for a product"""
    start_time = time.time()
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'error': 'product_id is required'}), 400
        
        if not video_generator:
            return jsonify({'error': 'Video generator not initialized'}), 500
        
        # Start video generation
        job_id = video_generator.start_video_generation(product_id)
        
        # Emit metrics for video generation start
        emit_video_metrics(product_id=product_id, status="started")
        logger.info(f"Video generation started for product {product_id}, job_id: {job_id}")
        
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': 'Video generation started'
        })
    
    except ValueError as e:
        emit_video_metrics(product_id=product_id if 'product_id' in dir() else None, status="error")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error starting video generation: {e}")
        emit_video_metrics(product_id=product_id if 'product_id' in dir() else None, status="error")
        return jsonify({'error': 'Failed to start video generation'}), 500

@app.route('/video-status/<job_id>', methods=['GET'])
def video_status(job_id):
    """Check the status of video generation"""
    try:
        if not video_generator:
            return jsonify({'error': 'Video generator not initialized'}), 500
        
        status = video_generator.check_job_status(job_id)
        
        # Emit status check metrics
        emit_video_metrics(status=status.get('status', 'unknown'))
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error checking video status: {e}")
        return jsonify({'error': 'Failed to check video status'}), 500

@app.route('/video/<video_filename>', methods=['GET'])
def serve_video(video_filename):
    """Serve generated video file"""
    try:
        if not video_generator:
            return jsonify({'error': 'Video generator not initialized'}), 500
        
        video_path = video_generator.get_video_path(video_filename)
        if not video_path:
            return jsonify({'error': 'Video not found'}), 404
        
        return send_file(video_path, as_attachment=False, mimetype='video/mp4')
    
    except Exception as e:
        logger.error(f"Error serving video: {e}")
        return jsonify({'error': 'Failed to serve video'}), 500

@app.route('/validate-video', methods=['POST'])
def validate_video():
    """Validate generated video (approve/reject)"""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        approved = data.get('approved', False)
        
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400
        
        # For now, just log the validation
        # In a real system, you might update the job status or move files
        logger.info(f"Video validation for job {job_id}: {'approved' if approved else 'rejected'}")
        
        return jsonify({
            'status': 'success',
            'message': f"Video {'approved' if approved else 'rejected'} successfully"
        })
    
    except Exception as e:
        logger.error(f"Error validating video: {e}")
        return jsonify({'error': 'Failed to validate video'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
