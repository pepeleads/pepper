"""
S2S Tracking implementation for Pepper-Ads.com
This module provides functions to integrate server-to-server (S2S) tracking with form submissions.
"""

import json
import threading
import requests
from datetime import datetime
from flask import request, current_app
from app.models import AdTracking
from app import db

class S2STracker:
    """Class for handling S2S tracking operations"""
    
    @staticmethod
    def get_tracking_params_from_request():
        """
        Extract tracking parameters from the request (URL parameters or cookies)
        """
        # First check URL parameters, then cookies
        click_id = request.args.get('click_id') or request.cookies.get('click_id')
        campaign_id = request.args.get('campaign_id') or request.cookies.get('campaign_id')
        source = request.args.get('source') or request.cookies.get('source', 'pepper-ads')
        
        return {
            'click_id': click_id,
            'campaign_id': campaign_id,
            'source': source
        }
    
    @staticmethod
    def store_tracking_cookies(response_obj, tracking_params):
        """
        Store tracking parameters in cookies for future submissions
        """
        if tracking_params.get('click_id'):
            response_obj.set_cookie('click_id', tracking_params['click_id'], max_age=2592000)  # 30 days
        if tracking_params.get('campaign_id'):
            response_obj.set_cookie('campaign_id', tracking_params['campaign_id'], max_age=2592000)  # 30 days
        if tracking_params.get('source'):
            response_obj.set_cookie('source', tracking_params['source'], max_age=2592000)  # 30 days
        return response_obj
    
    @staticmethod
    def track_conversion(form, response, tracking_params, user_data=None):
        """
        Track a form submission conversion
        
        Args:
            form: The form object
            response: The response/submission object
            tracking_params: Dictionary containing click_id, campaign_id, and source
            user_data: Optional user data (like email) to include
        
        Returns:
            tracking_id: ID of the created tracking record, or None if tracking failed
        """
        click_id = tracking_params.get('click_id')
        if not click_id:
            return None
            
        try:
            # Calculate form value (if applicable)
            form_value = 0
            if hasattr(form, 'value'):
                form_value = form.value
            
            # Create tracking record
            tracking = AdTracking(
                source=tracking_params.get('source', 'pepper-ads'),
                campaign_id=tracking_params.get('campaign_id'),
                click_id=click_id,
                conversion_id=str(response.id),
                amount=form_value,
                status='completed',
                form_id=form.id,
                response_id=response.id,
                raw_data={
                    'form_title': form.title,
                    'user_data': user_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            db.session.add(tracking)
            db.session.commit()
            
            # Make an internal S2S call to our own tracking endpoint
            S2STracker.send_s2s_postback(
                tracking.source,
                tracking.click_id,
                tracking.campaign_id,
                tracking.conversion_id,
                tracking.amount,
                form.id,
                response.id
            )
            
            return tracking.id
            
        except Exception as e:
            current_app.logger.error(f"Error creating tracking record: {str(e)}")
            return None
    
    @staticmethod
    def send_s2s_postback(source, click_id, campaign_id, conversion_id, amount, form_id, response_id):
        """
        Send a postback to our own tracking endpoint (asynchronously)
        """
        def send_request():
            try:
                # Build the absolute URL to our tracking endpoint
                tracking_url = request.host_url.rstrip('/') + "/api/tracking/pepper-ads"
                
                # Prepare tracking data
                tracking_data = {
                    'source': source,
                    'click_id': click_id,
                    'campaign_id': campaign_id,
                    'conversion_id': conversion_id,
                    'amount': amount,
                    'form_id': form_id,
                    'response_id': response_id
                }
                
                # Send the request
                requests.post(tracking_url, json=tracking_data, timeout=5)
                
            except Exception as e:
                if current_app:
                    current_app.logger.error(f"Error sending S2S postback: {str(e)}")
        
        # Send request in a background thread to avoid blocking
        tracking_thread = threading.Thread(target=send_request)
        tracking_thread.daemon = True
        tracking_thread.start()

# Usage example in form submission route:
"""
from s2s_tracking import S2STracker

@app.route('/form/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    # ... existing code ...
    
    # Get tracking parameters
    tracking_params = S2STracker.get_tracking_params_from_request()
    
    # Process form and save response
    # ... existing code ...
    
    # Track conversion
    S2STracker.track_conversion(form, response, tracking_params, user_email)
    
    # Redirect to success page
    response_obj = redirect(url_for('form_submitted', form_id=form_id))
    
    # Store tracking cookies
    response_obj = S2STracker.store_tracking_cookies(response_obj, tracking_params)
    
    return response_obj
""" 