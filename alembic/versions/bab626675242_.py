"""empty message

Revision ID: bab626675242
Revises: 64b9c895476f
Create Date: 2025-03-14 09:52:51.377305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bab626675242'
down_revision: Union[str, None] = '64b9c895476f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass



def downgrade() -> None:
    pass
