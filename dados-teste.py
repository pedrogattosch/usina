import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("usina_dados.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS fluxo_pessoas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora TEXT NOT NULL,
    evento TEXT NOT NULL
)
""")

cursor.execute("DELETE FROM fluxo_pessoas")

hoje = datetime.now().replace(minute=0, second=0, microsecond=0)

for hora in range(8, 22):
    quantidade_entradas = random.randint(2, 8)
    quantidade_saidas = random.randint(1, 6)

    for _ in range(quantidade_entradas):
        data_hora = hoje.replace(hour=hora) + timedelta(minutes=random.randint(0, 59))
        cursor.execute(
            "INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)",
            (data_hora.strftime("%Y-%m-%d %H:%M:%S"), "Entrada")
        )

    for _ in range(quantidade_saidas):
        data_hora = hoje.replace(hour=hora) + timedelta(minutes=random.randint(0, 59))
        cursor.execute(
            "INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)",
            (data_hora.strftime("%Y-%m-%d %H:%M:%S"), "Saida")
        )

conn.commit()
conn.close()

print("Banco de dados de teste criado com sucesso!")
