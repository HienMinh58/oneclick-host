import psycopg2
import psycopg2.extras
from config import DATABASE_URL

# Register UUID adapter
psycopg2.extras.register_uuid()


def get_connection():
    """Create a new database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_queued_deployment(conn):
    """
    Atomically pick up the next queued deployment.
    Uses SELECT ... FOR UPDATE SKIP LOCKED for safe concurrent access (future).
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT d."Id", d."ServiceId", d."Version",
                   s."RepoUrl", s."Branch", s."Subfolder", s."Name" as "ServiceName",
                   p."Name" as "ProjectName"
            FROM "Deployments" d
            JOIN "Services" s ON d."ServiceId" = s."Id"
            JOIN "Projects" p ON s."ProjectId" = p."Id"
            WHERE d."Status" = 'queued'
            ORDER BY d."CreatedAt" ASC
            LIMIT 1
            FOR UPDATE OF d SKIP LOCKED
        """)
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE "Deployments"
                SET "Status" = 'cloning', "StartedAt" = NOW()
                WHERE "Id" = %s
            """, (row["Id"],))
            conn.commit()
        return row


def update_deployment_status(conn, deployment_id, status, **kwargs):
    """Update deployment status and optional fields."""
    sets = ['"Status" = %s']
    values = [status]

    if "error_message" in kwargs:
        sets.append('"ErrorMessage" = %s')
        values.append(kwargs["error_message"])

    if "image_tag" in kwargs:
        sets.append('"ImageTag" = %s')
        values.append(kwargs["image_tag"])

    if "build_logs" in kwargs:
        sets.append('"BuildLogs" = %s')
        values.append(kwargs["build_logs"])

    if status in ("live", "failed"):
        sets.append('"CompletedAt" = NOW()')

    values.append(deployment_id)

    with conn.cursor() as cur:
        cur.execute(
            f'UPDATE "Deployments" SET {", ".join(sets)} WHERE "Id" = %s',
            values
        )
    conn.commit()


def update_service_status(conn, service_id, status, **kwargs):
    """Update service status and optional fields."""
    sets = ['"Status" = %s', '"UpdatedAt" = NOW()']
    values = [status]

    if "live_url" in kwargs:
        sets.append('"LiveUrl" = %s')
        values.append(kwargs["live_url"])

    if "container_id" in kwargs:
        sets.append('"ContainerId" = %s')
        values.append(kwargs["container_id"])

    if "detected_stack" in kwargs:
        sets.append('"DetectedStack" = %s')
        values.append(kwargs["detected_stack"])

    values.append(service_id)

    with conn.cursor() as cur:
        cur.execute(
            f'UPDATE "Services" SET {", ".join(sets)} WHERE "Id" = %s',
            values
        )
    conn.commit()


def get_env_vars(conn, service_id):
    """Get environment variables for a service."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT "Key", "Value"
            FROM "EnvironmentVariables"
            WHERE "ServiceId" = %s
        """, (service_id,))
        return {row["Key"]: row["Value"] for row in cur.fetchall()}
