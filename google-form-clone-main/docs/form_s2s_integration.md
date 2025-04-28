# Form S2S Tracking Integration Guide

This guide explains how to integrate server-to-server (S2S) tracking with your forms, so form submissions can be tracked as conversions in the pepper-ads.com tracking system.

## Overview

The S2S tracking integration has two main components:

1. **Client-side tracking**: Captures tracking parameters from the URL (like click_id, campaign_id) and stores them in cookies.
2. **Server-side tracking**: When a form is submitted, the tracking parameters are sent to the pepper-ads.com tracking system.

## Installation Steps

### 1. Include the Tracking JavaScript

Add the tracking.js script to your base template:

```html
<script src="{{ url_for('static', filename='js/tracking.js') }}"></script>
```

This script will automatically:
- Capture tracking parameters from the URL
- Store them in cookies
- Add hidden fields to forms when they're submitted

### 2. Import the S2S Tracking Module

In your app.py or form handling file, import the S2S tracking module:

```python
from s2s_tracking import S2STracker
```

### 3. Modify Form Submission Handlers

Update your form submission route to include tracking:

```python
@app.route('/form/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    # Get the form
    form = Form.query.get_or_404(form_id)
    
    # Get tracking parameters from request/cookies
    tracking_params = S2STracker.get_tracking_params_from_request()
    
    # Process the form submission as usual
    # ...
    
    # Save the form response
    response = Response(form_id=form_id, ...)
    db.session.add(response)
    db.session.commit()
    
    # Track the conversion
    S2STracker.track_conversion(form, response, tracking_params, user_email)
    
    # Redirect to success page
    response_obj = redirect(url_for('form_submitted', form_id=form_id))
    
    # Store tracking cookies for future submissions
    response_obj = S2STracker.store_tracking_cookies(response_obj, tracking_params)
    
    return response_obj
```

## How It Works

1. When users click on an ad, they'll arrive at your form with tracking parameters in the URL (e.g., `?click_id=123&campaign_id=abc&source=google`)
2. The tracking.js script captures these parameters and stores them in cookies
3. When the form is submitted, the parameters are included in the request
4. The form submission handler:
   - Creates the form response as usual
   - Creates a tracking record linking the conversion to the ad click
   - Sends a server-to-server postback to the pepper-ads.com tracking endpoint
   - Stores the tracking parameters in cookies for future form submissions

## Testing Your Integration

### Test Mode

To test the integration without real ad clicks, you can manually add tracking parameters to your form URL:

```
https://your-domain.com/form/123?click_id=test123&campaign_id=test-campaign&source=test
```

### Viewing Tracking Data

Administrators can view all tracking data in the admin dashboard:

```
https://pepper-ads.com/admin/tracking
```

## URL Parameters

The following parameters can be added to form URLs to enable tracking:

| Parameter | Description | Required |
|-----------|-------------|----------|
| `click_id` | Unique identifier for the ad click | Yes |
| `campaign_id` | ID of the advertising campaign | No |
| `source` | Source of the traffic (default: pepper-ads) | No |

## Troubleshooting

- Check browser cookies to verify tracking parameters are being stored
- Verify that forms have hidden fields with tracking parameters when submitted
- Check the admin tracking dashboard to see if conversions are being recorded
- Look for errors in your application logs related to tracking

## Security Considerations

- The tracking system only records non-sensitive data (no form answers are tracked)
- User email is only included if explicitly passed to the tracking function
- No personally identifiable information is shared with external systems

For more information on the overall tracking system, see [pepper_ads_integration.md](pepper_ads_integration.md). 