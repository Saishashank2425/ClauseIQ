"""Add pgvector storage, tenant ACLs and document versioning."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_pgvector_rbac_versions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Render Postgres and local Postgres must have permission to install pgvector.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.drop_index("ix_documents_sha256", table_name="documents")
    op.add_column("documents", sa.Column("tenant_id", sa.String(128), nullable=True))
    op.add_column("documents", sa.Column("owner_id", sa.String(128), nullable=True))
    op.add_column("documents", sa.Column("version_group_id", sa.String(36), nullable=True))
    op.add_column("documents", sa.Column("version_number", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("is_current", sa.Boolean(), nullable=True))
    op.add_column("documents", sa.Column("supersedes_document_id", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_documents_supersedes", "documents", "documents",
        ["supersedes_document_id"], ["id"], ondelete="SET NULL"
    )

    # Existing records are quarantined into a legacy owner scope; they are not
    # exposed to newly authenticated users by the authorization query.
    op.execute("""
        UPDATE documents
        SET tenant_id = 'legacy',
            owner_id = 'legacy',
            version_group_id = 'legacy-' || id::text,
            version_number = 1,
            is_current = TRUE
    """)
    op.alter_column("documents", "tenant_id", nullable=False)
    op.alter_column("documents", "owner_id", nullable=False)
    op.alter_column("documents", "version_group_id", nullable=False)
    op.alter_column("documents", "version_number", nullable=False)
    op.alter_column("documents", "is_current", nullable=False)
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=False)
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_version_group_id", "documents", ["version_group_id"])
    op.create_index("ix_documents_is_current", "documents", ["is_current"])
    op.create_unique_constraint(
        "uq_documents_tenant_sha256", "documents", ["tenant_id", "sha256"]
    )
    op.create_unique_constraint(
        "uq_document_version", "documents", ["version_group_id", "version_number"]
    )

    op.add_column("clauses", sa.Column("embedding", Vector(384), nullable=True))
    op.create_unique_constraint(
        "uq_clause_per_document", "clauses", ["document_id", "clause_id"]
    )
    op.create_index(
        "ix_clauses_embedding_hnsw",
        "clauses",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "subject_id", name="uq_tenant_member"),
    )
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_tenant_memberships_subject_id", "tenant_memberships", ["subject_id"])

    op.create_table(
        "document_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("principal_type", sa.String(16), nullable=False),
        sa.Column("principal_id", sa.String(128), nullable=False),
        sa.Column("permission", sa.String(16), nullable=False, server_default="read"),
        sa.Column("granted_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "document_id", "principal_type", "principal_id", "permission",
            name="uq_document_permission"
        ),
    )
    op.create_index("ix_document_permissions_document_id", "document_permissions", ["document_id"])


def downgrade():
    op.drop_index("ix_document_permissions_document_id", table_name="document_permissions")
    op.drop_table("document_permissions")
    op.drop_index("ix_tenant_memberships_subject_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_tenant_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_index("ix_clauses_embedding_hnsw", table_name="clauses")
    op.drop_constraint("uq_clause_per_document", "clauses", type_="unique")
    op.drop_column("clauses", "embedding")
    op.drop_constraint("uq_document_version", "documents", type_="unique")
    op.drop_constraint("uq_documents_tenant_sha256", "documents", type_="unique")
    op.drop_index("ix_documents_is_current", table_name="documents")
    op.drop_index("ix_documents_version_group_id", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=True)
    op.drop_constraint("fk_documents_supersedes", "documents", type_="foreignkey")
    for column in (
        "source_updated_at", "supersedes_document_id", "is_current",
        "version_number", "version_group_id", "owner_id", "tenant_id"
    ):
        op.drop_column("documents", column)
    op.execute("DROP EXTENSION IF EXISTS vector")
