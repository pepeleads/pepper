from app import app, db, FormTemplate
import json

def add_google_style_templates():
    with app.app_context():
        # Clear existing templates (optional)
        # FormTemplate.query.delete()
        # db.session.commit()
        
        # Create data URI patterns for template preview images
        image_patterns = {
            'contact': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNFOEYwRkUiLz48Y2lyY2xlIGN4PSIxMDAiIGN5PSI2MCIgcj0iMzAiIGZpbGw9IiM0Mjg1RjQiLz48cmVjdCB4PSI1MCIgeT0iMTAwIiB3aWR0aD0iMTAwIiBoZWlnaHQ9IjMwIiByeD0iNCIgZmlsbD0iIzQyODVGNCIvPjx0ZXh0IHg9IjEwMCIgeT0iMTIwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjE0Ij5Db250YWN0PC90ZXh0Pjwvc3ZnPg==',
            
            'event': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNGQ0U4RTYiLz48cmVjdCB4PSI2MCIgeT0iMzAiIHdpZHRoPSI4MCIgaGVpZ2h0PSI4MCIgcng9IjQiIGZpbGw9IiNFQTQzMzUiLz48dGV4dCB4PSIxMDAiIHk9IjcwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjE0Ij5FdmVudDwvdGV4dD48cmVjdCB4PSI1MCIgeT0iMTEwIiB3aWR0aD0iMTAwIiBoZWlnaHQ9IjIwIiByeD0iNCIgZmlsbD0iI0VBNDMzNSIvPjwvc3ZnPg==',
            
            'feedback': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNGRkYwRTAiLz48Y2lyY2xlIGN4PSI2MCIgY3k9IjYwIiByPSIyMCIgZmlsbD0iI0ZCQkMwNSIvPjxjaXJjbGUgY3g9IjE0MCIgY3k9IjYwIiByPSIyMCIgZmlsbD0iI0ZCQkMwNSIvPjxwYXRoIGQ9Ik02MCwxMTAgQzYwLDExMCAxMDAsMTMwIDE0MCwxMTAiIHN0cm9rZT0iI0ZCQkMwNSIgc3Ryb2tlLXdpZHRoPSI4IiBmaWxsPSJub25lIi8+PC9zdmc+',
            
            'rsvp': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNFNkY0RUEiLz48cmVjdCB4PSI1MCIgeT0iNDAiIHdpZHRoPSIxMDAiIGhlaWdodD0iNzAiIHJ4PSI0IiBmaWxsPSIjMzRBODUzIi8+PHBhdGggZD0iTTgwLDcwIEwxMDAsOTAgTDEzMCw2MCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI4IiBmaWxsPSJub25lIi8+PHRleHQgeD0iMTAwIiB5PSIxMzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiMzNEE4NTMiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiI+UlNWUDwvdGV4dD48L3N2Zz4=',
            
            'application': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNFOEYwRkUiLz48cmVjdCB4PSI1MCIgeT0iMzAiIHdpZHRoPSIxMDAiIGhlaWdodD0iOTAiIHJ4PSI0IiBmaWxsPSJ3aGl0ZSIgc3Ryb2tlPSIjNDI4NUY0IiBzdHJva2Utd2lkdGg9IjIiLz48cmVjdCB4PSI2MCIgeT0iNTAiIHdpZHRoPSI4MCIgaGVpZ2h0PSI4IiBmaWxsPSIjRTBFMEUwIi8+PHJlY3QgeD0iNjAiIHk9IjcwIiB3aWR0aD0iODAiIGhlaWdodD0iOCIgZmlsbD0iI0UwRTBFMCIvPjxyZWN0IHg9IjYwIiB5PSI5MCIgd2lkdGg9IjgwIiBoZWlnaHQ9IjgiIGZpbGw9IiNFMEUwRTAiLz48L3N2Zz4=',
            
            'education': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNGM0U4RkYiLz48cGF0aCBkPSJNNTAsNzAgTDEwMCw0MCBMMTUwLDcwIEwxMDAsMTAwIFoiIGZpbGw9IiM2NzNBQjciLz48cmVjdCB4PSI3MCIgeT0iMTAwIiB3aWR0aD0iNjAiIGhlaWdodD0iMjAiIGZpbGw9IiM2NzNBQjciLz48cGF0aCBkPSJNMTQwLDcwIEwxNDAsOTUiIHN0cm9rZT0iIzY3M0FCNyIgc3Ryb2tlLXdpZHRoPSI0Ii8+PC9zdmc+',
            
            'order': 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNGRkYzRTAiLz48cmVjdCB4PSI2MCIgeT0iMzAiIHdpZHRoPSI4MCIgaGVpZ2h0PSI2MCIgcng9IjQiIGZpbGw9IiNGOUFCMDAiLz48cmVjdCB4PSI3MCIgeT0iNTAiIHdpZHRoPSI2MCIgaGVpZ2h0PSI4IiBmaWxsPSJ3aGl0ZSIvPjxyZWN0IHg9IjcwIiB5PSI3MCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjgiIGZpbGw9IndoaXRlIi8+PHJlY3QgeD0iNzAiIHk9IjEwMCIgd2lkdGg9IjYwIiBoZWlnaHQ9IjIwIiByeD0iNCIgZmlsbD0iI0Y5QUIwMCIvPjx0ZXh0IHg9IjEwMCIgeT0iMTE1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEyIj5PcmRlcjwvdGV4dD48L3N2Zz4='
        }
        
        # Create Google-style templates
        templates = [
            {
                'title': 'Contact Information',
                'description': 'Collect contact information from your customers',
                'category': 'contact',
                'preview_image': image_patterns['contact'],
                'questions': [
                    {
                        'question_text': 'Name',
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
                    }
                ]
            },
            {
                'title': 'Event Registration',
                'description': 'Register people for your event',
                'category': 'event',
                'preview_image': image_patterns['event'],
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
                        'question_text': 'Will you attend in person?',
                        'question_type': 'radio',
                        'options': ['Yes', 'No', 'Not sure yet'],
                        'required': True
                    },
                    {
                        'question_text': 'Which sessions will you attend?',
                        'question_type': 'checkbox',
                        'options': ['Morning Session', 'Afternoon Workshop', 'Evening Networking'],
                        'required': True
                    }
                ]
            },
            {
                'title': 'Customer Feedback',
                'description': 'Get feedback from your customers',
                'category': 'feedback',
                'preview_image': image_patterns['feedback'],
                'questions': [
                    {
                        'question_text': 'How satisfied are you with our product?',
                        'question_type': 'radio',
                        'options': ['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied', 'Very Dissatisfied'],
                        'required': True
                    },
                    {
                        'question_text': 'What features do you like most?',
                        'question_type': 'checkbox',
                        'options': ['Ease of use', 'Design', 'Speed', 'Customer service', 'Price'],
                        'required': False
                    },
                    {
                        'question_text': 'How likely are you to recommend us?',
                        'question_type': 'radio',
                        'options': ['Very likely', 'Likely', 'Neutral', 'Unlikely', 'Very unlikely'],
                        'required': True
                    },
                    {
                        'question_text': 'Any additional comments?',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            },
            {
                'title': 'RSVP Form',
                'description': 'Collect RSVPs for your event',
                'category': 'event',
                'preview_image': image_patterns['rsvp'],
                'questions': [
                    {
                        'question_text': 'Will you attend?',
                        'question_type': 'radio',
                        'options': ['Yes', 'No', 'Maybe'],
                        'required': True
                    },
                    {
                        'question_text': 'Your Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'How many guests will you bring?',
                        'question_type': 'radio',
                        'options': ['0', '1', '2', '3+'],
                        'required': True
                    },
                    {
                        'question_text': 'Dietary restrictions',
                        'question_type': 'checkbox',
                        'options': ['Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'None'],
                        'required': False
                    }
                ]
            },
            
            {
                'title': 'Job Application Form',
                'description': 'Collect information from job applicants',
                'category': 'application',
                'preview_image': image_patterns['application'],
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
                        'question_text': 'Position Applied For',
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
                        'question_text': 'Skills (select all that apply)',
                        'question_type': 'checkbox',
                        'options': ['Project Management', 'Customer Service', 'Sales', 'Marketing', 'Web Development', 'Design', 'Data Analysis'],
                        'required': True
                    },
                    {
                        'question_text': 'Why are you interested in this position?',
                        'question_type': 'text',
                        'required': True
                    }
                ]
            },
            
            {
                'title': 'Course Evaluation',
                'description': 'Get feedback about your course or training',
                'category': 'education',
                'preview_image': image_patterns['education'],
                'questions': [
                    {
                        'question_text': 'Course Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'Instructor Name',
                        'question_type': 'text',
                        'required': True
                    },
                    {
                        'question_text': 'How would you rate the course content?',
                        'question_type': 'radio',
                        'options': ['Excellent', 'Good', 'Average', 'Below Average', 'Poor'],
                        'required': True
                    },
                    {
                        'question_text': 'How would you rate the instructor?',
                        'question_type': 'radio',
                        'options': ['Excellent', 'Good', 'Average', 'Below Average', 'Poor'],
                        'required': True
                    },
                    {
                        'question_text': 'What aspects of the course were most valuable?',
                        'question_type': 'checkbox',
                        'options': ['Lectures', 'Hands-on exercises', 'Group discussions', 'Course materials', 'Assignments'],
                        'required': False
                    },
                    {
                        'question_text': 'What suggestions do you have for improving the course?',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            },
            
            {
                'title': 'Product Order Form',
                'description': 'Take product orders from customers',
                'category': 'order',
                'preview_image': image_patterns['order'],
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
                        'options': ['Basic Package ($99)', 'Standard Package ($199)', 'Premium Package ($299)', 'Enterprise Package ($499)'],
                        'required': True
                    },
                    {
                        'question_text': 'Add-on Items',
                        'question_type': 'checkbox',
                        'options': ['Extended Warranty (+$49)', 'Express Shipping (+$25)', 'Gift Wrapping (+$10)', 'Priority Support (+$39)'],
                        'required': False
                    },
                    {
                        'question_text': 'Preferred Delivery Date',
                        'question_type': 'date',
                        'required': False
                    },
                    {
                        'question_text': 'Special Instructions',
                        'question_type': 'text',
                        'required': False
                    }
                ]
            }
        ]
        
        for template_data in templates:
            template = FormTemplate(
                title=template_data['title'],
                description=template_data['description'],
                category=template_data['category'],
                preview_image=template_data['preview_image'],
                is_public=True
            )
            template.questions = json.dumps(template_data['questions'])
            db.session.add(template)
        
        db.session.commit()
        print(f"Added {len(templates)} Google-style templates with embedded images successfully!")

if __name__ == "__main__":
    add_google_style_templates() 