"""Job.repo_fs

Revision ID: 5773ec3bc06
Revises: 3ce0ed6fff6
Create Date: 2015-12-01 02:03:19.042318

"""

# revision identifiers, used by Alembic.
revision = '5773ec3bc06'
down_revision = '3ce0ed6fff6'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.alter_column('job', 'repo', new_column_name='repo_fs')


def downgrade():
    op.alter_column('job', 'repo_fs', new_column_name='repo')
