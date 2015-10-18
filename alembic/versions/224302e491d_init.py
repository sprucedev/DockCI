"""init

Revision ID: 224302e491d
Revises: 
Create Date: 2015-10-18 11:33:26.875668

"""

# revision identifiers, used by Alembic.
revision = '224302e491d'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('role',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('password', sa.String(length=255), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_table('o_auth_token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service', sa.String(length=31), nullable=True),
    sa.Column('key', sa.String(length=80), nullable=True),
    sa.Column('secret', sa.String(length=80), nullable=True),
    sa.Column('scope', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_o_auth_token_user_id'), 'o_auth_token', ['user_id'], unique=False)
    op.create_table('roles_users',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_index(op.f('ix_roles_users_user_id'), 'roles_users', ['user_id'], unique=False)
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('repo', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('utility', sa.Boolean(), nullable=False),
    sa.Column('hipchat_api_token', sa.String(length=255), nullable=True),
    sa.Column('hipchat_room', sa.String(length=255), nullable=True),
    sa.Column('github_repo_id', sa.String(length=255), nullable=True),
    sa.Column('github_hook_id', sa.Integer(), nullable=True),
    sa.Column('github_secret', sa.String(length=255), nullable=True),
    sa.Column('github_auth_token_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['github_auth_token_id'], ['o_auth_token.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_slug'), 'project', ['slug'], unique=True)
    op.create_index(op.f('ix_project_utility'), 'project', ['utility'], unique=False)
    op.create_table('job',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('create_ts', sa.DateTime(), nullable=False),
    sa.Column('start_ts', sa.DateTime(), nullable=True),
    sa.Column('complete_ts', sa.DateTime(), nullable=True),
    sa.Column('result', sa.Enum('success', 'fail', 'broken', name='job_results'), nullable=True),
    sa.Column('repo', sa.Text(), nullable=False),
    sa.Column('commit', sa.String(length=41), nullable=False),
    sa.Column('tag', sa.Text(), nullable=True),
    sa.Column('image_id', sa.String(length=65), nullable=True),
    sa.Column('container_id', sa.String(length=65), nullable=True),
    sa.Column('exit_code', sa.Integer(), nullable=True),
    sa.Column('docker_client_host', sa.Text(), nullable=True),
    sa.Column('git_author_name', sa.Text(), nullable=True),
    sa.Column('git_author_email', sa.Text(), nullable=True),
    sa.Column('git_committer_name', sa.Text(), nullable=True),
    sa.Column('git_committer_email', sa.Text(), nullable=True),
    sa.Column('git_changes', sa.Text(), nullable=True),
    sa.Column('ancestor_job_id', sa.Integer(), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['ancestor_job_id'], ['job.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_project_id'), 'job', ['project_id'], unique=False)
    op.create_index(op.f('ix_job_result'), 'job', ['result'], unique=False)
    op.create_table('job_stage_tmp',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=31), nullable=True),
    sa.Column('job_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['job.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_stage_tmp_job_id'), 'job_stage_tmp', ['job_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_job_stage_tmp_job_id'), table_name='job_stage_tmp')
    op.drop_table('job_stage_tmp')
    op.drop_index(op.f('ix_job_result'), table_name='job')
    op.drop_index(op.f('ix_job_project_id'), table_name='job')
    op.drop_table('job')
    op.drop_index(op.f('ix_project_utility'), table_name='project')
    op.drop_index(op.f('ix_project_slug'), table_name='project')
    op.drop_table('project')
    op.drop_index(op.f('ix_roles_users_user_id'), table_name='roles_users')
    op.drop_table('roles_users')
    op.drop_index(op.f('ix_o_auth_token_user_id'), table_name='o_auth_token')
    op.drop_table('o_auth_token')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_table('role')
    ### end Alembic commands ###