from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, DATETIME
from alembic import autogenerate, context
from unittest import TestCase
from tests import staging_env, sqlite_db, clear_staging_env, eq_, eq_ignore_whitespace

def _model_one():
    m = MetaData()

    Table('user', m,
        Column('id', Integer, primary_key=True),
        Column('name', String(50)),
        Column('a1', Text),
        Column("pw", String(50))
    )

    Table('address', m,
        Column('id', Integer, primary_key=True),
        Column('email_address', String(100), nullable=False),
    )

    Table('order', m,
        Column('order_id', Integer, primary_key=True),
        Column("amount", Numeric(8, 2), nullable=False, 
                server_default="0"),
    )

    Table('extra', m,
        Column("x", CHAR)
    )

    return m

def _model_two():
    m = MetaData()

    Table('user', m,
        Column('id', Integer, primary_key=True),
        Column('name', String(50), nullable=False),
        Column('a1', Text, server_default="x"),
    )

    Table('address', m,
        Column('id', Integer, primary_key=True),
        Column('email_address', String(100), nullable=False),
        Column('street', String(50))
    )

    Table('order', m,
        Column('order_id', Integer, primary_key=True),
        Column("amount", Numeric(10, 2), nullable=True, 
                    server_default="0"),
        Column('user_id', Integer, ForeignKey('user.id')),
    )

    Table('item', m, 
        Column('id', Integer, primary_key=True),
        Column('description', String(100)),
        Column('order_id', Integer, ForeignKey('order.order_id')),
    )
    return m

class AutogenerateDiffTest(TestCase):
    @classmethod
    def setup_class(cls):
        staging_env()
        cls.bind = sqlite_db()
        cls.m1 = _model_one()
        cls.m1.create_all(cls.bind)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = _model_two()
        connection = self.bind.connect()
        diffs = []
        autogenerate._produce_net_changes(connection, metadata, diffs)
        print "\n".join(repr(d) for d in diffs)

        eq_(
            diffs[0],
            ('add_table', metadata.tables['item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], 'remove_column')
        eq_(diffs[2][2].name, 'pw')

        eq_(diffs[3][0][0], "modify_default")
        eq_(diffs[3][0][1], "user")
        eq_(diffs[3][0][2], "a1")
        eq_(diffs[3][0][5].arg, "x")

        eq_(diffs[4][0][0], 'modify_nullable')
        eq_(diffs[4][0][4], True)
        eq_(diffs[4][0][5], False)

        eq_(diffs[5][0], "add_column")
        eq_(diffs[5][1], "order")
        eq_(diffs[5][2], metadata.tables['order'].c.user_id)

        eq_(diffs[6][0][0], "modify_type")
        eq_(diffs[6][0][1], "order")
        eq_(diffs[6][0][2], "amount")
        eq_(repr(diffs[6][0][4]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[6][0][5]), "Numeric(precision=10, scale=2)")

        eq_(diffs[6][1][0], 'modify_nullable')
        eq_(diffs[6][1][4], False)
        eq_(diffs[6][1][5], True)

        eq_(diffs[7][0], "add_column")
        eq_(diffs[7][1], "address")
        eq_(diffs[7][2], metadata.tables['address'].c.street)


    def test_render_diffs(self):
        """test a full render including indentation"""

        # TODO: this test isn't going
        # to be so spectacular on Py3K...

        metadata = _model_two()
        connection = self.bind.connect()
        template_args = {}
        context.configure(
            connection=connection, 
            autogenerate_metadata=metadata)
        autogenerate.produce_migration_diffs(template_args, set())
        eq_(template_args['upgrades'],
"""### commands auto generated by Alembic - please adjust! ###
    create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=100), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint([order_id], ['order.order_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    drop_table(u'extra')
    drop_column('user', u'pw')
    alter_column('user', 'a1', 
               existing_type=sa.TEXT(), 
               server_default='x', 
               existing_nullable=True)
    alter_column('user', 'name', 
               existing_type=sa.VARCHAR(length=50), 
               nullable=False)
    add_column('order', sa.Column('user_id', sa.Integer(), nullable=True))
    alter_column('order', u'amount', 
               existing_type=sa.NUMERIC(precision=8, scale=2), 
               type_=sa.Numeric(precision=10, scale=2), 
               nullable=True, 
               existing_server_default='0')
    add_column('address', sa.Column('street', sa.String(length=50), nullable=True))
    ### end Alembic commands ###""")

        eq_(template_args['downgrades'],
"""### commands auto generated by Alembic - please adjust! ###
    drop_table('item')
    create_table(u'extra',
    sa.Column(u'x', sa.CHAR(), nullable=True),
    sa.PrimaryKeyConstraint()
    )
    add_column('user', sa.Column(u'pw', sa.VARCHAR(length=50), nullable=True))
    alter_column('user', 'a1', 
               existing_type=sa.TEXT(), 
               server_default=None, 
               existing_nullable=True)
    alter_column('user', 'name', 
               existing_type=sa.VARCHAR(length=50), 
               nullable=True)
    drop_column('order', 'user_id')
    alter_column('order', u'amount', 
               existing_type=sa.Numeric(precision=10, scale=2), 
               type_=sa.NUMERIC(precision=8, scale=2), 
               nullable=False, 
               existing_server_default='0')
    drop_column('address', 'street')
    ### end Alembic commands ###""")

class AutogenRenderTest(TestCase):
    """test individual directives"""

    @classmethod
    def setup_class(cls):
        context._context_opts['autogenerate_sqlalchemy_prefix'] = 'sa.'

    def test_render_table_upgrade(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column("address_id", Integer, ForeignKey("address.id")),
            Column("timestamp", DATETIME, server_default="NOW()"),
            Column("amount", Numeric(5, 2)),
        )
        eq_ignore_whitespace(
            autogenerate._add_table(t, set()),
            "create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('address_id', sa.Integer(), nullable=True),"
            "sa.Column('timestamp', sa.DATETIME(), "
                "server_default='NOW()', "
                "nullable=True),"
            "sa.Column('amount', sa.Numeric(precision=5, scale=2), nullable=True),"
            "sa.ForeignKeyConstraint([address_id], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id')"
            ")"
        )

    def test_render_drop_table(self):
        eq_(
            autogenerate._drop_table(Table("sometable", MetaData()), set()),
            "drop_table('sometable')"
        )

    def test_render_add_column(self):
        eq_(
            autogenerate._add_column(
                    "foo", Column("x", Integer, server_default="5"), set()),
            "add_column('foo', sa.Column('x', sa.Integer(), "
                "server_default='5', nullable=True))"
        )

    def test_render_drop_column(self):
        eq_(
            autogenerate._drop_column(
                    "foo", Column("x", Integer, server_default="5"), set()),

            "drop_column('foo', 'x')"
        )

    def test_render_modify_type(self):
        eq_ignore_whitespace(
            autogenerate._modify_col(
                        "sometable", "somecolumn", 
                        set(),
                        type_=CHAR(10), existing_type=CHAR(20)),
            "alter_column('sometable', 'somecolumn', "
                "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10))"
        )

    def test_render_modify_nullable(self):
        eq_ignore_whitespace(
            autogenerate._modify_col(
                        "sometable", "somecolumn", 
                        set(),
                        existing_type=Integer(),
                        nullable=True),
            "alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True)"
        )

    def test_render_modify_nullable_w_default(self):
        eq_ignore_whitespace(
            autogenerate._modify_col(
                        "sometable", "somecolumn", 
                        set(),
                        existing_type=Integer(),
                        existing_server_default="5",
                        nullable=True),
            "alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default='5')"
        )

# TODO: tests for dialect-specific type rendering + imports
