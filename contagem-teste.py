import cv2
import math
import sqlite3
from datetime import datetime

print("Conectando ao banco de dados usina_dados.db...")
conn = sqlite3.connect('usina_dados.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS fluxo_pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora DATETIME,
        evento TEXT
    )
''')
conn.commit()

def registrar_evento(tipo_evento):
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)",
        (agora, tipo_evento)
    )
    conn.commit()

print("Iniciando contagem por vídeo...")

video = cv2.VideoCapture("teste_usina.mp4")

fgbg = cv2.createBackgroundSubtractorMOG2(
    history=500,
    varThreshold=50,
    detectShadows=False
)

entradas = 0
saidas = 0
linha_y = 240
rastreadores = {}
proximo_id = 0

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
saida_video = cv2.VideoWriter(
    'resultado_teste_video.mp4',
    fourcc,
    20.0,
    (640, 480)
)

try:
    while True:
        ret, frame = video.read()

        if not ret:
            print("Fim do vídeo.")
            break

        frame = cv2.resize(frame, (640, 480))

        mascara = fgbg.apply(frame)
        _, mascara = cv2.threshold(mascara, 200, 255, cv2.THRESH_BINARY)
        mascara = cv2.dilate(mascara, None, iterations=4)

        contornos, _ = cv2.findContours(
            mascara,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.line(frame, (0, linha_y), (640, linha_y), (255, 0, 0), 2)

        centros_atuais = []

        for contorno in contornos:
            if cv2.contourArea(contorno) < 2000:
                continue

            x, y, w, h = cv2.boundingRect(contorno)
            centros_atuais.append((int(x + w / 2), int(y + h / 2), x, y, w, h))

        novos_rastreadores = {}

        for cx, cy, x, y, w, h in centros_atuais:
            rastreado = False

            for id_obj, (ant_cx, ant_cy) in rastreadores.items():
                if math.hypot(cx - ant_cx, cy - ant_cy) < 60:
                    novos_rastreadores[id_obj] = (cx, cy)
                    rastreado = True

                    if ant_cy < linha_y and cy >= linha_y:
                        entradas += 1
                        registrar_evento('Entrada')
                        cv2.line(frame, (0, linha_y), (640, linha_y), (0, 255, 0), 5)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Entrada detectada! Total entradas: {entradas}")

                    elif ant_cy > linha_y and cy <= linha_y:
                        saidas += 1
                        registrar_evento('Saida')
                        cv2.line(frame, (0, linha_y), (640, linha_y), (0, 0, 255), 5)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saida detectada! Total saidas: {saidas}")

                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(
                        frame,
                        f"ID: {id_obj}",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )
                    break

            if not rastreado:
                novos_rastreadores[proximo_id] = (cx, cy)
                proximo_id += 1

        rastreadores = novos_rastreadores

        cv2.putText(frame, f"Entradas: {entradas}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Saidas: {saidas}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        saida_video.write(frame)

        cv2.imshow("Teste com vídeo", frame)

        key = cv2.waitKey(30)
        if key & 0xFF == ord('q'):
            break

finally:
    print("Encerrando o teste...")
    saida_video.release()
    video.release()
    conn.close()
    cv2.destroyAllWindows()
