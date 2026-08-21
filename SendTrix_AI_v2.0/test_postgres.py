import psycopg
 
try:
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="sendtrix",
        user="postgres",
        password="itst1999@G"
    )
 
    print("PostgreSQL connection successful!")
 
    conn.close()
 
except Exception as e:
    print("PostgreSQL connection failed:")
    print(e)
 