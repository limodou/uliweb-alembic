from os import path

__version__ = '0.3.5'

package_dir = path.abspath(path.dirname(__file__))


from alembic import op
from alembic import context

