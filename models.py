class PredefinedTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    preview_image = db.Column(db.String(500))
    form_structure = db.Column(db.JSON)  # Stores the form structure
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_predefined = db.Column(db.Boolean, default=True)  # Flag to identify predefined templates

    def __repr__(self):
        return f'<PredefinedTemplate {self.title}>' 