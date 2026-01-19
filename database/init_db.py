import sqlite3
import os

def init_db():
    if not os.path.exists("database"):
        os.makedirs("database")
        
    db_path = os.path.join("database", "data_pipeline.db")
    schema_path = os.path.join("database", "schema.sql")

    conn = sqlite3.connect(db_path)
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.close()
    print(f"Banco criado com sucesso em: {db_path}")

if __name__ == "__main__":
    init_db()