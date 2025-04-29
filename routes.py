from flask import render_template
from flask_login import login_required, current_user
from app.models import Form, Template, PredefinedTemplate

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's forms
        forms = Form.query.filter_by(user_id=current_user.id).order_by(Form.created_at.desc()).all()
        
        # Get user's templates
        user_templates = Template.query.filter_by(user_id=current_user.id).order_by(Template.created_at.desc()).all()
        
        # Get predefined templates
        predefined_templates = PredefinedTemplate.query.filter_by(is_active=True).order_by(PredefinedTemplate.created_at.desc()).all()
        
        # Combine user templates and predefined templates
        all_templates = list(user_templates) + list(predefined_templates)
        
        # Debug print to check templates
        print(f"User templates: {len(user_templates)}")
        print(f"Predefined templates: {len(predefined_templates)}")
        print(f"Total templates: {len(all_templates)}")
        
        return render_template('dashboard.html', 
                            forms=forms, 
                            templates=all_templates,
                            current_user=current_user)
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        return render_template('dashboard.html', 
                            forms=[], 
                            templates=[],
                            current_user=current_user) 