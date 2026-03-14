# app.py
"""DJOrganizer v19 — Flask web server.

PRIVACY-FIRST DESIGN:
- No telemetry, no analytics, no external calls — runs 100% offline
- No audio fingerprinting or content hashing — never identifies specific recordings
- No file paths in CSV exports — only musical tags (title, artist, genre, energy, etc.)
- Undo log (moves.json) contains paths for reversal only — auto-deletes after 24h
- No logging of file sources, download origins, or acquisition metadata
- The app must never create data that could be used as liability against the user
"""
import os
import json
import secrets
import shutil
import socket
from pathlib import Path
from flask import (Flask, Response, render_template, request, jsonify,
                   session, stream_with_context)
from engine.classifier import classify_file
from engine.tagger import tag_file, read_metadata
from engine.config import load_config, save_config, validate_path, DEFAULT_CONFIG
from engine.genres import get_folder_name, get_all_active_genres, AUDIO_EXTS

def create_app(testing=False):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config["TESTING"] = testing

    CONFIG_FILE = Path(__file__).parent / "djorganizer_config.txt"
    MOVES_FILE = Path(__file__).parent / "djorganizer_moves.json"

    @app.before_request
    def ensure_csrf():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)

    def check_csrf():
        token = request.json.get("csrf_token") or request.form.get("csrf_token")
        return token == session.get("csrf_token")

    # ── Pages ──
    # Privacy-first: auto-delete stale undo data on launch (>24h old)
    # moves.json contains file paths needed for undo — minimize retention
    if MOVES_FILE.exists():
        import time
        age = time.time() - MOVES_FILE.stat().st_mtime
        if age > 86400:  # 24 hours
            MOVES_FILE.unlink()

    @app.route("/")
    def welcome():
        has_undo = MOVES_FILE.exists()
        config = load_config(CONFIG_FILE)
        return render_template("welcome.html",
                               csrf_token=session.get("csrf_token"),
                               has_undo=has_undo,
                               config=config)

    @app.route("/preview")
    def preview():
        return render_template("preview.html",
                               csrf_token=session.get("csrf_token"))

    @app.route("/results")
    def results():
        return render_template("results.html",
                               csrf_token=session.get("csrf_token"))

    # ── API ──
    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        """Start scan — returns SSE stream with progress updates."""
        if not check_csrf():
            return jsonify({"error": "Invalid CSRF token"}), 403

        data = request.get_json()
        if not data or "path" not in data:
            return jsonify({"error": "Missing path"}), 400

        source = Path(data["path"])
        if not validate_path(source):
            return jsonify({"error": "Path rejected for safety"}), 403
        if not source.exists() or not source.is_dir():
            return jsonify({"error": "Folder not found"}), 404

        # Store resolved source for scope-checking in /api/sort
        session["scanned_source"] = str(source.resolve())

        # Collect audio files recursively — skip symlinks to prevent escape
        audio_files = sorted(
            [f for f in source.rglob("*")
             if f.is_file() and not f.is_symlink() and f.suffix.lower() in AUDIO_EXTS],
            key=lambda x: x.name.lower()
        )
        total = len(audio_files)

        def generate():
            tracks = []
            locale_counts = {}
            for i, f in enumerate(audio_files):
                classification = classify_file(f)
                metadata = read_metadata(f)
                tags = tag_file(f, classification, metadata)
                track_dict = {**tags.__dict__, "filepath": str(tags.filepath)}
                tracks.append(track_dict)

                if track_dict["genre"] in ("israeli", "arabic", "russian",
                                           "kpop", "jpop", "bollywood", "turkish"):
                    locale_counts[track_dict["genre"]] = locale_counts.get(track_dict["genre"], 0) + 1

                if (i + 1) % 10 == 0 or i == total - 1:
                    yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': total, 'latest': track_dict['title']})}\n\n"

            active_locales = [g for g, c in locale_counts.items() if c >= 5]
            yield f"data: {json.dumps({'type': 'complete', 'tracks': tracks, 'total': len(tracks), 'active_locales': active_locales, 'source_path': str(source)})}\n\n"

        return Response(stream_with_context(generate()),
                        mimetype="text/event-stream")

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        config = load_config(CONFIG_FILE) or DEFAULT_CONFIG.copy()
        return jsonify(config)

    @app.route("/api/config", methods=["POST"])
    def api_config_save():
        if not check_csrf():
            return jsonify({"error": "Invalid CSRF token"}), 403
        data = request.get_json()
        save_config(data, CONFIG_FILE)
        return jsonify({"status": "saved"})

    @app.route("/api/sort", methods=["POST"])
    def api_sort():
        if not check_csrf():
            return jsonify({"error": "Invalid CSRF token"}), 403

        data = request.get_json()
        tracks = data.get("tracks", [])
        output_path = Path(data.get("output_path", ""))
        copy_mode = data.get("copy_mode", True)
        filename_suffix = data.get("filename_suffix", False)

        if not validate_path(output_path):
            return jsonify({"error": "Output path rejected"}), 403

        # Check disk space — walk up to nearest existing parent
        check_path = output_path
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent
        total_disk, used, free = shutil.disk_usage(check_path)
        needed = sum(Path(t["filepath"]).stat().st_size for t in tracks if Path(t["filepath"]).exists())
        if copy_mode and free < needed * 1.1:
            return jsonify({"error": "Not enough disk space"}), 507

        # Validate scanned source scope — src files must be within scanned dir
        scanned_source = session.get("scanned_source")
        if not scanned_source:
            return jsonify({"error": "No scan performed — scan a folder first"}), 400
        scanned_root = Path(scanned_source).resolve()

        # Execute sort
        moves = []
        errors = []
        MAX_DUP = 9999
        for t in tracks:
            src = Path(t.get("filepath", ""))
            # Validate: must exist, be a file, have audio extension, be within scanned dir
            if not src.exists() or not src.is_file():
                errors.append({"file": t.get("filepath", ""), "error": "File not found"})
                continue
            if src.suffix.lower() not in AUDIO_EXTS:
                errors.append({"file": str(src), "error": "Not an audio file"})
                continue
            try:
                if scanned_root not in src.resolve().parents and src.resolve() != scanned_root:
                    errors.append({"file": str(src), "error": "File outside scanned folder"})
                    continue
            except (OSError, ValueError):
                errors.append({"file": str(src), "error": "Path resolution failed"})
                continue

            genre_folder = get_folder_name(t["genre"])
            dest_dir = output_path / genre_folder
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Apply filename suffix if enabled: "Track [House][H].ext"
            dest_name = src.name
            if filename_suffix:
                stem, ext = src.stem, src.suffix
                genre_label = t.get("genre", "").replace("_", " ").title()
                energy_label = t.get("energy", "")[0] if t.get("energy") else ""
                dest_name = f"{stem} [{genre_label}][{energy_label}]{ext}"
            dest = dest_dir / dest_name

            if dest.exists():
                stem, suffix = dest.stem, dest.suffix
                counter = 1
                while dest.exists() and counter <= MAX_DUP:
                    dest = dest_dir / f"{stem}_dup{counter}{suffix}"
                    counter += 1
                if dest.exists():
                    errors.append({"file": str(src), "error": "Too many duplicates"})
                    continue

            try:
                if copy_mode:
                    shutil.copy2(str(src), str(dest))
                else:
                    shutil.move(str(src), str(dest))
                moves.append({"from": str(src), "to": str(dest)})
            except Exception as e:
                errors.append({"file": str(src), "error": str(e)})

        MOVES_FILE.write_text(json.dumps({
            "copy_mode": copy_mode,
            "moves": moves
        }, indent=2), encoding="utf-8")

        return jsonify({
            "moved": len(moves),
            "errors": errors,
            "copy_mode": copy_mode,
        })

    @app.route("/api/undo", methods=["POST"])
    def api_undo():
        if not check_csrf():
            return jsonify({"error": "Invalid CSRF token"}), 403
        if not MOVES_FILE.exists():
            return jsonify({"error": "No undo data found"}), 404

        data = json.loads(MOVES_FILE.read_text(encoding="utf-8"))
        reverted = 0
        skipped = 0
        for move in reversed(data["moves"]):
            dest = Path(move["to"])
            src = Path(move["from"])
            # Re-validate both paths before any file operation
            if not validate_path(dest) or not validate_path(src):
                skipped += 1
                continue
            if not dest.exists():
                skipped += 1
                continue
            try:
                if data.get("copy_mode"):
                    dest.unlink()
                else:
                    shutil.move(str(dest), str(src))
                reverted += 1
            except Exception:
                skipped += 1

        MOVES_FILE.unlink()
        return jsonify({"reverted": reverted, "skipped": skipped})

    @app.route("/api/export-csv", methods=["POST"])
    def api_export_csv():
        if not check_csrf():
            return jsonify({"error": "Invalid CSRF token"}), 403
        data = request.get_json()
        tracks = data.get("tracks", [])
        source_path = Path(data.get("source_path", ""))

        if not validate_path(source_path):
            return jsonify({"error": "Export path rejected for safety"}), 403
        if not source_path.exists():
            return jsonify({"error": "Source path not found"}), 404

        csv_path = source_path.parent / "djorganizer_tags.csv"
        import csv
        fieldnames = ["title", "artist", "genre", "energy", "clean",
                      "bpm", "key", "mix_type", "year", "language",
                      "vocal_type", "duration", "date_added", "era"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in tracks:
                row = {k: t.get(k, "") for k in fieldnames}
                writer.writerow(row)

        return jsonify({"csv_path": str(csv_path)})

    return app

def find_free_port(start=5555, max_tries=10):
    """Find a free port starting from 5555."""
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start

def pick_folder_gui():
    """Show a native OS folder picker. Returns path string or None."""
    import sys
    if sys.platform == "darwin":
        # Use osascript for a native Finder dialog (no tkinter dependency)
        import subprocess
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "Finder" to activate\n'
             'set theFolder to choose folder with prompt "Select your music folder"\n'
             'return POSIX path of theFolder'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    else:
        # Windows/Linux: use tkinter
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            folder = filedialog.askdirectory(title="Select your music folder")
            root.destroy()
            if folder:
                return folder
        except Exception:
            pass
    return None

if __name__ == "__main__":
    import sys
    import webbrowser

    # Check for --no-picker flag or command-line path
    folder_path = None
    if len(sys.argv) > 1 and sys.argv[1] != "--no-picker":
        folder_path = sys.argv[1]
    elif "--no-picker" not in sys.argv:
        folder_path = pick_folder_gui()

    app = create_app()
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    if folder_path:
        # Pre-fill the folder path so the welcome page can auto-scan
        app.config["PREFILL_PATH"] = folder_path
        url += f"?path={folder_path}"
    print(f"DJOrganizer v19 running at http://127.0.0.1:{port}")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=False)
