# app_server.py
import os
import io
import glob
import socket
import base64
import cv2
import qrcode
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from src.engine.pipeline import WhiteboardEngine

app = Flask(__name__)
app.config["SECRET_KEY"] = "whiteboard-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*")

engine = WhiteboardEngine()

LECTURE_SLIDES = []


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def list_available_images() -> list:
    """Lists all real images in test_images/, ignoring debug_* files and sorted by newest first."""
    os.makedirs("test_images", exist_ok=True)
    files = []
    for ext in ("*.jpeg", "*.jpg", "*.png", "*.webp"):
        for path in glob.glob(os.path.join("test_images", ext)):
            filename = os.path.basename(path)
            if not filename.startswith("debug_"):
                files.append(path.replace("\\", "/"))
    # Sort by most recently modified so your newest image is always first!
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files


@app.route("/")
def projector_view():
    student_url = f"http://{get_local_ip()}:5000/student"
    qr_b64 = generate_qr_base64(student_url)
    images = list_available_images()
    return render_template(
        "projector.html",
        qr_b64=qr_b64,
        student_url=student_url,
        slides=LECTURE_SLIDES,
        images=images,
    )


@app.route("/api/images", methods=["GET"])
def get_images():
    """Returns refreshed list of images in test_images/ without restarting the server."""
    return jsonify({"images": list_available_images()})


@app.route("/student")
def student_view():
    return render_template("student_notes.html", slides=LECTURE_SLIDES)


@app.route("/api/scan", methods=["POST"])
def trigger_scan():
    data = request.json or {}
    requested_path = data.get("image_path")
    replace_index = data.get("replace_index")
    use_warp = data.get(
        "use_warp", False
    )  # False by default so old calibration doesn't ruin new images!

    is_retry = replace_index is not None and 0 <= replace_index < len(LECTURE_SLIDES)

    # If recapturing an existing slide and no new image_path was explicitly chosen, use that slide's original image
    if is_retry and not requested_path:
        requested_path = LECTURE_SLIDES[replace_index].get("image_path")

    # Fallback to the newest image in test_images/
    available = list_available_images()
    image_path = (
        requested_path
        if (requested_path and os.path.exists(requested_path))
        else (available[0] if available else None)
    )

    if not image_path:
        err_msg = "No images found in test_images/"
        socketio.emit("scan_status", {"status": "error", "message": err_msg})
        return jsonify({"status": "error", "message": err_msg}), 400

    socketio.emit(
        "scan_status",
        {
            "status": "scanning",
            "mode": f"recapturing ({os.path.basename(image_path)})"
            if is_retry
            else f"scanning {os.path.basename(image_path)}",
        },
    )

    print(f"\n[SCAN] Reading file: {image_path} | Retry={is_retry} | Warp={use_warp}")
    frame = cv2.imread(image_path)
    if frame is None:
        err_msg = f"Could not read {image_path}"
        socketio.emit("scan_status", {"status": "error", "message": err_msg})
        return jsonify({"status": "error", "message": err_msg}), 400

    # Warp is opt-in and owned by the engine (guardrail: never apply stale calibration).
    result = engine.process(frame, retry=is_retry, use_warp=use_warp)
    diagrams = [d.to_dict() for d in result.diagrams]

    if result.status == "success":
        if is_retry:
            LECTURE_SLIDES[replace_index]["latex"] = result.latex
            LECTURE_SLIDES[replace_index]["diagrams"] = diagrams
            LECTURE_SLIDES[replace_index]["image_path"] = image_path
            LECTURE_SLIDES[replace_index]["timestamp"] = datetime.now().strftime("%I:%M %p")
            updated_slide = LECTURE_SLIDES[replace_index]

            socketio.emit("update_latex_slide", {
                "index": replace_index,
                "slide": updated_slide
            })
            return jsonify({"status": "success", "slide": updated_slide, "replaced": True})
        else:
            slide_data = {
                "slide_num": len(LECTURE_SLIDES) + 1,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "image_path": image_path,
                "latex": result.latex,
                "diagrams": diagrams
            }
            LECTURE_SLIDES.append(slide_data)

            socketio.emit("new_latex_slide", slide_data)
            return jsonify({"status": "success", "slide": slide_data, "replaced": False})
    else:
        socketio.emit("scan_status", {"status": "error", "message": result.error})
        return jsonify({"status": "error", "message": result.error}), 500


if __name__ == "__main__":
    ip = get_local_ip()
    print(f"\n=======================================================")
    print(f" Projector UI:   http://localhost:5000")
    print(f" Student UI:     http://{ip}:5000/student")
    print(f"=======================================================\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
