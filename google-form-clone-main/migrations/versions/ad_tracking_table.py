"""Add AdTracking model

Revision ID: ad_tracking_table
Revises: 
Create Date: 2023-05-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ad_tracking_table'
down_revision = None  # Change this to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create the ad_tracking table
    op.create_table('ad_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('campaign_id', sa.String(length=100), nullable=True),
        sa.Column('click_id', sa.String(length=100), nullable=True),
        sa.Column('conversion_id', sa.String(length=100), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('form_id', sa.Integer(), nullable=True),
        sa.Column('response_id', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ),
        sa.ForeignKeyConstraint(['response_id'], ['form_responses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop the ad_tracking table
    op.drop_table('ad_tracking') 