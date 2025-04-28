# Google Forms Clone

A web application that allows users to create and fill out forms, similar to Google Forms.

## Features
- User authentication (signup/login)
- Create forms with various question types
- Share forms via unique links
- View form responses
- Real-time form preview
- Third-party data integration for form submitters

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python init_db.py
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Project Structure
- `app.py`: Main application file
- `models.py`: Database models
- `forms.py`: Form definitions
- `static/`: Static files (CSS, JavaScript)
- `templates/`: HTML templates
- `instance/`: Database and instance-specific files 

## Third-Party Data Integration

This application can automatically fetch additional user data from third-party websites when users submit forms. Here's how it works:

1. When a user submits a form that includes an email field, the application will check if the form is associated with a company.
2. If both conditions are met, the application sends a request to the company's API endpoint to get additional data about the user.
3. The third-party data is stored in the database and associated with the form response.
4. Form owners can view this enriched user data alongside regular form submissions.

### API Requirements for Third-Party Sites

Third-party sites can also push data directly to the application using the webhook endpoint. The expected format is:

```json
{
  "user_email": "user@example.com",
  "company_code": "company_referral_code",
  "user_data": {
    "name": "John Doe",
    "profile": {
      "age": 30,
      "location": "New York"
    },
    "activity": {
      "last_login": "2023-07-18T14:25:30Z",
      "products_viewed": ["Product A", "Product B"]
    }
  }
}
```

This feature allows you to collect comprehensive user information while keeping your forms simple and user-friendly.

### Setting Up Third-Party Integration

To enable third-party data integration:

1. Create a company in the system and note its referral code.
2. Create forms that are associated with this company.
3. Ensure your forms include at least one field that collects user email.
4. Configure the third-party site to either:
   - Respond to GET requests with parameters `user_email`, `company_name`, `form_title`, and `referral_code`
   - Push data to your webhook endpoint `/api/third-party-webhook` in the format shown above

No API keys are required, making it easy to integrate with multiple services.

### Testing the Third-Party Integration

To test the integration locally, you can use the included mock tools:

1. **Test with the Mock Third-Party Server**: 
   ```bash
   # Start the mock API server in one terminal
   python mock_third_party_server.py --port 5001
   
   # Start your main application in another terminal
   python app.py
   ```
   
   The mock server includes pre-defined test users:
   - john.doe@example.com
   - jane.smith@example.com
   
   When you submit a form with one of these email addresses, your app will try to fetch data from the mock server.

2. **Test with the Webhook Example**:
   ```bash
   # After submitting a form with an email address
   python webhook_example.py --email "user@example.com" --company "your-company-code"
   ```
   
   This simulates a third-party site pushing data to your webhook endpoint.

3. **Manual Testing Workflow**:
   - Create a company in your app and note its referral code
   - Create a form associated with this company
   - Add an email field to your form
   - Submit the form with a test email
   - Verify that the app fetches data from the mock server
   - Check the form responses section to view the fetched third-party data 