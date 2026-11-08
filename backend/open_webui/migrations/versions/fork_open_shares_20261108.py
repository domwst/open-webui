"""Preserve anonymous links from this fork using upstream's explicit open grant.

Revision ID: fork_open_shares_20261108
Revises: 9f6c2a8d1b43
"""

from alembic import op
import sqlalchemy as sa

revision = 'fork_open_shares_20261108'
down_revision = '9f6c2a8d1b43'
branch_labels = None
depends_on = None

grants = sa.table(
    'access_grant',
    sa.column('id', sa.Text),
    sa.column('resource_type', sa.Text),
    sa.column('resource_id', sa.Text),
    sa.column('principal_type', sa.Text),
    sa.column('principal_id', sa.Text),
    sa.column('permission', sa.Text),
)


def convert(source, target):
    conn = op.get_bind()
    # The old fork exposed only shared-chat user:*:read grants anonymously.
    # Private links, named-user grants and all other resources stay unchanged.
    rows = conn.execute(sa.select(grants.c.id, grants.c.resource_id).where(
        grants.c.resource_type == 'shared_chat',
        grants.c.principal_type == source,
        grants.c.principal_id == '*',
        grants.c.permission == 'read',
    )).fetchall()
    for grant_id, resource_id in rows:
        existing = conn.execute(sa.select(grants.c.id).where(
            grants.c.resource_type == 'shared_chat',
            grants.c.resource_id == resource_id,
            grants.c.principal_type == target,
            grants.c.principal_id == '*',
            grants.c.permission == 'read',
        )).first()
        if existing:
            conn.execute(grants.delete().where(grants.c.id == grant_id))
        else:
            conn.execute(grants.update().where(grants.c.id == grant_id).values(principal_type=target))


def upgrade():
    convert('user', 'anyone')


def downgrade():
    convert('anyone', 'user')
