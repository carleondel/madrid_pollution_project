import psycopg2

conn = psycopg2.connect(
    dbname="madrid_pollution",
    user="madrid_user",
    password="madrid_pass",
    host="localhost",
    port="5432"
)

print("Connected!")
conn.close()
