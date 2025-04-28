from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Form, FormResponse, AdTracking
from app import db

@app.route('/form/<int:form_id>/responses')
@login_required
def view_responses(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to view these responses.', 'danger')
        return redirect(url_for('dashboard'))
    
    responses = FormResponse.query.filter_by(form_id=form_id).order_by(FormResponse.submitted_at.desc()).all()
    return render_template('view_responses.html', form=form, responses=responses)

@app.route('/api/postback', methods=['POST'])
def postback_endpoint():
    """
    Public endpoint for receiving postback data from external services.
    This can be used as a webhook URL for third-party integrations.
    """
    # Get the data from the request
    data = request.json or {}
    
    # Log the received data
    app.logger.info(f"Received postback data: {data}")
    
    # Get the form_id and response_id if provided
    form_id = data.get('form_id')
    response_id = data.get('response_id')
    
    # Process the data as needed
    # This is where you would handle the specific logic for your postback
    # For example, updating a form response or triggering some action
    
    # Example: If form_id and response_id are provided, update a response
    if form_id and response_id:
        try:
            response = FormResponse.query.filter_by(id=response_id, form_id=form_id).first()
            if response:
                # Update the response with the received data
                response.third_party_data = data.get('third_party_data', {})
                response.updated_at = datetime.utcnow()
                db.session.commit()
                return jsonify({'status': 'success', 'message': 'Response updated successfully'}), 200
        except Exception as e:
            app.logger.error(f"Error processing postback: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    # Return a success response
    return jsonify({'status': 'received', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/api/tracking/pepper-ads', methods=['GET', 'POST'])
def pepper_ads_tracking():
    """
    S2S tracking endpoint specifically for pepper-ads.com postbacks.
    Accepts both GET and POST requests to accommodate different integration methods.
    """
    # Get the tracking data from query parameters or JSON body
    if request.method == 'POST':
        data = request.json or request.form.to_dict() or {}
    else:  # GET
        data = request.args.to_dict()
    
    # Log the received tracking data
    app.logger.info(f"Received pepper-ads tracking data: {data}")
    
    # Extract common tracking parameters
    source = data.get('source', 'pepper-ads')  # Default to 'pepper-ads' if not specified
    campaign_id = data.get('campaign_id')
    click_id = data.get('click_id') or data.get('cid')
    conversion_id = data.get('conversion_id') or data.get('transaction_id')
    amount = data.get('amount') or data.get('value')
    status = data.get('status', 'completed')
    
    # Optional: Link to form data if form_id is provided
    form_id = data.get('form_id')
    response_id = data.get('response_id')
    
    # Store the tracking data
    try:
        # Create a new tracking record
        tracking = AdTracking(
            source=source,
            campaign_id=campaign_id,
            click_id=click_id,
            conversion_id=conversion_id,
            amount=amount,
            status=status,
            form_id=form_id,
            response_id=response_id,
            raw_data=data,
            created_at=datetime.utcnow()
        )
        db.session.add(tracking)
        db.session.commit()
        
        # Process the conversion (e.g., update related form response, trigger notifications)
        # This will depend on your specific business logic
        if form_id and response_id:
            # Update the form response if needed
            response = FormResponse.query.filter_by(id=response_id, form_id=form_id).first()
            if response:
                # You could update additional fields here based on the tracking data
                response.updated_at = datetime.utcnow()
                db.session.commit()
        
        # Return a success response (pepper-ads expects a 200 OK)
        return jsonify({
            'status': 'success',
            'message': 'Conversion tracked successfully',
            'tracking_id': tracking.id,
            'click_id': click_id
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error processing pepper-ads tracking: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/tracking')
@login_required
def admin_tracking():
    """Admin view to see tracking data from ad networks like pepper-ads.com"""
    # Only allow admin users to access this page
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all tracking data, sorted by creation date (newest first)
    tracking_data = AdTracking.query.order_by(AdTracking.created_at.desc()).all()
    
    # Group by source for statistics
    sources = {}
    for track in tracking_data:
        if track.source not in sources:
            sources[track.source] = {'count': 0, 'amount': 0}
        sources[track.source]['count'] += 1
        if track.amount:
            sources[track.source]['amount'] += track.amount
    
    return render_template('admin_tracking.html', 
                          tracking_data=tracking_data, 
                          sources=sources,
                          title="Ad Tracking Data")

# Test endpoint to generate sample tracking data (remove in production)
@app.route('/api/tracking/test', methods=['GET'])
@login_required
def test_tracking():
    """
    Test endpoint to generate sample tracking data.
    This should be removed in production.
    """
    # Only allow admin users to access this endpoint
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Generate sample tracking data
    sources = ['google-ads', 'facebook', 'affiliate', 'direct']
    statuses = ['completed', 'pending', 'rejected']
    
    for i in range(5):  # Generate 5 sample records
        source = sources[i % len(sources)]
        status = statuses[i % len(statuses)]
        
        tracking = AdTracking(
            source=source,
            campaign_id=f'camp-{i+1}',
            click_id=f'click-{i+100}',
            conversion_id=f'conv-{i+500}',
            amount=float(10 + i * 5.5),
            status=status,
            raw_data={
                'sample': True,
                'test_id': i,
                'timestamp': datetime.utcnow().isoformat()
            },
            created_at=datetime.utcnow()
        )
        db.session.add(tracking)
    
    db.session.commit()
    flash('Sample tracking data generated successfully.', 'success')
    return redirect(url_for('admin_tracking'))

# Register custom filters with Jinja2
@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object to a string."""
    if value is None:
        return ""
    return value.strftime(format) 