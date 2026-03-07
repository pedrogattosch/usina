import cv2
import math
import sqlite3
import numpy as np
from datetime import datetime
from picamera2 import Picamera2

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
print("Conectando ao banco de dados usina_dados.db...")
conn = sqlite3.connect('usina_dados.db', check_same_thread=False)
cursor = conn.cursor()

# Cria a tabela se ela não existir
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fluxo_pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora DATETIME,
        evento TEXT
    )
''')
conn.commit()

def registrar_evento(tipo_evento):
    """Guarda no banco de dados a hora exata e se foi entrada ou saida"""
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)", (agora, tipo_evento))
    conn.commit()

print("Iniciando contagem...")

# Inicializa a câmera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

entradas = 0
saidas = 0
linha_y = 240 
rastreadores = {}
proximo_id = 0

print("Pressione 'q' na janela do vídeo para fechar.")

try:
    while True:
        # 1. Captura o frame
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # 2. Aplica a máscara de detecção de movimento
        mascara = fgbg.apply(frame)
        _, mascara = cv2.threshold(mascara, 200, 255, cv2.THRESH_BINARY)
        mascara = cv2.dilate(mascara, None, iterations=4)

        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Desenha a linha de cruzamento na tela
        cv2.line(frame, (0, linha_y), (640, linha_y), (255, 0, 0), 2)

        # 3. Filtra objetos pelo tamanho
        centros_atuais = []
        for contorno in contornos:
            if cv2.contourArea(contorno) < 2000:
                continue
            x, y, w, h = cv2.boundingRect(contorno)
            centros_atuais.append((int(x + w / 2), int(y + h / 2), x, y, w, h))

        # 4. Lógica de Rastreamento e contagem
        novos_rastreadores = {}
        for cx, cy, x, y, w, h in centros_atuais:
            rastreado = False
            for id_obj, (ant_cx, ant_cy) in rastreadores.items():
                
                # Se moveu menos de 60 pixels, assume que é o mesmo objeto
                if math.hypot(cx - ant_cx, cy - ant_cy) < 60:
                    novos_rastreadores[id_obj] = (cx, cy)
                    rastreado = True
                    
                    # Lógica de cruzamento da linha
                    if ant_cy < linha_y and cy >= linha_y:
                        entradas += 1
                        registrar_evento('Entrada')
                        cv2.line(frame, (0, linha_y), (640, linha_y), (0, 255, 0), 5) # Pisca verde
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Entrada detectada! Total entradas: {entradas}")
                        
                    elif ant_cy > linha_y and cy <= linha_y:
                        saidas += 1
                        registrar_evento('Saida')
                        cv2.line(frame, (0, linha_y), (640, linha_y), (0, 0, 255), 5) # Pisca vermelho
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saida detectada! Total saidas: {saidas}")
                    
                    # Desenha o retângulo em volta da pessoa e o ID
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(frame, f"ID: {id_obj}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    break
            
            # Se for um objeto novo
            if not rastreado:
                novos_rastreadores[proximo_id] = (cx, cy)
                proximo_id += 1

        rastreadores = novos_rastreadores

        # Exibe os contadores finais na tela do vídeo
        cv2.putText(frame, f"Entradas: {entradas}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Saidas: {saidas}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # ATENÇÃO: Se for colocar para rodar automático, comente as linhas abaixo para não abrir a janela de vídeo
        # cv2.imshow("Contador Usina (4:3)", frame)
        # key = cv2.waitKey(1)
        # if key & 0xFF == ord('q'):
        #    break

finally:
    print("Encerrando o sistema...")
    conn.close() 
    cv2.destroyAllWindows()
    picam2.stop()