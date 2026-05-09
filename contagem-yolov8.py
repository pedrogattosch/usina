import cv2
import sqlite3
from datetime import datetime
from ultralytics import YOLO

VIDEO_PATH = "teste_usina.mp4"
DB_NAME = "usina_dados.db"

RES_W = 640
RES_H = 480

# Linha horizontal. 0.50 = meio da tela.
# Se quiser mais para baixo, use 0.60, 0.70 etc.
LINE_POS = 0.50
line_y = int(RES_H * LINE_POS)

IMG_SIZE = 416
CONF = 0.35

SHOW_WINDOW = True
SAVE_OUTPUT_VIDEO = True
OUTPUT_VIDEO = "resultado_yolov8_teste.mp4"

count_in = 0
count_out = 0

# Guarda o último Y de cada ID rastreado
track_memory = {}

# Evita contar o mesmo ID várias vezes seguidas
counted_ids = set()

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fluxo_pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME,
            evento TEXT
        )
    """)

    conn.commit()
    conn.close()

def registrar_evento(tipo_evento):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)",
        (agora, tipo_evento)
    )

    conn.commit()
    conn.close()

def crossed_line(y_prev, y_new):
    if y_prev < line_y and y_new >= line_y:
        return "Entrada"

    if y_prev >= line_y and y_new < line_y:
        return "Saida"

    return None

def main():
    global count_in, count_out, track_memory

    setup_database()

    print("Carregando modelo YOLOv8n...")
    model = YOLO("yolov8n.pt")
    model.fuse()

    print(f"Abrindo vídeo: {VIDEO_PATH}")
    video = cv2.VideoCapture(VIDEO_PATH)

    if not video.isOpened():
        print("Erro: não foi possível abrir o vídeo.")
        print("Verifique se o arquivo teste_usina.mp4 está na mesma pasta do script.")
        return

    writer = None

    if SAVE_OUTPUT_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            OUTPUT_VIDEO,
            fourcc,
            20.0,
            (RES_W, RES_H)
        )

    print("Iniciando teste com YOLOv8n...")
    print("Pressione Q para encerrar.")

    while True:
        ret, frame = video.read()

        if not ret:
            print("Fim do vídeo.")
            break

        frame = cv2.resize(frame, (RES_W, RES_H))

        results = model.track(
            frame,
            persist=True,
            classes=[0],       # classe 0 = pessoa
            imgsz=IMG_SIZE,
            conf=CONF,
            verbose=False
        )

        current_frame_memory = {}
        boxes = []
        ids = []

        if (
            results
            and results[0].boxes is not None
            and results[0].boxes.id is not None
        ):
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()

            for box, track_id_float in zip(boxes, ids):
                track_id = int(track_id_float)

                x1, y1, x2, y2 = box
                y_center = (y1 + y2) / 2
                x_center = (x1 + x2) / 2

                prev_y = track_memory.get(track_id)

                if prev_y is not None:
                    evento = crossed_line(prev_y, y_center)

                    if evento is not None and track_id not in counted_ids:
                        counted_ids.add(track_id)

                        if evento == "Entrada":
                            count_in += 1
                            registrar_evento("Entrada")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ENTRADA | ID {track_id}")

                        elif evento == "Saida":
                            count_out += 1
                            registrar_evento("Saida")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] SAÍDA | ID {track_id}")

                current_frame_memory[track_id] = y_center

                # Desenhos na tela
                x1, y1, x2, y2 = map(int, box)

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.circle(
                    frame,
                    (int(x_center), int(y_center)),
                    5,
                    (0, 0, 255),
                    -1
                )

                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

        track_memory = current_frame_memory

        # Linha de contagem
        cv2.line(
            frame,
            (0, line_y),
            (RES_W, line_y),
            (255, 0, 0),
            2
        )

        # Contadores
        cv2.putText(
            frame,
            f"ENTRADAS: {count_in}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"SAIDAS: {count_out}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        if writer is not None:
            writer.write(frame)

        if SHOW_WINDOW:
            cv2.imshow("Teste YOLOv8n - Usina do Conhecimento", frame)

            key = cv2.waitKey(1)
            if key & 0xFF == ord("q"):
                break

    video.release()

    if writer is not None:
        writer.release()

    cv2.destroyAllWindows()

    print("Teste finalizado.")
    print(f"Total de entradas: {count_in}")
    print(f"Total de saídas: {count_out}")
    print(f"Vídeo gerado: {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
