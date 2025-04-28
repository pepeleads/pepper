from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AdTracking(db.Model):
    """Model for storing S2S tracking data from ad networks like pepper-ads.com"""
    
    __tablename__ = 'ad_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)  # e.g., 'pepper-ads'
    campaign_id = db.Column(db.String(100))
    click_id = db.Column(db.String(100))
    conversion_id = db.Column(db.String(100))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')
    
    # Optional relationship to form response if applicable
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=True)
    response_id = db.Column(db.Integer, db.ForeignKey('form_responses.id'), nullable=True)
    
    # Store the complete raw data as JSON
    raw_data = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    form = db.relationship('Form', backref=db.backref('ad_tracking', lazy=True), foreign_keys=[form_id])
    response = db.relationship('FormResponse', backref=db.backref('ad_tracking', lazy=True), foreign_keys=[response_id])
    
    def __repr__(self):
        return f'<AdTracking {self.id} - {self.source} - {self.click_id}>' 