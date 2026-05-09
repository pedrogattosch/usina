import cv2
import math
import sqlite3
from datetime import datetime

VIDEO_PATH = "teste_usina.mp4"
DB_NAME = "usina_dados.db"

RES_W = 640
RES_H = 480

OUTPUT_VIDEO = "resultado_teste_video.mp4"
SHOW_WINDOW = True
SAVE_OUTPUT_VIDEO = True

# A calibração foca a faixa central, onde o fluxo cruza a linha do YOLO.
ROI_X1 = 20
ROI_Y1 = 100
ROI_X2 = 620
ROI_Y2 = 470

LINE_Y = 224
BAND_OFFSET = 30
LINE_TOP = LINE_Y - BAND_OFFSET
LINE_BOTTOM = LINE_Y + BAND_OFFSET

# Filtros calibrados para os blobs do vídeo redimensionado.
MIN_AREA = 300
MAX_AREA = 5000
MIN_WIDTH = 10
MIN_HEIGHT = 22
MAX_WIDTH = 80
MAX_HEIGHT = 140
MIN_ASPECT_RATIO = 1.15
MAX_ASPECT_RATIO = 6.0

MAX_DISTANCE = 75
MAX_MISSING_FRAMES = 15
MIN_TRACK_HITS = 2
MIN_TRACK_TRAVEL = 28
MERGE_DISTANCE_X = 12
MERGE_DISTANCE_Y = 22
TRACK_POINT_Y = 0.5

print("Conectando ao banco de dados usina_dados.db...")

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS fluxo_pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora DATETIME,
        evento TEXT
    )
""")

conn.commit()


def registrar_evento(tipo_evento):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO fluxo_pessoas (data_hora, evento) VALUES (?, ?)",
        (agora, tipo_evento)
    )

    conn.commit()


def get_zone(cy):
    if cy < LINE_TOP:
        return "acima"

    if cy > LINE_BOTTOM:
        return "abaixo"

    return "meio"


def is_valid_contour(w, h, area):
    if area < MIN_AREA:
        return False

    if area > MAX_AREA:
        return False

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        return False

    if w > MAX_WIDTH or h > MAX_HEIGHT:
        return False

    aspect_ratio = h / max(w, 1)

    if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
        return False

    return True


def should_merge_boxes(a, b):
    ax2 = a["x"] + a["w"]
    ay2 = a["y"] + a["h"]
    bx2 = b["x"] + b["w"]
    by2 = b["y"] + b["h"]

    overlap_x = min(ax2, bx2) - max(a["x"], b["x"])
    overlap_y = min(ay2, by2) - max(a["y"], b["y"])

    if overlap_x > 0 and overlap_y > 0:
        return True

    close_x = abs(a["cx"] - b["cx"]) <= MERGE_DISTANCE_X
    close_y = abs(a["cy"] - b["cy"]) <= MERGE_DISTANCE_Y
    return close_x and close_y


def merge_detections(deteccoes):
    merged = []

    for det in sorted(deteccoes, key=lambda item: item["area"], reverse=True):
        combined = False

        for current in merged:
            if not should_merge_boxes(current, det):
                continue

            x1 = min(current["x"], det["x"])
            y1 = min(current["y"], det["y"])
            x2 = max(current["x"] + current["w"], det["x"] + det["w"])
            y2 = max(current["y"] + current["h"], det["y"] + det["h"])

            current["x"] = x1
            current["y"] = y1
            current["w"] = x2 - x1
            current["h"] = y2 - y1
            current["cx"] = int(x1 + current["w"] / 2)
            current["cy"] = int(y1 + current["h"] / 2)
            current["area"] = max(current["area"], det["area"])
            combined = True
            break

        if not combined:
            merged.append(det.copy())

    return [
        det for det in merged
        if is_valid_contour(det["w"], det["h"], det["area"])
    ]


def create_new_tracker(cx, cy, det):
    return {
        "cx": cx,
        "cy": cy,
        "prev_cy": cy,
        "first_cy": cy,
        "start_zone": get_zone(cy),
        "last_zone": get_zone(cy),
        "counted": False,
        "missing": 0,
        "updated": True,
        "hits": 1,
        "age": 1,
        "min_cy": cy,
        "max_cy": cy,
        "box": det
    }


print("Iniciando contagem por vídeo com OpenCV melhorado...")

video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print(f"Erro: não foi possível abrir o vídeo '{VIDEO_PATH}'.")
    print("Verifique se o arquivo está na mesma pasta do script.")
    conn.close()
    raise SystemExit

fgbg = cv2.createBackgroundSubtractorMOG2(
    history=250,
    varThreshold=20,
    detectShadows=False
)

kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 9))

entradas = 0
saidas = 0

rastreadores = {}
proximo_id = 0

saida_video = None

if SAVE_OUTPUT_VIDEO:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    saida_video = cv2.VideoWriter(
        OUTPUT_VIDEO,
        fourcc,
        20.0,
        (RES_W, RES_H)
    )

print("Pressione Q para encerrar.")
print("Revise o vídeo gerado para conferir se a zona de contagem está bem posicionada.")

try:
    while True:
        ret, frame = video.read()

        if not ret:
            print("Fim do vídeo.")
            break

        frame = cv2.resize(frame, (RES_W, RES_H))

        roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]

        mascara = fgbg.apply(roi)

        _, mascara = cv2.threshold(
            mascara,
            210,
            255,
            cv2.THRESH_BINARY
        )

        mascara = cv2.morphologyEx(
            mascara,
            cv2.MORPH_OPEN,
            kernel_open,
            iterations=1
        )

        mascara = cv2.morphologyEx(
            mascara,
            cv2.MORPH_CLOSE,
            kernel_close,
            iterations=2
        )

        mascara = cv2.dilate(
            mascara,
            None,
            iterations=1
        )

        contornos, _ = cv2.findContours(
            mascara,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        deteccoes = []

        for contorno in contornos:
            area = cv2.contourArea(contorno)
            x, y, w, h = cv2.boundingRect(contorno)

            if not is_valid_contour(w, h, area):
                continue

            x_global = x + ROI_X1
            y_global = y + ROI_Y1

            cx = int(x_global + w / 2)
            cy = int(y_global + (h * TRACK_POINT_Y))

            deteccoes.append({
                "cx": cx,
                "cy": cy,
                "x": x_global,
                "y": y_global,
                "w": w,
                "h": h,
                "area": area
            })

        deteccoes = merge_detections(deteccoes)

        for id_obj in rastreadores:
            rastreadores[id_obj]["updated"] = False

        matched_ids = set()

        for det in deteccoes:
            cx = det["cx"]
            cy = det["cy"]

            melhor_id = None
            melhor_distancia = MAX_DISTANCE

            for id_obj, tracker in rastreadores.items():
                if id_obj in matched_ids:
                    continue

                distancia = math.hypot(
                    cx - tracker["cx"],
                    cy - tracker["cy"]
                )

                if distancia < melhor_distancia:
                    melhor_distancia = distancia
                    melhor_id = id_obj

            if melhor_id is None:
                rastreadores[proximo_id] = create_new_tracker(cx, cy, det)
                proximo_id += 1
                continue

            tracker = rastreadores[melhor_id]

            prev_cy = tracker["cy"]
            old_zone = tracker["last_zone"]
            new_zone = get_zone(cy)

            tracker["cx"] = cx
            tracker["cy"] = cy
            tracker["prev_cy"] = prev_cy
            tracker["missing"] = 0
            tracker["updated"] = True
            tracker["hits"] += 1
            tracker["age"] += 1
            tracker["min_cy"] = min(tracker["min_cy"], cy)
            tracker["max_cy"] = max(tracker["max_cy"], cy)
            tracker["box"] = det
            matched_ids.add(melhor_id)

            if not tracker["counted"]:
                travel = tracker["max_cy"] - tracker["min_cy"]
                is_mature_track = tracker["hits"] >= MIN_TRACK_HITS
                crossed_down = prev_cy < LINE_Y <= cy
                crossed_up = prev_cy > LINE_Y >= cy

                if (
                    crossed_down
                    and travel >= MIN_TRACK_TRAVEL
                    and is_mature_track
                ):
                    entradas += 1
                    tracker["counted"] = True
                    registrar_evento("Entrada")

                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"Entrada detectada! Total entradas: {entradas}"
                    )

                elif (
                    crossed_up
                    and travel >= MIN_TRACK_TRAVEL
                    and is_mature_track
                ):
                    saidas += 1
                    tracker["counted"] = True
                    registrar_evento("Saida")

                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"Saida detectada! Total saidas: {saidas}"
                    )

            if new_zone != "meio":
                tracker["last_zone"] = new_zone

        ids_para_remover = []

        for id_obj, tracker in rastreadores.items():
            if not tracker.get("updated", False):
                tracker["missing"] += 1
                tracker["age"] += 1

            if tracker["missing"] > MAX_MISSING_FRAMES:
                ids_para_remover.append(id_obj)

        for id_obj in ids_para_remover:
            del rastreadores[id_obj]

        cv2.rectangle(
            frame,
            (ROI_X1, ROI_Y1),
            (ROI_X2, ROI_Y2),
            (180, 180, 180),
            1
        )

        cv2.line(
            frame,
            (ROI_X1, LINE_TOP),
            (ROI_X2, LINE_TOP),
            (255, 0, 0),
            2
        )

        cv2.line(
            frame,
            (ROI_X1, LINE_BOTTOM),
            (ROI_X2, LINE_BOTTOM),
            (255, 0, 0),
            2
        )

        cv2.putText(
            frame,
            "ZONA DE CONTAGEM",
            (20, LINE_TOP - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 0, 0),
            2
        )

        for id_obj, tracker in rastreadores.items():
            det = tracker.get("box")

            if not det:
                continue

            x = det["x"]
            y = det["y"]
            w = det["w"]
            h = det["h"]

            color = (0, 255, 0)

            if tracker.get("counted"):
                color = (0, 255, 255)

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                color,
                2
            )

            cv2.circle(
                frame,
                (tracker["cx"], tracker["cy"]),
                5,
                (0, 0, 255),
                -1
            )

            cv2.putText(
                frame,
                f"ID {id_obj} | {tracker['last_zone']}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

        cv2.putText(
            frame,
            f"Entradas: {entradas}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Saidas: {saidas}",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        cv2.putText(
            frame,
            f"Objetos rastreados: {len(rastreadores)}",
            (10, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        if saida_video is not None:
            saida_video.write(frame)

        if SHOW_WINDOW:
            cv2.imshow("Teste OpenCV melhorado - Usina", frame)

            key = cv2.waitKey(30)

            if key & 0xFF == ord("q"):
                break

finally:
    print("Encerrando o teste...")

    if saida_video is not None:
        saida_video.release()

    video.release()
    conn.close()
    cv2.destroyAllWindows()

    print(f"Total de entradas: {entradas}")
    print(f"Total de saídas: {saidas}")
    print(f"Vídeo gerado: {OUTPUT_VIDEO}")
