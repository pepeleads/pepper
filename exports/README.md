# Survey Response Exports

This directory contains exported survey responses in various formats.

## JSON Exports

JSON exports of survey responses are saved in the `survey_responses/` subdirectory. Each response is saved as a separate JSON file with a unique filename containing the form ID, response ID, and timestamp.

### File Format

The JSON files have the following structure:

```json
{
  "response_id": 123,
  "form_id": 456,
  "form_title": "Customer Feedback",
  "submitted_at": "2025-05-15T14:30:25.123456",
  "utm_data": {
    "source": "email",
    "medium": "campaign",
    "campaign": "spring2025",
    "content": "banner",
    "term": "survey"
  },
  "device_type": "mobile",
  "company_id": 789,
  "company_name": "ACME Inc.",
  "answers": [
    {
      "question_id": 1,
      "question_text": "What is your name?",
      "question_type": "text",
      "answer_text": "John Doe"
    },
    {
      "question_id": 2,
      "question_text": "Which products do you use?",
      "question_type": "checkbox",
      "answer_text": "Product A, Product C",
      "subquestion_answers": [
        {
          "subquestion_id": 5,
          "subquestion_text": "How would you rate Product A?",
          "subquestion_type": "radio",
          "parent_option": "Product A",
          "answer_text": "Excellent"
        }
      ]
    }
  ]
}
```

### Export Methods

There are two ways responses are exported to JSON:

1. **Automatic export on submission**: Each time a user submits a form, the response is automatically exported to a JSON file.

2. **Manual export from responses view**: From the responses page, an admin user can export all responses for a form as a single JSON file by clicking the "Export to JSON" button.

### Programmatic Access

If you need to programmatically export responses, you can use the `export_response_to_json` helper function:

```python
from app import export_response_to_json

# Get the response and form objects
response = Response.query.get(response_id)
form = Form.query.get(form_id)

# Export the response to JSON
response_data, file_path = export_response_to_json(response, form)
```

This function returns both the JSON data as a Python dictionary and the path to the saved file. 