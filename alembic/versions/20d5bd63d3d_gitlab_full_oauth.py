"""GitLab full OAuth

Revision ID: 20d5bd63d3d
Revises: 104ef30bb0
Create Date: 2015-11-07 11:29:00.109240

"""

# revision identifiers, used by Alembic.
revision = '20d5bd63d3d'
down_revision = '104ef30bb0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(table_name='project', column_name='github_auth_token_id', new_column_name='external_auth_token_id')
    op.drop_column('project', 'gitlab_base_uri')
    op.drop_column('project', 'gitlab_private_token')


def downgrade():
    op.alter_column(table_name='project', column_name='external_auth_token_id', new_column_name='github_auth_token_id')
    op.add_column('project', sa.Column('gitlab_private_token', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('project', sa.Column('gitlab_base_uri', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
