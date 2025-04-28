/**
 * Pepper-Ads.com S2S Tracking JS
 * This script captures tracking parameters from the URL and stores them in cookies
 * for later use during form submission.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Capture tracking parameters from URL
    captureTrackingParams();
    
    // Append tracking params to form actions
    attachTrackingToForms();
});

/**
 * Capture tracking parameters from URL and store in cookies
 */
function captureTrackingParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const trackingParams = {
        'click_id': urlParams.get('click_id'),
        'campaign_id': urlParams.get('campaign_id'),
        'source': urlParams.get('source')
    };
    
    // Store parameters in cookies (30 days expiry)
    for (const [param, value] of Object.entries(trackingParams)) {
        if (value) {
            setCookie(param, value, 30);
        }
    }
}

/**
 * Set a cookie with the given name, value and expiry days
 */
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + d.toUTCString();
    document.cookie = name + "=" + value + ";" + expires + ";path=/";
}

/**
 * Get a cookie by name
 */
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    if (match) return match[2];
    return null;
}

/**
 * Append tracking parameters to all form actions
 */
function attachTrackingToForms() {
    // Get tracking params from cookies
    const click_id = getCookie('click_id');
    const campaign_id = getCookie('campaign_id');
    const source = getCookie('source');
    
    // Only proceed if we have tracking params
    if (!click_id && !campaign_id && !source) {
        return;
    }
    
    // Add tracking params to all forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add hidden fields for tracking params
            if (click_id) {
                addHiddenField(form, 'click_id', click_id);
            }
            if (campaign_id) {
                addHiddenField(form, 'campaign_id', campaign_id);
            }
            if (source) {
                addHiddenField(form, 'source', source);
            }
        });
    });
}

/**
 * Add a hidden input field to a form
 */
function addHiddenField(form, name, value) {
    // Check if field already exists
    let field = form.querySelector(`input[name="${name}"]`);
    
    if (!field) {
        field = document.createElement('input');
        field.type = 'hidden';
        field.name = name;
        form.appendChild(field);
    }
    
    field.value = value;
} 