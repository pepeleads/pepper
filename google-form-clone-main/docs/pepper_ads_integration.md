# Pepper-Ads.com S2S Integration Guide

This document outlines how to integrate your Pepper-Ads.com application with S2S tracking for conversions.

## Postback URL

When setting up your campaign, you'll need to provide a postback URL. Use the following URL:

```
https://pepper-ads.com/api/tracking/pepper-ads
```

## Supported Parameters

The tracking endpoint accepts the following parameters:

| Parameter | Description | Required |
|-----------|-------------|----------|
| `click_id` or `cid` | Unique identifier for the click | Yes |
| `campaign_id` | ID of the campaign | No |
| `conversion_id` or `transaction_id` | ID of the conversion/transaction | No |
| `amount` or `value` | Monetary value of the conversion | No |
| `status` | Status of the conversion (default: 'completed') | No |
| `form_id` | ID of the associated form (if applicable) | No |
| `response_id` | ID of the associated form response (if applicable) | No |

## Integration Methods

### GET Request

You can use a GET request for simple integrations:

```
https://pepper-ads.com/api/tracking/pepper-ads?click_id=12345&campaign_id=abcdef&amount=19.99
```

### POST Request

For more complex data, you can use a POST request with a JSON payload:

```json
{
  "click_id": "12345",
  "campaign_id": "abcdef",
  "amount": 19.99,
  "form_id": 123,
  "response_id": 456,
  "custom_data": {
    "user_agent": "Mozilla/5.0...",
    "referrer": "https://example.com"
  }
}
```

## Linking with Form Responses

To associate tracking data with specific form submissions, include the `form_id` and `response_id` parameters in your postback. This allows you to see which conversions came from specific form submissions.

## Viewing Tracking Data

Administrators can view tracking data by navigating to:

```
https://pepper-ads.com/admin/tracking
```

This page shows all tracking data and provides statistics by source.

## Troubleshooting

- Ensure that the `click_id` parameter is always included in your postbacks
- Check the server logs for any errors related to tracking
- Verify that your server can receive external POST/GET requests (adjust firewall settings if needed)

## Example Implementation for Your Advertisers

Here's how your advertisers should configure their postback URL in your campaign settings:

1. Log in to their advertising platform dashboard
2. Navigate to their campaign settings
3. Find the "Postback URL" or "S2S tracking" section
4. Enter your tracking URL: `https://pepper-ads.com/api/tracking/pepper-ads?click_id={click_id}&campaign_id={campaign_id}&amount={amount}`
5. Save their settings

Replace the placeholders `{click_id}`, `{campaign_id}`, and `{amount}` with the appropriate tokens provided by their advertising platform. 