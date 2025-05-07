from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from sqlalchemy.orm import relationship
from datetime import datetime
import PyPDF2
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask_moment import Moment
import json
import random
import requests
from datetime import datetime
import uuid
from urllib.parse import urlencode
import copy
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.jinja_env.filters['fromjson'] = json.loads

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Moment for handling dates and times in templates
moment = Moment(app)

# Add context processor for current date
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

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

def datetime_filter(date):
    if date:
        return date.strftime('%Y-%m-%d %H:%M:%S')
    return ''
app.jinja_env.filters['datetime'] = datetime_filter

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
    is_closed = db.Column(db.Boolean, default=False)  # New field to track if the form is closed/expired
    requires_consent = db.Column(db.Boolean, default=True)  # Require privacy policy and terms consent
    
    # Quiz-related fields
    is_quiz = db.Column(db.Boolean, default=False)  # Is this form a quiz?
    passing_score = db.Column(db.Integer, default=0)  # Passing score percentage
    show_score = db.Column(db.Boolean, default=True)  # Whether to show score to respondents
    sharing_token = db.Column(db.String(255), nullable=True)  # New field for sharing token

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
    answers = relationship('SubQuestionAnswer', backref='subquestion', lazy=True, cascade='all, delete-orphan')
    
# Add this model for tracking postbacks
class PostbackTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    tracking_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transaction_count = db.Column(db.Integer, default=0)
    
    form = db.relationship('Form', backref='postback_tracking')

# Add this model for storing postback logs
class PostbackLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(100), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    payout = db.Column(db.Float, nullable=True)
    response_json = db.Column(db.Text, nullable=True)  # Store full response
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)

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
    
    # Quiz-related fields
    is_quiz_question = db.Column(db.Boolean, default=False)
    correct_answer = db.Column(db.Text, nullable=True)  # JSON string for correct answers
    points = db.Column(db.Integer, default=0)  # Points for correct answer
    feedback = db.Column(db.Text, nullable=True)  # Feedback for the question
    
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
    # Add UTM tracking fields
    utm_source = db.Column(db.String(100), nullable=True)
    utm_medium = db.Column(db.String(100), nullable=True)
    utm_campaign = db.Column(db.String(100), nullable=True)
    utm_content = db.Column(db.String(100), nullable=True)
    utm_term = db.Column(db.String(100), nullable=True)
    # New field for device type
    device_type = db.Column(db.String(20), nullable=True)
    # Privacy and Terms consent
    has_consent = db.Column(db.Boolean, default=False)
    
    # Quiz-related fields
    score = db.Column(db.Integer, nullable=True)  # Quiz score (total points)
    max_score = db.Column(db.Integer, nullable=True)  # Maximum possible score
    passed = db.Column(db.Boolean, nullable=True)  # Whether the user passed

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

class FormTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    questions = db.Column(db.Text)  # JSON string of questions
    category = db.Column(db.String(50))  # e.g., 'survey', 'registration', 'feedback'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    preview_image = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='templates')
    template_data = db.Column(db.Text, nullable=True)  # JSON string of complete template data

    def get_questions(self):
        try:
            return json.loads(self.questions) if self.questions else []
        except:
            return []

    def set_questions(self, questions):
        self.questions = json.dumps(questions)
        
    def get_template_data(self):
        """Get complete template data including questions and subquestions"""
        # Provide backward compatibility - if template_data field is empty, create from questions
        if not self.template_data:
            questions = self.get_questions()
            data = {
                'questions': questions,
                'subquestions': []
            }
            return json.dumps(data)
        return self.template_data
        
    def set_template_data(self, data):
        """Set template data. Accepts either JSON string or Python dict."""
        if isinstance(data, dict):
            self.template_data = json.dumps(data)
        else:
            self.template_data = data

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes

def generate_postback_url(form_id, user_id):
    # Generate a unique tracking ID
    tracking_id = str(uuid.uuid4())
    
    # Check if there's already a tracking for this form
    existing = PostbackTracking.query.filter_by(form_id=form_id).first()
    
    if existing:
        # Return existing tracking ID
        tracking_id = existing.tracking_id
    else:
        # Create new tracking record
        tracking = PostbackTracking(
            form_id=form_id,
            tracking_id=tracking_id
        )
        db.session.add(tracking)
        db.session.commit()
    
    # Build the postback URL
    base_url = "https://pepper-ads.com/postback"
    params = {
        'tracking_id': tracking_id,
        'user_id': user_id
    }
    
    return f"{base_url}?{urlencode(params)}"

# Add this function to save postback data to JSON file
def save_postback_to_json(postback_data):
    filename = 'postback_logs.json'
    
    # Try to read existing data
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
        
    # Add timestamp to data
    postback_data['logged_at'] = datetime.utcnow().isoformat()
    
    # Append new data
    data.append(postback_data)
    
    # Write back to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True

# Add this function after existing imports
def extract_utm_parameters(request):
    """Extract all UTM parameters from a request"""
    utm_params = {}
    
    # Common UTM parameters to extract
    utm_fields = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
    
    for param in utm_fields:
        value = request.args.get(param)
        if value:
            utm_params[param] = value
    
    return utm_params
def detect_device_type(user_agent):
    """Detect if user is on mobile, tablet, or desktop based on user agent string"""
    user_agent = user_agent.lower()
    
    # Check for mobile devices first
    if any(word in user_agent for word in ['iphone', 'android', 'mobile', 'phone']):
        # Special check for tablets that also have "android" in their UA
        if any(word in user_agent for word in ['ipad', 'tablet']):
            return 'tablet'
        return 'mobile'
    
    # Check for tablets
    elif any(word in user_agent for word in ['ipad', 'tablet']):
        return 'tablet'
    
    # Default to desktop
    else:
        return 'desktop'
    
@app.route('/')
def index():
    # Extract UTM parameters and session ID
    utm_params = extract_utm_parameters(request)
    session_id = request.args.get('session_id')
    
    # Detect device type
    device_type = request.args.get('device')
    if not device_type:
        device_type = detect_device_type(request.user_agent.string)
    
    # Store UTM, session and device data in session if present
    if 'utm_source' in utm_params:
        session['utm_source'] = utm_params['utm_source']
        session['utm_data'] = utm_params
    
    if session_id:
        session['session_id'] = session_id
        
    # Store device type
    session['device_type'] = device_type
    
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
                # If found, redirect to the form view - ensure we don't lose UTM parameters
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
    try:
        # Get user's forms
        forms = Form.query.filter_by(user_id=current_user.id).all()
        
        # Get predefined templates
        predefined_templates = FormTemplate.query.filter_by(is_public=True).all()
        
        # Get user's custom templates if they exist
        user_templates = []
        if hasattr(current_user, 'templates'):
            user_templates = current_user.templates
        
        # Combine user templates and predefined templates
        all_templates = list(user_templates) + list(predefined_templates)
        
        print(f"Forms: {len(forms)}, Templates: {len(all_templates)}")
        
        return render_template('dashboard.html', forms=forms, templates=all_templates)
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        return render_template('dashboard.html', forms=[], templates=[])

@app.route('/create_form', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        requires_consent = 'requires_consent' in request.form
        
        # Create a new form
        form = Form(
            title=title,
            description=description,
            user_id=current_user.id,
            company_id=session.get('referral_company_id'),
            requires_consent=requires_consent
        )
        
        # Add form to database
        db.session.add(form)
        db.session.commit()
        
        # Clear referral from session after form creation
        session.pop('referral_company_id', None)
        
        return redirect(url_for('edit_form', form_id=form.id))
        
    return render_template('create_form.html')

@app.route('/form/<int:form_id>')
def view_form(form_id):
    form = Form.query.get_or_404(form_id)
    token = request.args.get('token')
    
    # Check if the form is private and if the token is valid
    if form.is_private and (not token or token != form.sharing_token):
        if current_user.is_authenticated and form.user_id == current_user.id:
            pass  # Allow form owner to view
        else:
            flash('This form is private.', 'warning')
            return redirect(url_for('index'))
    
    return render_template('view_form.html', form=form)

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

# Helper function to export responses as JSON
def export_response_to_json(response, form):
    """
    Helper function to export a single response as JSON
    
    Args:
        response: The Response object to export
        form: The Form object the response belongs to
        
    Returns:
        dict: JSON-serializable dictionary of the response data
        str: Path to the saved JSON file
    """
    # Create response data structure
    response_data = {
        'response_id': response.id,
        'form_id': form.id,
        'form_title': form.title,
        'submitted_at': response.submitted_at.isoformat(),
        'utm_data': {
            'source': response.utm_source,
            'medium': response.utm_medium,
            'campaign': response.utm_campaign,
            'content': response.utm_content,
            'term': response.utm_term
        },
        'device_type': response.device_type,
        'company_id': response.company_id,
        'company_name': response.company.name if response.company else None,
        'answers': []
    }
    
    # Get all answers for this response
    for question in form.questions:
        answer = Answer.query.filter_by(
            response_id=response.id,
            question_id=question.id
        ).first()
        
        if answer:
            answer_data = {
                'question_id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'answer_text': answer.answer_text
            }
            
            # Get subquestion answers if applicable
            if question.question_type in ['radio', 'multiple_choice', 'checkbox']:
                # Get selected options
                selected_options = answer.answer_text.split(', ') if question.question_type == 'checkbox' else [answer.answer_text]
                
                # Get all subquestions for this question
                subquestions = SubQuestion.query.filter_by(question_id=question.id).all()
                
                subquestion_answers = []
                for subq in subquestions:
                    # Only include subquestions matching selected parent options
                    if any(opt in subq.parent_option for opt in selected_options):
                        sq_answer = SubQuestionAnswer.query.filter_by(
                            response_id=response.id,
                            subquestion_id=subq.id
                        ).first()
                        
                        if sq_answer:
                            subquestion_answers.append({
                                'subquestion_id': subq.id,
                                'subquestion_text': subq.question_text,
                                'subquestion_type': subq.question_type,
                                'parent_option': subq.parent_option,
                                'answer_text': sq_answer.answer_text
                            })
                
                # Add subquestion answers if any exist
                if subquestion_answers:
                    answer_data['subquestion_answers'] = subquestion_answers
            
            response_data['answers'].append(answer_data)
    
    # Create export directory if it doesn't exist
    export_path = os.path.join('exports', 'survey_responses')
    os.makedirs(export_path, exist_ok=True)
    
    # Create filename with form ID, response ID and timestamp
    timestamp = response.submitted_at.strftime('%Y%m%d%H%M%S')
    filename = f"response_{form.id}_{response.id}_{timestamp}.json"
    file_path = os.path.join(export_path, filename)
    
    # Write response to JSON file
    with open(file_path, 'w') as json_file:
        json.dump(response_data, json_file, indent=2)
    
    return response_data, file_path

@app.route('/form/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    # Check if the form is closed
    if form.is_closed:
        # Handle API requests
        if request.headers.get('X-Embedded') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'error',
                'message': 'This form is closed and no longer accepting responses.'
            }), 403
        
        # Handle regular form submission
        flash('This form is closed and no longer accepting responses.', 'danger')
        return redirect(url_for('view_form', form_id=form_id))
    
    # Check for privacy consent if required
    if form.requires_consent:
        privacy_consent = request.form.get('privacy_consent')
        if not privacy_consent or privacy_consent != 'on':
            # Handle API requests
            if request.headers.get('X-Embedded') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'error',
                    'message': 'You must agree to the privacy policy and terms and conditions to submit this form.'
                }), 400
            
            # Handle regular form submission
            flash('You must agree to the privacy policy and terms and conditions to submit this form.', 'danger')
            return redirect(url_for('view_form', form_id=form_id))
    
    try:
        # Get company ID from form or session
        company_id = form.company_id or session.get('referral_company_id')
        
        # Get UTM data safely using nested get calls with defaults
        utm_data = session.get('utm_data', {})
        
        # Create response
        response = Response(
            form_id=form_id,
            company_id=company_id,
            # Add UTM parameters from session
            utm_source=session.get('utm_source'),
            utm_medium=utm_data.get('utm_medium'),
            utm_campaign=utm_data.get('utm_campaign'),
            utm_content=utm_data.get('utm_content'),
            utm_term=utm_data.get('utm_term'),
            # Device type
            device_type=session.get('device_type', 'desktop'),
            # Set privacy consent
            has_consent=form.requires_consent and request.form.get('privacy_consent') == 'on'
        )
        db.session.add(response)
        db.session.flush()  # Assign ID without committing
        
        # Process form data
        form_data = request.form.to_dict(flat=False)
        
        # For debugging
        print("Received form data:")
        for key, value in form_data.items():
            print(f"{key}: {value}")
        
        # Variables for quiz scoring
        total_score = 0
        max_possible_score = 0
        answered_questions = []
        
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
                answer = Answer(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)
                answered_questions.append(question.id)
                
                # Calculate score for quiz questions
                if form.is_quiz and question.is_quiz_question:
                    max_possible_score += question.points
                    
                    # Check if answer is correct based on question type
                    if question.correct_answer:
                        correct_answer = json.loads(question.correct_answer)
                        
                        # For multiple choice and radio questions, check if the selected option matches
                        if question.question_type in ['radio', 'multiple_choice']:
                            # Correct answer is stored as the index of the option
                            try:
                                options = json.loads(question.options) if question.options else []
                                # If answer_text matches the text of the correct option, it's correct
                                if options and int(correct_answer) < len(options):
                                    correct_option_text = options[int(correct_answer)]['text']
                                    if answer_text == correct_option_text:
                                        total_score += question.points
                            except (ValueError, IndexError, json.JSONDecodeError) as e:
                                print(f"Error checking quiz answer: {str(e)}")
                        # For text, email, number, etc. - direct comparison
                        elif answer_text == correct_answer:
                            total_score += question.points
                
                # If this is a choice question and has subquestions, check for selected option
                if question.question_type in ['radio', 'multiple_choice', 'checkbox'] and answer_text:
                    selected_options = answer_text.split(', ') if question.question_type == 'checkbox' else [answer_text]
                    
                    # Process all subquestions directly using subq_id pattern
                    subquestions = SubQuestion.query.filter_by(question_id=question.id).all()
                    
                    for subq in subquestions:
                        # Only process subquestions matching the selected parent option
                        if any(opt in subq.parent_option for opt in selected_options):
                            subq_field_name = f'subq_{subq.id}'
                            
                            if subq.question_type == 'checkbox':
                                subq_values = request.form.getlist(subq_field_name)
                                subq_answer = ', '.join(subq_values) if subq_values else None
                            else:
                                subq_values = form_data.get(subq_field_name, [])
                                subq_answer = subq_values[0] if subq_values else None
                            
                            if subq_answer:
                                sq_answer = SubQuestionAnswer(
                                    response_id=response.id,
                                    subquestion_id=subq.id,
                                    selected_option=subq_answer if subq.question_type in ['radio', 'multiple_choice', 'checkbox'] else None,
                                    answer_text=subq_answer
                                )
                                db.session.add(sq_answer)
        
        # Update response with quiz score if this is a quiz
        if form.is_quiz:
            response.score = total_score
            response.max_score = max_possible_score
            # Check if the respondent passed the quiz based on passing percentage
            if max_possible_score > 0:
                score_percentage = (total_score / max_possible_score) * 100
                response.passed = score_percentage >= form.passing_score
            else:
                response.passed = False
        
        # Commit all the answers and subquestion answers
        db.session.commit()
        
        # Export the response as JSON
        _, export_path = export_response_to_json(response, form)
        
        print(f"Response exported to JSON: {export_path}")
        
        # Check if request is from an embedded iframe or AJAX request
        is_embedded = request.headers.get('X-Embedded') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Prepare data for response
        response_data = {
            'status': 'success',
            'message': 'Thank you! Your response has been recorded.',
            'custom_thank_you': form.thank_you_message if hasattr(form, 'thank_you_message') and form.thank_you_message else None,
            'redirect_url': url_for('dashboard'),
            'response_id': response.id
        }
        
        # Add quiz results if this is a quiz and we should show the score
        if form.is_quiz and form.show_score:
            response_data.update({
                'is_quiz': True,
                'score': total_score,
                'max_score': max_possible_score,
                'passing_score': form.passing_score,
                'passed': response.passed,
                'score_percentage': round((total_score / max_possible_score) * 100) if max_possible_score > 0 else 0
            })
        
        # Handle AJAX requests or embedded forms
        if is_embedded:
            # Return JSON response for AJAX requests
            return jsonify(response_data)
        
        # Set flash message with quiz results if applicable
        if form.is_quiz and form.show_score:
            if response.passed:
                flash(f'Congratulations! You passed the quiz with a score of {total_score}/{max_possible_score} ({response_data["score_percentage"]}%).', 'success')
            else:
                flash(f'You scored {total_score}/{max_possible_score} ({response_data["score_percentage"]}%). The passing score is {form.passing_score}%.', 'warning')
        else:
            flash('Thank you! Your response has been recorded.', 'success')
            
        # Return standard page redirect for non-AJAX requests
        return redirect(url_for('form_submitted', form_id=form_id, response_id=response.id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting form: {str(e)}")
        
        # Handle AJAX requests or embedded forms
        is_embedded = request.headers.get('X-Embedded') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_embedded:
            return jsonify({
                'status': 'error',
                'message': f'Error submitting form: {str(e)}'
            }), 400
        
        flash(f'Error submitting form: {str(e)}', 'danger')
        return redirect(url_for('view_form', form_id=form_id))

# Add a success page route
@app.route('/form/<int:form_id>/submitted')
def form_submitted(form_id):
    form = Form.query.get_or_404(form_id)
    
    # If response_id is in the URL, fetch it for displaying quiz results
    response_id = request.args.get('response_id', type=int)
    response = None
    
    if response_id:
        response = Response.query.get(response_id)
    
    return render_template('form_submitted.html', form=form, response=response, now=datetime.now())

@app.route('/form/<int:form_id>/responses')
@login_required
def view_responses(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to view these responses')
        return redirect(url_for('dashboard'))
    
    responses = Response.query.filter_by(form_id=form_id).all()
    return render_template('view_responses.html', form=form, responses=responses)

@app.route('/form/<int:form_id>/responses/export-json')
@login_required
def export_responses_json(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to export these responses')
        return redirect(url_for('dashboard'))
    
    responses = Response.query.filter_by(form_id=form_id).all()
    
    # Create a list to hold all responses
    all_responses = []
    
    for response in responses:
        # Use the helper function to export each response
        response_data, _ = export_response_to_json(response, form)
        all_responses.append(response_data)
    
    # Create export directory if it doesn't exist
    export_path = os.path.join('exports', 'survey_responses')
    os.makedirs(export_path, exist_ok=True)
    
    # Create filename with form ID and timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"all_responses_form_{form_id}_{timestamp}.json"
    file_path = os.path.join(export_path, filename)
    
    # Write all responses to JSON file
    with open(file_path, 'w') as json_file:
        json.dump(all_responses, json_file, indent=2)
    
    # Return the file as a download
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/form/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to delete this form.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Delete all responses first
    Response.query.filter_by(form_id=form_id).delete()
    
    # Delete all questions
    Question.query.filter_by(form_id=form_id).delete()
    
    # Delete the form
    db.session.delete(form)
    db.session.commit()
    
    flash('Form deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/form/<int:form_id>/share')
@login_required
def share_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to share this form')
        return redirect(url_for('dashboard'))
    
    # Getting the base URL with protocol (http/https)
    if request.headers.get('X-Forwarded-Proto'):
        proto = request.headers.get('X-Forwarded-Proto')
    else:
        proto = 'https' if request.is_secure else 'http'
    
    host = request.host
    base_url = f"{proto}://{host}"
    
    # Use pepper-ads.com domain for production
    production_url = "http://pepper-ads.com"
    
    # Create the base share URL with form and user parameters
    base_share_url = f"{production_url}/?form_id={form.id}&user_id={form.user_id}"
    
    # Generate postback URL for this form
    postback_url = generate_postback_url(form.id, form.user_id)
    
    # Detect current device type from request
    current_device = detect_device_type(request.user_agent.string)
    
    # Create additional share URLs with UTM parameters for different platforms
    # Now including device parameter
    share_urls = {
        'default': f"{base_share_url}&utm_source=default&utm_medium=referral&utm_campaign=form_share&device={current_device}",
        'facebook': f"{base_share_url}&utm_source=facebook&utm_medium=social&utm_campaign=form_share&device={current_device}",
        'twitter': f"{base_share_url}&utm_source=twitter&utm_medium=social&utm_campaign=form_share&device={current_device}",
        'linkedin': f"{base_share_url}&utm_source=linkedin&utm_medium=social&utm_campaign=april_launch&device={current_device}",
        'email': f"{base_share_url}&utm_source=email&utm_medium=email&utm_campaign=form_share&device={current_device}"
    }
    
    # You can also create a generic UTM share URL if needed
    utm_share_url = f"{base_share_url}&utm_source=other&utm_medium=referral&utm_campaign=form_share&device={current_device}"
    
    # Create embed URLs for iframes
    embed_url = f"{base_url}/form/{form.id}/embed"
    
    # Generate iframe HTML code
    iframe_code = f'<iframe src="{embed_url}" width="100%" height="600" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>'
    
    return render_template('share_form.html', form=form, 
                          base_url=base_url,
                          production_url=production_url,
                          share_url=f"{base_share_url}&device={current_device}", 
                          share_urls=share_urls,
                          utm_share_url=utm_share_url,
                          current_device=current_device,
                          postback_url=postback_url,
                          embed_url=embed_url,
                          iframe_code=iframe_code)  # Add embed URL and iframe code to template

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
        # Update privacy consent requirement if provided
        if 'requires_consent' in data:
            form.requires_consent = data['requires_consent']
        
        # Update quiz settings if provided
        if 'is_quiz' in data:
            form.is_quiz = data['is_quiz']
        if 'passing_score' in data:
            form.passing_score = int(data['passing_score'])
        if 'show_score' in data:
            form.show_score = data['show_score']
        
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
                order=idx,
                # Add quiz-related fields
                is_quiz_question=q_data.get('is_quiz_question', False),
                correct_answer=q_data.get('correct_answer', None),
                points=q_data.get('points', 0),
                feedback=q_data.get('feedback', None)
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

@app.route('/postback/dashboard')
@login_required
def postback_dashboard():
    # Get all forms for this user
    forms = Form.query.filter_by(user_id=current_user.id).all()
    
    # Get tracking IDs for these forms
    form_ids = [form.id for form in forms]
    trackings = PostbackTracking.query.filter(PostbackTracking.form_id.in_(form_ids)).all()
    
    # Get tracking IDs
    tracking_ids = [t.tracking_id for t in trackings]
    
    # Get logs for these tracking IDs
    logs = PostbackLog.query.filter(PostbackLog.tracking_id.in_(tracking_ids)).order_by(PostbackLog.timestamp.desc()).limit(100).all()
    
    # Group by form
    form_postbacks = {}
    for form in forms:
        form_tracking = next((t for t in trackings if t.form_id == form.id), None)
        if form_tracking:
            form_logs = [log for log in logs if log.tracking_id == form_tracking.tracking_id]
            postback_url = f"http://pepper-ads.com/postback?tracking_id={form_tracking.tracking_id}&user_id={form.user_id}"
            
            form_postbacks[form.id] = {
                'form': form,
                'tracking': form_tracking,
                'logs': form_logs,
                'postback_url': postback_url
            }
    
    return render_template('postback_dashboard.html', form_postbacks=form_postbacks)

@app.route('/postback', methods=['GET', 'POST'])
def receive_postback():
    # Get parameters from either GET or POST
    if request.method == 'GET':
        params = request.args.to_dict()
    else:
        params = request.form.to_dict()
    
    # Extract key parameters
    tracking_id = params.get('tracking_id')
    transaction_id = params.get('transaction_id')
    username = params.get('username')
    user_id = params.get('user_id')
    status = params.get('status')
    payout = params.get('payout')
    
    if not tracking_id:
        return jsonify({'status': 'error', 'message': 'Missing tracking_id'}), 400
    
    # Try to convert payout to float if present
    if payout:
        try:
            payout = float(payout)
        except ValueError:
            payout = None
    
    # Find the tracking record
    tracking = PostbackTracking.query.filter_by(tracking_id=tracking_id).first()
    
    if tracking:
        # Increment transaction count
        tracking.transaction_count += 1
        tracking.last_updated = datetime.utcnow()
        
        # Create log entry
        log = PostbackLog(
            tracking_id=tracking_id,
            transaction_id=transaction_id,
            username=username,
            user_id=user_id,
            status=status,
            payout=payout,
            response_json=json.dumps(params),
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        # Save to JSON file
        save_postback_to_json({
            'tracking_id': tracking_id,
            'transaction_id': transaction_id,
            'username': username,
            'user_id': user_id,
            'status': status,
            'payout': payout,
            'all_params': params,
            'ip_address': request.remote_addr
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Postback received',
            'tracking_id': tracking_id
        })
    else:
        return jsonify({'status': 'error', 'message': 'Invalid tracking_id'}), 404

@app.route('/form/<int:form_id>/embed')
def embed_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    # Get all questions and their subquestions
    questions = Question.query.filter_by(form_id=form_id).order_by(Question.order).all()
    subquestions = {}
    for question in questions:
        subquestions[question.id] = SubQuestion.query.filter_by(question_id=question.id).order_by(SubQuestion.order).all()
        
        # For each subquestion, get its nested subquestions
        for subquestion in subquestions[question.id]:
            try:
                subquestion.nested_options = json.loads(subquestion.options) if subquestion.options else []
            except Exception:
                # Last resort fallback
                subquestion.nested_options = []

    # Sort questions by order
    form.questions.sort(key=lambda q: q.order)
    
    # Check if this is an embedded view (like Google Forms' embedded=true parameter)
    is_embedded = request.args.get('embedded') == 'true'
    
    # Use the dedicated embed template instead of view_form.html
    return render_template('embed_form.html', form=form, subquestions=subquestions, 
                          is_embedded=is_embedded, is_closed=form.is_closed)

@app.route('/form/<int:form_id>/share')
@login_required
def share_form(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to share this form')
        return redirect(url_for('dashboard'))
    
    # Getting the base URL with protocol (http/https)
    if request.headers.get('X-Forwarded-Proto'):
        proto = request.headers.get('X-Forwarded-Proto')
    else:
        proto = 'https' if request.is_secure else 'http'
    
    host = request.host
    base_url = f"{proto}://{host}"
    
    # Use pepper-ads.com domain for production
    production_url = "http://pepper-ads.com"
    
    # Create the base share URL with form and user parameters
    base_share_url = f"{production_url}/?form_id={form.id}&user_id={form.user_id}"
    
    # Generate postback URL for this form
    postback_url = generate_postback_url(form.id, form.user_id)
    
    # Detect current device type from request
    current_device = detect_device_type(request.user_agent.string)
    
    # Create additional share URLs with UTM parameters for different platforms
    # Now including device parameter
    share_urls = {
        'default': f"{base_share_url}&utm_source=default&utm_medium=referral&utm_campaign=form_share&device={current_device}",
        'facebook': f"{base_share_url}&utm_source=facebook&utm_medium=social&utm_campaign=form_share&device={current_device}",
        'twitter': f"{base_share_url}&utm_source=twitter&utm_medium=social&utm_campaign=form_share&device={current_device}",
        'linkedin': f"{base_share_url}&utm_source=linkedin&utm_medium=social&utm_campaign=april_launch&device={current_device}",
        'email': f"{base_share_url}&utm_source=email&utm_medium=email&utm_campaign=form_share&device={current_device}"
    }
    
    # You can also create a generic UTM share URL if needed
    utm_share_url = f"{base_share_url}&utm_source=other&utm_medium=referral&utm_campaign=form_share&device={current_device}"
    
    # Create embed URLs for iframes
    embed_url = f"{base_url}/form/{form.id}/embed"
    
    # Generate iframe HTML code
    iframe_code = f'<iframe src="{embed_url}" width="100%" height="600" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>'
    
    return render_template('share_form.html', form=form, 
                          base_url=base_url,
                          production_url=production_url,
                          share_url=f"{base_share_url}&device={current_device}", 
                          share_urls=share_urls,
                          utm_share_url=utm_share_url,
                          current_device=current_device,
                          postback_url=postback_url,
                          embed_url=embed_url,
                          iframe_code=iframe_code)  # Add embed URL and iframe code to template

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
            
            # Create the form
            form = Form(
                title=form_data["title"] or "Form from Mindmap",
                description="Generated from mindmap",
                user_id=current_user.id,
                company_id=session.get('referral_company_id')
            )
            db.session.add(form)
            db.session.commit()
            
            # Add questions from sections
            question_order = 0
            for section in form_data["sections"]:
                # Add section header as a text field
                if section["name"]:
                    question = Question(
                        form_id=form.id,
                        question_text=f"## {section['name']} ##",
                        question_type="text",
                        required=False,
                        order=question_order
                    )
                    db.session.add(question)
                    question_order += 1
                
                # Add fields from this section
                for field in section["fields"]:
                    question = Question(
                        form_id=form.id,
                        question_text=field["label"],
                        question_type=field["type"],
                        required=False,
                        order=question_order
                    )
                    if field["options"]:
                        question.set_options(field["options"])
                    db.session.add(question)
                    question_order += 1
            
            db.session.commit()
            
            # Clear referral from session after form creation
            session.pop('referral_company_id', None)
            
            flash('Form generated successfully from mindmap!')
            return redirect(url_for('edit_form', form_id=form.id))
            
        except Exception as e:
            flash(f'Error processing mindmap: {str(e)}')
            return redirect(request.url)
    
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

def initialize_templates():
    """Initialize some default templates if none exist"""
    if FormTemplate.query.count() == 0:
        print("Creating predefined templates...")
        default_templates = [
            {
                'title': 'Contact Information',
                'description': 'Collect contact information from your customers or clients',
                'category': 'contact',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/10erh7nUxj1plOplVrZuDLCTQn0VYdVrFiWMsImLrDE0_400.png',
                'questions': [
                    {
                        'question_text': 'Full Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Email',
                        'question_type': 'email',
                        'required': True
                    },
                    {
                        'question_text': 'Phone Number',
                        'question_type': 'tel',
                        'required': False
                    },
                    {
                        'question_text': 'Address',
                        'question_type': 'text',
                        'required': False
                    },
                    {
                        'question_text': 'How would you prefer to be contacted?',
                        'question_type': 'radio',
                        'options': ['Email', 'Phone', 'Text Message'],
                        'required': True
                    }
                ]
            },
            {
                'title': 'Event Registration',
                'description': 'Register attendees for your upcoming event',
                'category': 'event',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/1XykI9graIiCpCfrL-tDY7hBfNRoamwF_K3NpmJugW10_400.png',
                'questions': [
                    {
                        'question_text': 'Full Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Email Address',
                        'question_type': 'email',
                        'required': True
                    },
                    {
                        'question_text': 'Phone Number',
                        'question_type': 'tel',
                        'required': True
                    },
                    {
                        'question_text': 'Which sessions will you attend?',
                        'question_type': 'checkbox',
                        'options': ['Morning Workshop', 'Afternoon Panel', 'Evening Networking', 'All Sessions'],
                        'required': True
                    },
                    {
                        'question_text': 'Dietary Restrictions',
                        'question_type': 'checkbox',
                        'options': ['Vegetarian', 'Vegan', 'Gluten-Free', 'Nut Allergy', 'None'],
                        'required': False
                    }
                ]
            },
            {
                'title': 'Customer Feedback',
                'description': 'Collect feedback about your products or services',
                'category': 'feedback',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/10Z7d4HPigN_VUiFf7tsP5x6DO-NmZ1CTkHEECH9JrE4_400.png',
                'questions': [
                    {
                        'question_text': 'How satisfied are you with our service?',
                        'question_type': 'radio',
                        'options': ['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied', 'Very Dissatisfied'],
                        'required': True
                    },
                    {
                        'question_text': 'What aspects did you like most?',
                        'question_type': 'checkbox',
                        'options': ['Customer Support', 'Product Quality', 'Pricing', 'User Experience', 'Delivery Speed'],
                        'required': True
                    },
                    {
                        'question_text': 'How likely are you to recommend us to others?',
                        'question_type': 'radio',
                        'options': ['Very Likely', 'Likely', 'Neutral', 'Unlikely', 'Very Unlikely'],
                        'required': True
                    },
                    {
                        'question_text': 'Additional comments or suggestions',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            },
            {
                'title': 'Job Application',
                'description': 'Collect information from job applicants',
                'category': 'application',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/1dnc-XoL33BwJgNZMLUZ5_Hj3F1z_AEYeNTcIWRR-QPI_400.png',
                'questions': [
                    {
                        'question_text': 'Full Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Email Address',
                        'question_type': 'email',
                        'required': True
                    },
                    {
                        'question_text': 'Phone Number',
                        'question_type': 'tel',
                        'required': True
                    },
                    {
                        'question_text': 'Position Applying For',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Years of Experience',
                        'question_type': 'radio',
                        'options': ['0-1 years', '1-3 years', '3-5 years', '5+ years'],
                        'required': True
                    },
                    {
                        'question_text': 'Resume/CV',
                        'question_type': 'file',
                        'required': True
                    },
                    {
                        'question_text': 'Cover Letter',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            },
            {
                'title': 'Product Order Form',
                'description': 'Accept orders for your products',
                'category': 'order',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/1XwQvBuou2HL_IGy4Nx-rFnGRk_iJ7JiRs5Y8EwNKbkI_400.png',
                'questions': [
                    {
                        'question_text': 'Customer Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Email Address',
                        'question_type': 'email',
                        'required': True
                    },
                    {
                        'question_text': 'Shipping Address',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Product Selection',
                        'question_type': 'radio',
                        'options': ['Product A - $19.99', 'Product B - $29.99', 'Product C - $39.99', 'Bundle Pack - $79.99'],
                        'required': True
                    },
                    {
                        'question_text': 'Quantity',
                        'question_type': 'number',
                        'required': True
                    },
                    {
                        'question_text': 'Payment Method',
                        'question_type': 'radio',
                        'options': ['Credit Card', 'PayPal', 'Bank Transfer'],
                        'required': True
                    }
                ]
            },
            {
                'title': 'RSVP Form',
                'description': 'Collect RSVPs for your event',
                'category': 'event',
                'preview_image': 'https://ssl.gstatic.com/docs/templates/thumbnails/1uiBg3yjY-S8_LHPLNcPE4pU17YvBM-tSrfKQgXIAQ5A_400.png',
                'questions': [
                    {
                        'question_text': 'Your Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Email Address',
                        'question_type': 'email',
                        'required': True
                    },
                    {
                        'question_text': 'Will you attend?',
                        'question_type': 'radio',
                        'options': ['Yes', 'No', 'Maybe'],
                        'required': True
                    },
                    {
                        'question_text': 'Number of Guests',
                        'question_type': 'number',
                        'required': True
                    },
                    {
                        'question_text': 'Any dietary restrictions?',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            }
        ]

        for template_data in default_templates:
            # Create a copy for database storage
            template_questions = []
            
            # Process each question to ensure options are properly formatted as JSON strings
            for question in template_data['questions']:
                question_copy = question.copy()  # Make a copy to avoid modifying original
                
                # Convert options list to JSON string if it exists
                if 'options' in question_copy and isinstance(question_copy['options'], list):
                    question_copy['options'] = json.dumps(question_copy['options'])
                
                template_questions.append(question_copy)
            
            # Create template
            template = FormTemplate(
                title=template_data['title'],
                description=template_data['description'],
                category=template_data['category'],
                preview_image=template_data['preview_image'],
                is_public=True
            )
            
            # Store questions with JSON string options
            template.questions = json.dumps(template_questions)
            
            # Create template_data structure with questions (keeping options as lists) and empty subquestions
            complete_data = {
                'questions': template_data['questions'],  # Original questions with options as lists
                'subquestions': []
            }
            
            # Store the complete template data
            template.template_data = json.dumps(complete_data)
            
            db.session.add(template)
        
        db.session.commit()
        print("Created predefined templates successfully!")

@app.route('/templates')
def template_gallery():
    categories = db.session.query(FormTemplate.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    selected_category = request.args.get('category')
    search_query = request.args.get('search', '')
    
    query = FormTemplate.query.filter_by(is_public=True)
    
    if selected_category:
        query = query.filter_by(category=selected_category)
    
    if search_query:
        query = query.filter(
            (FormTemplate.title.ilike(f'%{search_query}%')) |
            (FormTemplate.description.ilike(f'%{search_query}%'))
        )
    
    templates = query.order_by(FormTemplate.created_at.desc()).all()
    return render_template('template_gallery.html', 
                         templates=templates,
                         categories=categories,
                         selected_category=selected_category,
                         search_query=search_query)

@app.route('/template/<int:template_id>')
def view_template(template_id):
    template = FormTemplate.query.get_or_404(template_id)
    if not template.is_public and (not current_user.is_authenticated or template.user_id != current_user.id):
        flash('You do not have permission to view this template.', 'danger')
        return redirect(url_for('template_gallery'))
    
    return render_template('view_template.html', template=template)

@app.route('/template/<int:template_id>/use')
@login_required
def use_template(template_id):
    try:
        # Get the template
        template = FormTemplate.query.get_or_404(template_id)
        
        # Create a new form based on the template
        new_form = Form(
            title=template.title,
            description=template.description or "",
            user_id=current_user.id
        )
        db.session.add(new_form)
        db.session.flush()  # Get ID without committing
        
        # Get template data - with backwards compatibility
        template_data_str = template.get_template_data()
        template_data = json.loads(template_data_str)
        
        # If no template data structure, convert from old questions format
        if not template_data or 'questions' not in template_data:
            template_data = {
                'questions': template.get_questions(),
                'subquestions': []
            }
        
        # Create a mapping of original question IDs to new question IDs
        id_mapping = {}
        
        # Process questions first
        for q_idx, q_data in enumerate(template_data.get('questions', [])):
            # Convert options to JSON if it's a list
            options_data = q_data.get('options')
            if isinstance(options_data, list):
                options_json = json.dumps(options_data)
            else:
                options_json = options_data
            
            # Create new question
            new_question = Question(
                form_id=new_form.id,
                question_text=q_data.get('question_text', ''),
                question_type=q_data.get('question_type', 'text'),
                required=q_data.get('required', False),
                order=q_idx,
                options=options_json
            )
            db.session.add(new_question)
            db.session.flush()  # Get ID without committing
            
            # Store mapping of template question ID to new question ID
            original_id = q_data.get('id')
            if original_id:
                id_mapping[original_id] = new_question.id
        
        # Process subquestions if present in the template
        if 'subquestions' in template_data:
            for subq_data in template_data.get('subquestions', []):
                # Get the parent question ID from the mapping
                parent_id = id_mapping.get(subq_data.get('question_id'))
                if parent_id:
                    # Convert options to JSON if it's a list
                    sub_options_data = subq_data.get('options')
                    if isinstance(sub_options_data, list):
                        sub_options_json = json.dumps(sub_options_data)
                    else:
                        sub_options_json = sub_options_data
                    
                    new_subq = SubQuestion(
                        question_id=parent_id,
                        parent_option=subq_data.get('parent_option', ''),
                        question_text=subq_data.get('question_text', ''),
                        question_type=subq_data.get('question_type', 'text'),
                        required=subq_data.get('required', False),
                        order=subq_data.get('order', 0),
                        nesting_level=subq_data.get('nesting_level', 1),
                        options=sub_options_json
                    )
                    db.session.add(new_subq)
        
        # Commit the transaction
        db.session.commit()
        
        flash("Form created from template successfully!", "success")
        return redirect(url_for('edit_form', form_id=new_form.id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating form from template: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/template/upload', methods=['GET', 'POST'])
@login_required
def upload_template():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        questions = request.form.get('questions')
        is_public = request.form.get('is_public') == 'on'
        
        try:
            questions_data = json.loads(questions)
        except:
            flash('Invalid questions data', 'danger')
            return redirect(url_for('upload_template'))
        
        template = FormTemplate(
            title=title,
            description=description,
            category=category,
            is_public=is_public,
            user_id=current_user.id
        )
        template.set_questions(questions_data)
        
        db.session.add(template)
        db.session.commit()
        
        flash('Template uploaded successfully!', 'success')
        return redirect(url_for('template_gallery'))
    
    return render_template('upload_template.html')

@app.route('/form/<int:form_id>/embed-demo')
@login_required
def form_embed_demo(form_id):
    """Demo page showing how to embed forms and handle form submission events"""
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to access this form')
        return redirect(url_for('dashboard'))
    
    # Create embed URL
    if request.headers.get('X-Forwarded-Proto'):
        proto = request.headers.get('X-Forwarded-Proto')
    else:
        proto = 'https' if request.is_secure else 'http'
    
    host = request.host
    base_url = f"{proto}://{host}"
    
    # Generate embed URL and iframe code
    embed_url = f"{base_url}/form/{form.id}/embed"
    iframe_code = f'<iframe src="{embed_url}" width="100%" height="600" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>'
    
    return render_template('form_embed_demo.html', 
                          form=form, 
                          embed_url=embed_url,
                          iframe_code=iframe_code)

@app.route('/form/<int:form_id>/toggle-status', methods=['POST'])
@login_required
def toggle_form_status(form_id):
    form = Form.query.get_or_404(form_id)
    if form.user_id != current_user.id:
        flash('You do not have permission to modify this form', 'danger')
        return redirect(url_for('dashboard'))
        
    # Toggle the is_closed status
    form.is_closed = not form.is_closed
    db.session.commit()
    
    status = "closed" if form.is_closed else "reopened"
    flash(f'Form has been {status} successfully', 'success')
    
    # Check if the request is from AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'success',
            'is_closed': form.is_closed,
            'message': f'Form has been {status} successfully'
        })
    
    # Redirect to the appropriate page based on referrer
    referrer = request.referrer
    if referrer and '/edit' in referrer:
        return redirect(url_for('edit_form', form_id=form_id))
    elif referrer and '/responses' in referrer:
        return redirect(url_for('view_responses', form_id=form_id))
    else:
        return redirect(url_for('dashboard'))

@app.route('/privacy-policy')
def privacy_policy():
    """Route for viewing the privacy policy"""
    return render_template('privacy_policy.html', now=datetime.now())

@app.route('/terms-and-conditions')
def terms_and_conditions():
    """Route for viewing the terms and conditions"""
    return render_template('terms_and_conditions.html', now=datetime.now())

@app.route('/form/<int:form_id>/privacy-policy')
def form_privacy_policy(form_id):
    """Route for viewing a specific form's privacy policy"""
    form = Form.query.get_or_404(form_id)
    return render_template('privacy_policy.html', form=form, now=datetime.now())

@app.route('/form/<int:form_id>/terms-and-conditions')
def form_terms_and_conditions(form_id):
    """Route for viewing a specific form's terms and conditions"""
    form = Form.query.get_or_404(form_id)
    return render_template('terms_and_conditions.html', form=form, now=datetime.now())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Clear all existing templates and recreate
        FormTemplate.query.delete()
        db.session.commit()
        initialize_templates()  # Add this line to initialize templates
    app.run(debug=True)