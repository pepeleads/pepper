#!/usr/bin/env python
"""
A simple mock server that simulates a third-party site's API endpoint.
This allows you to test the integration without an actual external service.

Run this on a different port than your main application:
python mock_third_party_server.py --port 5001
"""

from flask import Flask, request, jsonify
import argparse
import random
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Pre-defined user profiles for testing
USER_PROFILES = {
    "john.doe@example.com": {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "profile": {
            "age": 32,
            "location": "New York, NY",
            "occupation": "Software Engineer"
        },
        "activity": {
            "last_login": (datetime.now() - timedelta(days=2)).isoformat(),
            "pages_visited": ["home", "products", "blog"],
            "total_logins": 42
        },
        "purchases": [
            {
                "order_id": "ORD-12345",
                "date": (datetime.now() - timedelta(days=30)).isoformat(),
                "total": 129.99,
                "items": [
                    {"id": "P12345", "name": "Premium Headphones", "price": 79.99, "quantity": 1},
                    {"id": "P67890", "name": "Phone Case", "price": 25.00, "quantity": 2}
                ]
            }
        ]
    },
    "jane.smith@example.com": {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "profile": {
            "age": 28,
            "location": "San Francisco, CA",
            "occupation": "Product Manager"
        },
        "activity": {
            "last_login": datetime.now().isoformat(),
            "pages_visited": ["home", "pricing", "contact", "checkout"],
            "total_logins": 17
        },
        "purchases": [
            {
                "order_id": "ORD-56789",
                "date": (datetime.now() - timedelta(days=5)).isoformat(),
                "total": 349.99,
                "items": [
                    {"id": "P54321", "name": "Smart Watch", "price": 349.99, "quantity": 1}
                ]
            }
        ]
    }
}

@app.route('/api/get-user-data', methods=['GET'])
def get_user_data():
    """
    Endpoint that returns user data based on email.
    This simulates a third-party API that would be called by your main application.
    """
    user_email = request.args.get('user_email')
    company_name = request.args.get('company_name')
    form_title = request.args.get('form_title')
    
    if not user_email:
        return jsonify({"error": "Missing user_email parameter"}), 400
    
    # Log the request for debugging
    print(f"Received data request for email: {user_email}")
    print(f"Company: {company_name}, Form: {form_title}")
    
    # Check if we have this user in our mock database
    if user_email in USER_PROFILES:
        # Return the pre-defined profile
        return jsonify(USER_PROFILES[user_email])
    
    # Generate a random profile for unknown emails
    generated_profile = generate_random_profile(user_email)
    return jsonify(generated_profile)

def generate_random_profile(email):
    """Generate a random user profile for testing"""
    first_name = email.split('@')[0].split('.')[0].title()
    last_name = email.split('@')[0].split('.')[-1].title() if '.' in email.split('@')[0] else "User"
    
    return {
        "name": f"{first_name} {last_name}",
        "email": email,
        "profile": {
            "age": random.randint(18, 65),
            "location": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Miami"]),
            "occupation": random.choice(["Engineer", "Designer", "Manager", "Student", "Entrepreneur"])
        },
        "activity": {
            "last_login": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            "pages_visited": random.sample(["home", "products", "pricing", "blog", "contact", "about", "checkout"], 
                                         k=random.randint(1, 5)),
            "total_logins": random.randint(1, 50)
        },
        "purchases": [
            {
                "order_id": f"ORD-{random.randint(10000, 99999)}",
                "date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "total": round(random.uniform(10.0, 500.0), 2),
                "items": [
                    {
                        "id": f"P{random.randint(10000, 99999)}",
                        "name": f"Product {chr(65 + random.randint(0, 25))}",
                        "price": round(random.uniform(10.0, 200.0), 2),
                        "quantity": random.randint(1, 3)
                    }
                ]
            }
        ]
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a mock third-party API server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
    parser.add_argument('--host', default='127.0.0.1', help='Host to run the server on (default: 127.0.0.1)')
    args = parser.parse_args()
    
    print(f"Starting mock third-party API server on http://{args.host}:{args.port}")
    print("Pre-defined test users:")
    for email in USER_PROFILES:
        print(f"  - {email}")
    print("\nCtrl+C to stop the server")
    
    app.run(host=args.host, port=args.port, debug=True) 