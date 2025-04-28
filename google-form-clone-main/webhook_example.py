#!/usr/bin/env python
"""
Example script for third-party sites to push user data to the webhook endpoint.
This script demonstrates how to send user data without requiring an API key.
"""

import requests
import json
import argparse
from datetime import datetime

def send_user_data(webhook_url, user_email, company_code, user_data=None):
    """
    Send user data to the webhook endpoint.
    
    Args:
        webhook_url (str): URL of the webhook endpoint (e.g., http://localhost:5000/api/third-party-webhook)
        user_email (str): Email address of the user
        company_code (str): Referral code of the company
        user_data (dict, optional): User data to send
    
    Returns:
        dict: Response from the server
    """
    if user_data is None:
        # Sample user data if none provided
        user_data = {
            "name": "John Doe",
            "email": user_email,
            "profile": {
                "age": 35,
                "location": "San Francisco, CA",
                "occupation": "Product Manager"
            },
            "activity": {
                "last_login": datetime.now().isoformat(),
                "pages_visited": ["home", "products", "checkout"],
                "total_logins": 27
            },
            "purchases": [
                {
                    "order_id": "ORD-12345",
                    "date": datetime.now().isoformat(),
                    "total": 129.99,
                    "items": [
                        {"id": "P12345", "name": "Product X", "price": 49.99, "quantity": 1},
                        {"id": "P67890", "name": "Product Y", "price": 39.99, "quantity": 2}
                    ]
                }
            ]
        }
    
    payload = {
        "user_email": user_email,
        "company_code": company_code,
        "user_data": user_data
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(payload))
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 400 else response.text
        }
    except requests.RequestException as e:
        return {
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Send user data to webhook endpoint")
    parser.add_argument("--url", default="http://localhost:5000/api/third-party-webhook", 
                        help="Webhook URL (default: http://localhost:5000/api/third-party-webhook)")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--company", required=True, help="Company referral code")
    parser.add_argument("--data", help="JSON file containing user data (optional)")
    
    args = parser.parse_args()
    
    user_data = None
    if args.data:
        try:
            with open(args.data, 'r') as f:
                user_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading JSON data file: {e}")
            return
    
    result = send_user_data(
        args.url,
        args.email,
        args.company,
        user_data
    )
    
    print(json.dumps(result, indent=2))
    
    if "status_code" in result and result["status_code"] == 200:
        print("\nSuccess! User data was sent to the webhook.")
    else:
        print("\nError sending data to webhook. Check the response for details.")

if __name__ == "__main__":
    main() 