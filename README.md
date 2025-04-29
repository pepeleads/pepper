# Google Forms Clone

A full-featured Google Forms clone built with Flask that allows you to create, share, and manage online forms with beautiful templates.

## Features

- **User Authentication**: Secure login and registration system
- **Form Creation**: Create custom forms with various question types
- **Predefined Templates**: Start from beautiful, ready-to-use templates
- **Response Collection**: Collect and analyze form responses
- **Form Sharing**: Share forms with others through customizable links
- **PDF Import**: Create forms by uploading PDFs
- **Mindmap Import**: Generate forms from mindmap text
- **Company Management**: Track responses by company with referral codes
- **UTM Tracking**: Track marketing campaigns with UTM parameters

## Question Types Supported

- Text
- Email
- Number
- Telephone
- URL
- Date
- Time
- Color
- File Upload
- Multiple Choice (Radio)
- Checkboxes
- Dropdown Selections
- Nested Questions (Conditional)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/google-forms-clone.git
cd google-forms-clone
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the application:
```bash
python app.py
```

## Usage

1. Register a new account or login
2. Access the dashboard to see your forms and templates
3. Create a new form or use a predefined template
4. Add questions and customize your form
5. Share your form with others
6. View and analyze responses

## Screenshots

(Add screenshots here)

## Technologies Used

- Flask: Web framework
- SQLite: Database
- SQLAlchemy: ORM
- Flask-Migrate: Database migrations
- Bootstrap: Frontend framework
- JavaScript: Interactive functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details. 