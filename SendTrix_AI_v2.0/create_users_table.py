from db import get_postgres_connection
 
conn = get_postgres_connection()
 
try:
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                microsoft_user_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
 
    conn.commit()
    print("Users table created successfully!")
 
finally:
    conn.close()