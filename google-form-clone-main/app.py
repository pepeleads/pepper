from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from sqlalchemy.orm import relationship
from datetime import datetime
import PyPDF2
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.jinja_env.filters['fromjson'] = json.loads

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def fromjson_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []
app.jinja_env.filters['fromjson'] = fromjson_filter

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    forms = db.relationship('Form', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    referral_code = db.Column(db.String(50), unique=True, nullable=False)
    forms = db.relationship('Form', backref='company', lazy=True)

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_form_user'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', name='fk_form_company'), nullable=True)
    questions = db.relationship('Question', backref='form', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('Response', backref='form', lazy=True, cascade='all, delete-orphan')

class SubQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    parent_option = db.Column(db.String(255), nullable=False)  # Which option this subquestion belongs to
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # text, multiple_choice, checkbox
    options = db.Column(db.Text)  # JSON string for multiple choice/checkbox options
    required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, nullable=False)
    nesting_level = db.Column(db.Integer, default=1)  # 1 for first level, 2 for nested, etc.
    
    # The answers to this subquestion
    answers = relationship('SubQuestionAnswer', backref='subquestion', lazy=True, cascade='all, delete-orphan')
    
    def get_options(self):
        if self.options:
            try:
                return json.loads(self.options)
            except:
                return []
        return []
    
    def set_options(self, options):
        self.options = json.dumps(options)

class SubQuestionAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    subquestion_id = db.Column(db.Integer, db.ForeignKey('sub_question.id'), nullable=False)
    selected_option = db.Column(db.String(255), nullable=True)  # For multiple choice/checkbox
    answer_text = db.Column(db.Text, nullable=True)  # For text questions

# Modify the Question model to include relationship to SubQuestions
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # text, multiple_choice, checkbox
    options = db.Column(db.Text)  # JSON string for multiple choice/checkbox options
    required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, nullable=False)
    
    # Add relationship to subquestions
    subquestions = relationship('SubQuestion', backref='parent_question', lazy=True, 
                               cascade='all, delete-orphan')

    def get_options(self):
        import json
        if self.options:
            try:
                return json.loads(self.options)
            except:
                return []
        return []

    def set_options(self, options):
        import json
        self.options = json.dumps(options)

# Update the Response model to include subquestion answers
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', name='fk_response_company'), nullable=True)
    answers = relationship('Answer', backref='response', lazy=True, cascade='all, delete-orphan')
    subquestion_answers = relationship('SubQuestionAnswer', backref='response', lazy=True, 
                                      cascade='all, delete-orphan')
    company = relationship('Company', backref='responses')


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)

class PDFUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=True)
    user = db.relationship('User', backref='pdf_uploads')
    form = db.relationship('Form', backref='pdf_upload')

class ThirdPartyUserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    external_site = db.Column(db.String(255), nullable=False)
    user_identifier = db.Column(db.String(255), nullable=False)  # Email, ID or other identifier used for the request
    data = db.Column(db.Text, nullable=True)  # JSON string containing all user data
    request_sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_received_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    
    # Relationship to the response
    response = db.relationship('Response', backref='third_party_data')
    
    def set_data(self, data_dict):
        self.data = json.dumps(data_dict)
        
    def get_data(self):
        if self.data:
            try:
                return json.loads(self.data)
            except:
                return {}
        return {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes

@app.route('/')
def index():
    # Check if there are form_id and user_id query parameters
    form_id = request.args.get('form_id')
    user_id = request.args.get('user_id')
    
    # If both parameters exist, try to show the form
    if form_id and user_id:
        try:
            form_id = int(form_id)
            user_id = int(user_id)
            
            # Check if the form exists and belongs to the specified user
            form = Form.query.filter_by(id=form_id, user_id=user_id).first()
            
            if form:
                # If found, redirect to the form view
                return redirect(url_for('view_form', form_id=form_id))
            else:
                flash('Form not found or invalid user ID')
        except ValueError:
            flash('Invalid form ID or user ID')
    
    # If no parameters or invalid form, show the regular index page
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
            
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    forms = Form.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', forms=forms)

@app.route('/create_form', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        company_id = request.form.get('company_id')
        
        # Validate company ownership if company_id is provided
        if company_id:
            company = Company.query.get(company_id)
            if not company:
                flash('Invalid company selected')
                return redirect(url_for('create_form'))
        else:
            company_id = session.get('referral_company_id')
        
        form = Form(
            title=title,
            description=description,
            user_id=current_user.id,
            company_id=company_id
        )
        db.session.add(form)
        db.session.commit()
        
        # Clear referral from session after form creation
        session.pop('referral_company_id', None)
        
        return redirect(url_for('edit_form', form_id=form.id))
    
    # For GET request, get available companies and company from query param
    companies = Company.query.all()
    selected_company_id = request.args.get('company')
    selected_company = None
    
    if selected_company_id:
        selected_company = Company.query.get(selected_company_id)
    
    return render_template('create_form.html', 
                          companies=companies, 
                          selected_company=selected_company)

@app.route('/form/<int:form_id>')
def view_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    # Get all subquestions for this form
    subquestions = SubQuestion.query.join(Question).filter(Question.form_id == form_id).all()

    # Process each question to handle nested structures
    for question in form.questions:
        if question.question_type in ['radio', 'multiple_choice']:
            try:
                # Parse options with full nested structure
                question.nested_options = json.loads(question.options or '[]')
                
                # If options is a plain array, convert to nested format
                if question.nested_options and isinstance(question.nested_options[0], str):
                    question.nested_options = [{"text": opt, "subquestions": []} for opt in question.nested_options]
            except (json.JSONDecodeError, TypeError, IndexError):
                # Fallback for legacy data format
                try:
                    raw_options = question.get_options()
                    # Convert simple options to the nested format
                    question.nested_options = [
                        {"text": opt, "subquestions": []} 
                        for opt in raw_options if opt
                    ]
                except Exception:
                    # Last resort fallback
                    question.nested_options = []

    # Sort questions by order
    form.questions.sort(key=lambda q: q.order)
    
    return render_template('view_form.html', form=form, subquestions=subquestions)

@app.route('/form/<int:form_id>/edit')
@login_required
def edit_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        return redirect(url_for('dashboard'))

    # decode JSON-encoded options into a new attribute
    for q in form.questions:
        try:
            q.parsed_options = json.loads(q.options) if q.options else []
        except ValueError:
            q.parsed_options = []

    return render_template('edit_form.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/form/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    try:
        # Get company ID from form or session
        company_id = form.company_id or session.get('referral_company_id')
        
        # Create response
        response = Response(
            form_id=form_id,
            company_id=company_id
        )
        db.session.add(response)
        db.session.flush()  # Assign ID without committing
        
        # Process form data
        form_data = request.form.to_dict(flat=False)
        
        # Track if we need to request third-party data
        third_party_data_needed = False
        user_email = None
        
        # Handle main questions
        for question in form.questions:
            field_name = f'question_{question.id}'
            
            if question.question_type == 'checkbox':
                # Handle multiple checkbox selections
                answer_texts = request.form.getlist(field_name)
                answer_text = ', '.join(answer_texts) if answer_texts else None
            else:
                # Get single value answers
                values = form_data.get(field_name, [])
                answer_text = values[0] if values else None
                
            if answer_text:
                # Check if this is an email field (for third-party data requests)
                if question.question_text.lower().find('email') >= 0 and '@' in answer_text:
                    user_email = answer_text
                    third_party_data_needed = True
                
                answer = Answer(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)
                
                # If this is a choice question and has subquestions, check for selected option
                if question.question_type in ['radio', 'multiple_choice', 'checkbox'] and answer_text:
                    selected_options = answer_text.split(', ') if question.question_type == 'checkbox' else [answer_text]
                    
                    # Find subquestions for these selected options
                    for selected_option in selected_options:
                        # Get level 1 subquestions for this option
                        subquestions = SubQuestion.query.filter_by(
                            question_id=question.id,
                            parent_option=selected_option,
                            nesting_level=1
                        ).all()
                        
                        # Process each subquestion
                        for subq in subquestions:
                            subq_field_name = f'subq_{subq.id}'
                            
                            if subq.question_type == 'checkbox':
                                subq_values = request.form.getlist(subq_field_name)
                                subq_answer = ', '.join(subq_values) if subq_values else None
                            else:
                                subq_values = form_data.get(subq_field_name, [])
                                subq_answer = subq_values[0] if subq_values else None
                            
                            if subq_answer:
                                # Check if this is an email field (for third-party data requests)
                                if subq.question_text.lower().find('email') >= 0 and '@' in subq_answer:
                                    user_email = subq_answer
                                    third_party_data_needed = True
                                
                                sq_answer = SubQuestionAnswer(
                                    response_id=response.id,
                                    subquestion_id=subq.id,
                                    selected_option=subq_answer if subq.question_type in ['radio', 'multiple_choice', 'checkbox'] else None,
                                    answer_text=subq_answer
                                )
                                db.session.add(sq_answer)
                                
                                # Handle level 2 nested subquestions
                                if subq.question_type in ['radio', 'multiple_choice', 'checkbox']:
                                    nested_selected_options = subq_answer.split(', ') if subq.question_type == 'checkbox' else [subq_answer]
                                    
                                    for nested_option in nested_selected_options:
                                        nested_parent = f"{selected_option}|{nested_option}"
                                        nested_subqs = SubQuestion.query.filter_by(
                                            question_id=question.id,
                                            parent_option=nested_parent,
                                            nesting_level=2
                                        ).all()
                                        
                                        for nested_subq in nested_subqs:
                                            nested_field_name = f'nested_subq_{nested_subq.id}'
                                            
                                            if nested_subq.question_type == 'checkbox':
                                                nested_values = request.form.getlist(nested_field_name)
                                                nested_answer = ', '.join(nested_values) if nested_values else None
                                            else:
                                                nested_values = form_data.get(nested_field_name, [])
                                                nested_answer = nested_values[0] if nested_values else None
                                            
                                            if nested_answer:
                                                # Check if this is an email field (for third-party data requests)
                                                if nested_subq.question_text.lower().find('email') >= 0 and '@' in nested_answer:
                                                    user_email = nested_answer
                                                    third_party_data_needed = True
                                                    
                                                nested_sq_answer = SubQuestionAnswer(
                                                    response_id=response.id,
                                                    subquestion_id=nested_subq.id,
                                                    selected_option=nested_answer if nested_subq.question_type in ['radio', 'multiple_choice', 'checkbox'] else None,
                                                    answer_text=nested_answer
                                                )
                                                db.session.add(nested_sq_answer)
        
        # Request third-party data if needed and user email is available
        if third_party_data_needed and user_email and form.company:
            # Create a record for the data request
            third_party_data = ThirdPartyUserData(
                response_id=response.id,
                external_site=form.company.name,
                user_identifier=user_email,
                status='pending'
            )
            db.session.add(third_party_data)
            
            # We'll request the data asynchronously after committing
            
        # Commit all the answers and subquestion answers
        db.session.commit()
        
        # Now that we've committed, trigger the third-party data request
        if third_party_data_needed and user_email and form.company:
            # In a real application, you would use a background task or queue for this
            # Here we'll make a synchronous request for simplicity
            try:
                request_third_party_data(third_party_data.id)
            except Exception as e:
                print(f"Error requesting third-party data: {str(e)}")
                # Log the error but continue - don't stop the form submission process
        
        flash('Form submitted successfully!')
        return redirect(url_for('form_submitted', form_id=form_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting form: {str(e)}')
        return redirect(url_for('view_form', form_id=form_id))

def request_third_party_data(third_party_data_id):
    """
    Function to request user data from a third-party site.
    In a production application, this would be handled by a background worker.
    """
    # Get the data request record
    third_party_data = ThirdPartyUserData.query.get(third_party_data_id)
    if not third_party_data:
        return
    
    # Get the company/form info
    response = third_party_data.response
    form = Form.query.get(response.form_id)
    company = Company.query.get(form.company_id) if form.company_id else None
    
    if not company:
        third_party_data.status = 'failed'
        third_party_data.set_data({"error": "No company information available"})
        db.session.commit()
        return
    
    try:
        # This would be the URL of the third-party API
        # For now, we'll use a placeholder URL based on company referral code
        api_url = f"https://{company.referral_code}.example.com/api/get-user-data"
        
        # In a real application, you would make an HTTP request without API key:
        # import requests
        # params = {
        #     "user_email": third_party_data.user_identifier,
        #     "company_name": company.name,
        #     "form_title": form.title,
        #     "referral_code": company.referral_code
        # }
        # response = requests.get(api_url, params=params)
        # 
        # if response.status_code == 200:
        #     user_data = response.json()
        # else:
        #     raise Exception(f"API returned status code {response.status_code}")
        
        # For this example, we'll simulate a successful response
        # with some dummy user data
        user_data = {
            "name": "Sample User",
            "email": third_party_data.user_identifier,
            "profile": {
                "age": 30,
                "location": "New York",
                "occupation": "Software Developer"
            },
            "activity": {
                "last_login": datetime.utcnow().isoformat(),
                "products_viewed": ["Product A", "Product B"],
                "purchases": [
                    {"id": "P12345", "name": "Product X", "price": 49.99}
                ]
            }
        }
        
        # Update the record with the received data
        third_party_data.set_data(user_data)
        third_party_data.status = 'completed'
        third_party_data.response_received_at = datetime.utcnow()
        
        db.session.commit()
        return user_data
        
    except Exception as e:
        # Handle errors
        error_message = str(e)
        third_party_data.status = 'failed'
        third_party_data.set_data({"error": error_message})
        db.session.commit()
        return None

# Add a success page route
@app.route('/form/<int:form_id>/submitted')
def form_submitted(form_id):
    form = Form.query.get_or_404(form_id)
    return render_template('form_submitted.html', form=form, now=datetime.utcnow)

@app.route('/form/<int:form_id>/responses')
@login_required
def view_responses(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to view these responses')
        return redirect(url_for('dashboard'))
    
    responses = Response.query.filter_by(form_id=form_id).all()
    return render_template('view_responses.html', form=form, responses=responses)

@app.route('/form/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to delete this form')
        return redirect(url_for('dashboard'))
    
    try:
        # Step 1: Delete associated PDF file and record
        pdf_upload = PDFUpload.query.filter_by(form_id=form.id).first()
        if pdf_upload:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_upload.filename)
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception as e:
                    print(f"Error deleting PDF file: {e}")
            db.session.delete(pdf_upload)
            db.session.commit()
        
        # Step 2: Delete all answers
        answers = Answer.query.join(Response).filter(Response.form_id == form_id).all()
        for answer in answers:
            db.session.delete(answer)
        db.session.commit()
        
        # Step 3: Delete all responses
        responses = Response.query.filter_by(form_id=form_id).all()
        for response in responses:
            db.session.delete(response)
        db.session.commit()
        
        # Step 4: Delete all questions
        questions = Question.query.filter_by(form_id=form_id).all()
        for question in questions:
            db.session.delete(question)
        db.session.commit()
        
        # Step 5: Finally, delete the form
        db.session.delete(form)
        db.session.commit()
        
        flash('Form and all associated data deleted successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting form: {str(e)}')
        return redirect(url_for('dashboard'))
    
    return redirect(url_for('dashboard'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def extract_questions_from_pdf(pdf_path):
    questions = []
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                lines = text.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    
                    # Skip empty lines
                    if not line:
                        i += 1
                        continue
                    
                    # Function to clean text - only keep alphabets and spaces
                    def clean_text(text):
                        # Keep only alphabets and spaces
                        text = ''.join(c for c in text if c.isalpha() or c == ' ')
                        # Remove extra spaces
                        text = ' '.join(text.split())
                        return text
                    
                    # Check for multiple choice questions
                    if any(option in line for option in ['(a)', '(b)', '(c)', '(d)', '(A)', '(B)', '(C)', '(D)']):
                        question_text = clean_text(line)
                        options = []
                        while i + 1 < len(lines) and any(option in lines[i + 1] for option in ['(a)', '(b)', '(c)', '(d)', '(A)', '(B)', '(C)', '(D)']):
                            i += 1
                            option_text = lines[i].strip()
                            # Remove option markers and clean text
                            option_text = option_text.split(')', 1)[1].strip() if ')' in option_text else option_text
                            option_text = clean_text(option_text)
                            options.append(option_text)
                        
                        questions.append({
                            'text': question_text,
                            'type': 'multiple_choice',
                            'options': options,
                            'required': True
                        })
                    
                    # Check for checkbox questions
                    elif any(checkbox in line for checkbox in ['[ ]', '[  ]', '□']):
                        question_text = clean_text(line)
                        options = []
                        while i + 1 < len(lines) and any(checkbox in lines[i + 1] for checkbox in ['[ ]', '[  ]', '□']):
                            i += 1
                            option_text = lines[i].strip()
                            # Remove checkbox markers and clean text
                            option_text = option_text.replace('[ ]', '').replace('[  ]', '').replace('□', '').strip()
                            option_text = clean_text(option_text)
                            options.append(option_text)
                        
                        questions.append({
                            'text': question_text,
                            'type': 'checkbox',
                            'options': options,
                            'required': True
                        })
                    
                    # Check for text input questions (with underline)
                    elif '_' in line or '___' in line:
                        # Extract the question part before the underline
                        question_text = line.split('_')[0].strip()
                        question_text = clean_text(question_text)
                        if question_text.endswith('?'):
                            questions.append({
                                'text': question_text,
                                'type': 'text',
                                'required': True
                            })
                    
                    # Check for regular questions
                    elif line.endswith('?'):
                        # Check if it's a required question (marked with *)
                        required = '*' in line
                        question_text = line.replace('*', '').strip()
                        question_text = clean_text(question_text)
                        
                        # Check if next line has options
                        if i + 1 < len(lines) and any(option in lines[i + 1] for option in ['(a)', '(b)', '(c)', '(d)', '(A)', '(B)', '(C)', '(D)']):
                            options = []
                            while i + 1 < len(lines) and any(option in lines[i + 1] for option in ['(a)', '(b)', '(c)', '(d)', '(A)', '(B)', '(C)', '(D)']):
                                i += 1
                                option_text = lines[i].strip()
                                # Remove option markers and clean text
                                option_text = option_text.split(')', 1)[1].strip() if ')' in option_text else option_text
                                option_text = clean_text(option_text)
                                options.append(option_text)
                            
                            questions.append({
                                'text': question_text,
                                'type': 'multiple_choice',
                                'options': options,
                                'required': required
                            })
                        else:
                            questions.append({
                                'text': question_text,
                                'type': 'text',
                                'required': required
                            })
                    
                    i += 1
                    
    except Exception as e:
        flash(f'Error processing PDF: {str(e)}')
    return questions

@app.route('/form/<int:form_id>/update', methods=['POST'])
@login_required
def update_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        return jsonify({'error':'Unauthorized'}), 403

    data = request.get_json(force=True)
    if 'questions' not in data:
        return jsonify({'error':'Invalid payload'}), 400

    try:
        # Begin transaction
        # Step 1: Delete all old subquestions (this will cascade to subquestion answers)
        subquestions = SubQuestion.query.join(Question).filter(Question.form_id == form_id).all()
        for sq in subquestions:
            db.session.delete(sq)
        
        # Step 2: Delete old questions (which will cascade to their answers)
        questions = Question.query.filter_by(form_id=form_id).all()
        for q in questions:
            db.session.delete(q)
        
        db.session.commit()

        # Step 3: Re-create questions with their subquestions
        for idx, q_data in enumerate(data['questions']):
            question_type = q_data['question_type']
            
            # Create main question
            question = Question(
                form_id=form_id,
                question_text=q_data['question_text'],
                question_type=question_type,
                required=q_data.get('required', False),
                order=idx
            )
            
            # Process options for choice-based questions
            if question_type in ['radio', 'multiple_choice', 'checkbox']:
                options_data = q_data.get('options', [])
                
                # If options is a string, try to parse it
                if isinstance(options_data, str):
                    try:
                        options_data = json.loads(options_data)
                    except:
                        options_data = []
                
                # Save options as JSON
                question.options = json.dumps(options_data)
                
                # Add question to session so we can get its ID for subquestions
                db.session.add(question)
                db.session.flush()  # This assigns the ID but doesn't commit
                
                # Process subquestions if they exist
                for option_idx, option_data in enumerate(options_data):
                    # Check if this is a simple option string or an object with subquestions
                    if isinstance(option_data, dict):
                        option_text = option_data.get('text', '')
                        subquestions_data = option_data.get('subquestions', [])
                        
                        # Process each subquestion for this option
                        for subq_idx, subq_data in enumerate(subquestions_data):
                            sub_q = SubQuestion(
                                question_id=question.id,
                                parent_option=option_text,
                                question_text=subq_data.get('text', ''),
                                question_type=subq_data.get('type', 'text'),
                                required=subq_data.get('required', False),
                                order=subq_idx,
                                nesting_level=1
                            )
                            
                            # Handle options for subquestions
                            if 'options' in subq_data:
                                sub_options = subq_data['options']
                                if isinstance(sub_options, list):
                                    sub_q.options = json.dumps(sub_options)
                                    
                                    # Process nested subquestions (level 2)
                                    for nested_idx, nested_option in enumerate(sub_options):
                                        if isinstance(nested_option, dict) and 'subquestions' in nested_option:
                                            for nested_subq_idx, nested_subq in enumerate(nested_option['subquestions']):
                                                nested_q = SubQuestion(
                                                    question_id=question.id,
                                                    parent_option=f"{option_text}|{nested_option.get('text', '')}",
                                                    question_text=nested_subq.get('text', ''),
                                                    question_type=nested_subq.get('type', 'text'),
                                                    required=nested_subq.get('required', False),
                                                    order=nested_subq_idx,
                                                    nesting_level=2
                                                )
                                                
                                                if 'options' in nested_subq:
                                                    nested_q.options = json.dumps(nested_subq['options'])
                                                
                                                db.session.add(nested_q)
                            
                            db.session.add(sub_q)
            else:
                # For non-choice questions, just save without options
                db.session.add(question)
        
        # Commit all changes
        db.session.commit()
        return jsonify({'message':'Form updated successfully', 'status': 'success'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/form/<int:form_id>/share')
@login_required
def share_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to share this form')
        return redirect(url_for('dashboard'))
    
    # Generate the full shareable URL
    # Getting the base URL with protocol (http/https)
    if request.headers.get('X-Forwarded-Proto'):
        proto = request.headers.get('X-Forwarded-Proto')
    else:
        proto = 'https' if request.is_secure else 'http'
    
    host = request.host
    base_url = f"{proto}://{host}"
    
    # Create the share URL with both parameters
    share_url = f"{base_url}/?form_id={form.id}&user_id={form.user_id}"
    
    # Print for debugging
    print(f"Share URL: {share_url}")
    
    return render_template('share_form.html', form=form, share_url=share_url)

@app.route('/upload_pdf', methods=['GET', 'POST'])
@login_required
def upload_pdf():
    if request.method == 'POST':
        if 'pdf' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['pdf']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Create PDF upload record
            pdf_upload = PDFUpload(
                filename=unique_filename,
                original_filename=filename,
                user_id=current_user.id,
                form_id=None  # Will be updated after form creation
            )
            db.session.add(pdf_upload)
            db.session.commit()
            
            # Extract questions and create form
            questions = extract_questions_from_pdf(file_path)
            if questions:
                form = Form(
                    title=f"Form from {filename}",
                    description="Automatically generated from PDF",
                    user_id=current_user.id,
                    company_id=session.get('referral_company_id')
                )
                db.session.add(form)
                db.session.commit()
                
                # Update PDF upload with form ID
                pdf_upload.form_id = form.id
                
                # Add questions to form
                for i, q in enumerate(questions):
                    question = Question(
                        form_id=form.id,
                        question_text=q['text'],
                        question_type=q['type'],
                        required=q['required'],
                        order=i
                    )
                    if 'options' in q:
                        question.set_options(q['options'])
                    db.session.add(question)
                
                db.session.commit()
                
                # Clear referral from session after form creation
                session.pop('referral_company_id', None)
                
                flash('Form generated successfully!')
                return redirect(url_for('edit_form', form_id=form.id))
            else:
                flash('No questions found in the PDF')
                return redirect(url_for('upload_pdf'))
    
    return render_template('upload_pdf.html')

def parse_mindmap_to_form(mindmap_text):
    form_data = {
        "title": "",
        "sections": []
    }
    
    current_section = None
    current_field = None
    
    lines = mindmap_text.split('\n')
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Count indentation level (number of spaces at start)
        indent_level = len(line) - len(line.lstrip())
        
        # Root level - Form title
        if indent_level == 0:
            form_data["title"] = line.strip()
            
        # First level - Sections
        elif indent_level == 2:  # Two spaces for sections
            # Remove "Section X:" prefix if present
            section_name = line.strip()
            if ":" in section_name:
                section_name = section_name.split(":", 1)[1].strip()
            
            current_section = {
                "name": section_name,
                "fields": []
            }
            form_data["sections"].append(current_section)
            
        # Second level - Fields
        elif indent_level == 4:  # Four spaces for fields
            field_parts = line.strip().split('|')
            field_label = field_parts[0].strip()
            field_type = "text"  # default type
            
            if len(field_parts) > 1:
                type_spec = field_parts[1].strip().lower()
                if type_spec in ['text', 'dropdown', 'checkbox', 'radio', 'email']:
                    field_type = type_spec
            
            current_field = {
                "label": field_label,
                "type": field_type,
                "options": []
            }
            current_section["fields"].append(current_field)
            
        # Third level - Options (for dropdown/checkbox/radio)
        elif indent_level == 6 and current_field:  # Six spaces for options
            if current_field["type"] in ['dropdown', 'checkbox', 'radio']:
                current_field["options"].append(line.strip())
    
    return form_data

@app.route('/upload_mindmap', methods=['GET', 'POST'])
@login_required
def upload_mindmap():
    if request.method == 'POST':
        mindmap_text = request.form.get('mindmap_text')
        if not mindmap_text:
            flash('No mindmap text provided')
            return redirect(request.url)
            
        try:
            form_data = parse_mindmap_to_form(mindmap_text)
            
            form = Form(
                title=form_data["title"],
                description="Generated from mindmap",
                user_id=current_user.id,
                company_id=session.get('referral_company_id')
            )
            db.session.add(form)
            db.session.commit()
            
            order = 0
            for section in form_data["sections"]:
                for field in section["fields"]:
                    type_mapping = {
                        'text': 'text',
                        'email': 'email',
                        'dropdown': 'multiple_choice',
                        'checkbox': 'checkbox',
                        'radio': 'radio'
                    }
                    
                    question_type = type_mapping.get(field["type"], 'text')
                    
                    question = Question(
                        form_id=form.id,
                        question_text=field["label"],
                        question_type=question_type,
                        required=True,
                        order=order
                    )
                    
                    if question_type in ['multiple_choice', 'checkbox', 'radio'] and field["options"]:
                        question.set_options(field["options"])
                    
                    db.session.add(question)
                    order += 1
            
            db.session.commit()
            
            # Clear referral from session after form creation
            session.pop('referral_company_id', None)
            
            flash('Form generated successfully from mindmap!')
            return redirect(url_for('edit_form', form_id=form.id))
            
        except Exception as e:
            flash(f'Error processing mindmap: {str(e)}')
            return redirect(url_for('upload_mindmap'))
    
    return render_template('upload_mindmap.html')

@app.route('/manage_companies', methods=['GET', 'POST'])
@login_required
def manage_companies():
    if request.method == 'POST':
        name = request.form.get('name')
        referral_code = request.form.get('referral_code')
        
        if not name or not referral_code:
            flash('Company name and referral code are required')
            return redirect(url_for('manage_companies'))
            
        company = Company(name=name, referral_code=referral_code)
        db.session.add(company)
        db.session.commit()
        flash('Company added successfully')
        return redirect(url_for('manage_companies'))
        
    companies = Company.query.all()
    return render_template('manage_companies.html', companies=companies)

@app.route('/referral/<referral_code>')
def handle_referral(referral_code):
    company = Company.query.filter_by(referral_code=referral_code).first()
    if not company:
        flash('Invalid referral link')
        return redirect(url_for('index'))
        
    # Store company_id in session for form creation
    session['referral_company_id'] = company.id
    return redirect(url_for('create_form'))

@app.route('/form/<int:form_id>/responses/<int:response_id>/user-data')
@login_required
def view_third_party_user_data(form_id, response_id):
    """
    View the third-party user data for a specific form response.
    """
    # Check if the user has permission to view this response
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to view this data')
        return redirect(url_for('dashboard'))
    
    response = Response.query.get_or_404(response_id)
    if response.form_id != form_id:
        flash('Invalid response ID')
        return redirect(url_for('view_responses', form_id=form_id))
    
    # Get the third-party data record
    third_party_data = ThirdPartyUserData.query.filter_by(response_id=response_id).first()
    
    if not third_party_data:
        flash('No third-party data available for this response')
        return redirect(url_for('view_responses', form_id=form_id))
    
    # Render a template with the data
    return render_template('user_data.html', 
                          form=form, 
                          response=response, 
                          third_party_data=third_party_data)

@app.route('/api/third-party-webhook', methods=['POST'])
def third_party_webhook():
    """
    Endpoint for third-party sites to push user data to our application.
    This is an alternative to our application pulling the data.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Check required fields
    required_fields = ["user_email", "company_code", "user_data"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Find the company by referral code
    company = Company.query.filter_by(referral_code=data["company_code"]).first()
    if not company:
        return jsonify({"error": "Invalid company code"}), 404
    
    # Find any responses using this email
    # This is a simple implementation - you might want a more specific way to match
    user_email = data["user_email"]
    
    try:
        # Find responses that have this email in any answer
        email_answers = Answer.query.join(Question).join(Response).join(Form).filter(
            Form.company_id == company.id,
            Answer.answer_text.contains(user_email)
        ).all()
        
        response_ids = [answer.response_id for answer in email_answers]
        
        if not response_ids:
            return jsonify({"error": "No matching responses found"}), 404
        
        # Update or create third-party data records for each response
        updated_records = []
        
        for response_id in response_ids:
            third_party_data = ThirdPartyUserData.query.filter_by(
                response_id=response_id,
                external_site=company.name
            ).first()
            
            if not third_party_data:
                # Create a new record
                third_party_data = ThirdPartyUserData(
                    response_id=response_id,
                    external_site=company.name,
                    user_identifier=user_email,
                    request_sent_at=datetime.utcnow()  # Set to now since it's pushed to us
                )
                db.session.add(third_party_data)
            
            # Update the data
            third_party_data.set_data(data["user_data"])
            third_party_data.status = 'completed'
            third_party_data.response_received_at = datetime.utcnow()
            
            updated_records.append(third_party_data.id)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Updated {len(updated_records)} response records",
            "updated_records": updated_records
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)