"""public projects

Revision ID: 4b558aa4806
Revises: 289417c9d06
Create Date: 2016-07-08 18:05:57.498826

"""

# revision identifiers, used by Alembic.
revision = '4b558aa4806'
down_revision = '289417c9d06'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('public', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index(op.f('ix_project_public'), 'project', ['public'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_project_public'), table_name='project')
    op.drop_column('project', 'public')
    ### end Alembic commands ###