import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="root",
    autocommit=True,
)

with conn.cursor() as cur:
    cur.execute(
        "CREATE DATABASE IF NOT EXISTS robot_dispatch "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute("CREATE USER IF NOT EXISTS 'dispatch'@'localhost' IDENTIFIED BY 'dispatch'")
    cur.execute("CREATE USER IF NOT EXISTS 'dispatch'@'127.0.0.1' IDENTIFIED BY 'dispatch'")
    cur.execute("GRANT ALL PRIVILEGES ON robot_dispatch.* TO 'dispatch'@'localhost'")
    cur.execute("GRANT ALL PRIVILEGES ON robot_dispatch.* TO 'dispatch'@'127.0.0.1'")
    cur.execute("FLUSH PRIVILEGES")

conn.close()
print("database and user ready")
