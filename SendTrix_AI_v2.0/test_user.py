from db import get_postgres_connection
 
conn = get_postgres_connection()
 
try:
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO users (
                microsoft_user_id,
                email,
                display_name
            )
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            "test-microsoft-id",
            "test@sendtrix.local",
            "Test User"
        ))
 
        user_id = cursor.fetchone()[0]
 
    conn.commit()
 
    print("User created!")
    print("SendTrix user ID:", user_id)
 
finally:
    conn.close()
 