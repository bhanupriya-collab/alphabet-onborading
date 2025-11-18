"""Flask app for Cloud Run deployment with email scheduler.

This app provides HTTP endpoints that Cloud Scheduler can call to trigger
email processing for Google Onboarding. Cloud Run requires a web server 
listening on PORT (default 8080).

Flow:
1. Cloud Scheduler hits /scheduler/run endpoint every N minutes
2. App reads Google Sheet to find rows where Next Email At <= now
3. Sends appropriate emails (welcome, compliance, password setup, etc.)
4. Updates last 4 columns: Next Email Type, Next Email At, Email Status, Overall Status
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from root_agent.tools.utils.email_scheduler import process_poll_cycle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SCHEDULE_CONFIG = {
    "enabled": True,
    "last_run": None,
    "dry_run": os.getenv('DRY_RUN', '0') == '1'
}

app = Flask(__name__)

@app.route('/')
def root():
    """Root endpoint with service info"""
    return jsonify({
        'service': 'Alphabet Onboarding Email Scheduler',
        'version': '1.0',
        'status': 'Running' if SCHEDULE_CONFIG['enabled'] else 'Disabled',
        'last_run': SCHEDULE_CONFIG['last_run'],
        'dry_run': SCHEDULE_CONFIG['dry_run'],
        'endpoints': {
            'scheduler': '/scheduler/run (POST/GET) - Cloud Scheduler trigger endpoint',
            'manual': '/manual/trigger (POST) - Manual trigger for testing',
            'health': '/health (GET) - Health check',
            'config': '/config (GET/POST) - View/Update configuration'
        },
        'environment': {
            'sheet_id': os.getenv('SHEET_ID', 'Not set'),
            'identity_range': os.getenv('SHEET_RANGE_IDENTITY', 'A:P'),
            'state_range': os.getenv('SHEET_RANGE_STATE', 'Q:T')
        }
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'service': 'alphabet-onboarding-scheduler',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/scheduler/run', methods=['POST', 'GET'])
def run_scheduler():
    """
    Main endpoint that Cloud Scheduler hits to trigger email processing.
    
    Cloud Scheduler should be configured to hit this endpoint every N minutes.
    Reads Google Sheet, finds due emails, sends them, and updates status columns.
    """
    try:
        logger.info("📧 Scheduler trigger received")
        
        # Check if processing is enabled
        if not SCHEDULE_CONFIG['enabled']:
            logger.info("📴 Email processing is disabled")
            return jsonify({
                'success': False,
                'message': 'Email processing is currently disabled',
                'enabled': False
            }), 200
        
        # Update last run time
        SCHEDULE_CONFIG['last_run'] = datetime.now().isoformat()
        
        # Run the email scheduler logic
        result = process_poll_cycle()
        
        # Log the result for Cloud Logging
        logger.info(f"✅ Scheduler completed: {json.dumps(result, indent=2)}")
        
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        error_msg = f"Scheduler execution failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/manual/trigger', methods=['POST'])
def manual_trigger():
    """
    Manual trigger endpoint for testing.
    Can be called from Cloud Console or curl for debugging.
    """
    try:
        logger.info("📞 Manual trigger called")
        
        # Update last run time
        SCHEDULE_CONFIG['last_run'] = datetime.now().isoformat()
        
        result = process_poll_cycle()
        
        logger.info(f"✅ Manual trigger completed: {json.dumps(result, indent=2)}")
        
        return jsonify({
            'success': True,
            'message': 'Manual trigger executed successfully',
            'result': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        error_msg = f"Manual trigger failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Get current schedule configuration"""
    return jsonify({
        'schedule_config': SCHEDULE_CONFIG,
        'environment_variables': {
            'SHEET_ID': os.getenv('SHEET_ID', 'Not set'),
            'IDENTITY_RANGE': os.getenv('SHEET_RANGE_IDENTITY', 'A:P'),
            'STATE_RANGE': os.getenv('SHEET_RANGE_STATE', 'Q:T'),
            'ENABLE_SENDING': os.getenv('ENABLE_SENDING', 'false'),
            'DRY_RUN': os.getenv('DRY_RUN', '0')
        },
        'message': 'Current scheduler configuration'
    }), 200

@app.route('/config', methods=['POST'])
def update_config():
    """Update schedule configuration (enable/disable processing)"""
    try:
        data = request.get_json()
        
        if 'enabled' in data:
            SCHEDULE_CONFIG['enabled'] = bool(data['enabled'])
            logger.info(f"Schedule enabled status updated to: {SCHEDULE_CONFIG['enabled']}")
        
        if 'dry_run' in data:
            SCHEDULE_CONFIG['dry_run'] = bool(data['dry_run'])
            logger.info(f"Dry run status updated to: {SCHEDULE_CONFIG['dry_run']}")
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'new_config': SCHEDULE_CONFIG
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating configuration: {e}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Get port from environment (Cloud Run sets this)
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🚀 Starting Alphabet Onboarding Email Scheduler on port {port}")
    
    # Run the Flask app
    # In production, use gunicorn (configured in Dockerfile)
    app.run(host='0.0.0.0', port=port, debug=False)
