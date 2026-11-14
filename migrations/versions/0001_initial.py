"""Initial documents and clauses schema."""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("documents",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("filename",sa.String(255),nullable=False),
        sa.Column("sha256",sa.String(64),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_documents_sha256","documents",["sha256"],unique=True)
    op.create_table("clauses",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("document_id",sa.Integer(),sa.ForeignKey("documents.id",ondelete="CASCADE"),nullable=False),
        sa.Column("clause_id",sa.String(32),nullable=False),
        sa.Column("page",sa.Integer(),nullable=True),
        sa.Column("text",sa.Text(),nullable=False),
        sa.Column("category",sa.String(100),nullable=False),
        sa.Column("risk_level",sa.String(16),nullable=False),
        sa.Column("risk_flags_json",sa.Text(),nullable=False))
    op.create_index("ix_clauses_document_id","clauses",["document_id"])
def downgrade():
    op.drop_index("ix_clauses_document_id",table_name="clauses")
    op.drop_table("clauses")
    op.drop_index("ix_documents_sha256",table_name="documents")
    op.drop_table("documents")
