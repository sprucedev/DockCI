"""git_branch

Revision ID: 1c398722878
Revises: 224302e491d
Create Date: 2015-10-18 00:38:22.737519

"""

# revision identifiers, used by Alembic.
revision = '1c398722878'
down_revision = '224302e491d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('job', sa.Column('git_branch', sa.Text(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('job', 'git_branch')
    ### end Alembic commands ###
