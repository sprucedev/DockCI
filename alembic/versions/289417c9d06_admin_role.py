"""admin role

Revision ID: 289417c9d06
Revises: 448338b03a3
Create Date: 2016-06-01 02:15:28.241077

"""

# revision identifiers, used by Alembic.
revision = '289417c9d06'
down_revision = '448338b03a3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    INSERT INTO role (name, description)
    VALUES ('admin', 'Administrators')
    """)
    op.execute("""
    INSERT INTO roles_users (user_id, role_id)
    SELECT u.id, r.id
    FROM "user" u, role r
    """)


def downgrade():
    op.execute("""
    DELETE FROM roles_users WHERE role_id IN (
        SELECT id FROM role WHERE name = 'admin'
    )
    """)
    op.execute("""
    DELETE FROM role WHERE name = 'admin'
    """)
