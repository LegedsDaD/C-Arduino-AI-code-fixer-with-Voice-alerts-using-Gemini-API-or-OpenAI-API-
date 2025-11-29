import hashlib
import threading
import tempfile
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from openai import OpenAI
import asyncio
import edge_tts
import pygame
import time

# ---------------- SETTINGS ----------------
OPENAI_API_KEY = "Your Api Key here"
CHECK_INTERVAL_MS = 1000  # 1 second polling for real-time detection

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- INITIALIZE PYGAME ----------------
pygame.mixer.init()

# ---------------- VOICE FUNCTION ----------------
selected_voice = "en-IN-NeerjaNeural"

def speak(text: str):
    """Run TTS in a separate thread using edge-tts and pygame for playback."""
    def tts_thread():
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            asyncio.run(edge_tts.Communicate(text, voice=selected_voice).save(temp_file.name))

            # Play audio
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            os.remove(temp_file.name)
        except Exception as e:
            print(f"[VOICE ERROR] {e}")

    threading.Thread(target=tts_thread, daemon=True).start()

# ---------------- AI FIX FUNCTION ----------------
def fix_code(code: str, callback):
    """Run AI fix in a separate thread and call callback with fixed code."""
    def ai_thread():
        try:
            speak("Fixing code using AI, please wait.")
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system",
                     "content": "You are an expert Arduino code fixer. Correct syntax and logic errors while keeping structure unchanged."},
                    {"role": "user", "content": code}
                ]
            )
            fixed_code = response.choices[0].message.content
            callback(fixed_code)
        except Exception as e:
            print(f"[AI ERROR]: {e}")
            callback(code)

    threading.Thread(target=ai_thread, daemon=True).start()

# ---------------- POPUP ----------------
def show_fix_popup(file_path: Path, old_code: str, root: tk.Tk):
    def apply_fix():
        def after_fix(fixed_code):
            if file_path.exists():
                file_path.write_text(fixed_code, encoding="utf-8")
                speak("The code has been fixed successfully.")
                messagebox.showinfo("Fixed", "AI has corrected the file.")
            popup.destroy()

        fix_code(old_code, after_fix)

    popup = tk.Toplevel(root)
    popup.title("Arduino Code Issue Detected")
    tk.Label(popup, text="Possible error detected.\nFix automatically?", font=("Arial", 13)).pack(pady=12)
    tk.Button(popup, text="Fix Code", command=apply_fix, bg="green", fg="white", font=("Arial", 12)).pack(pady=10)

# ---------------- FILE MONITOR ----------------
class FileMonitor:
    def __init__(self, file_path: Path, root: tk.Tk):
        self.file_path = file_path
        self.root = root
        self.last_hash = self.hash_file()
        self.monitoring = True
        self.poll_file()

    def hash_file(self):
        if self.file_path.exists():
            return hashlib.md5(self.file_path.read_bytes()).hexdigest()
        return None

    def stop_monitor(self):
        self.monitoring = False
        speak("Stopped monitoring.")

    def poll_file(self):
        if not self.monitoring:
            return

        if self.file_path.exists():
            new_hash = self.hash_file()
            if new_hash != self.last_hash:
                self.last_hash = new_hash
                try:
                    code = self.file_path.read_text(encoding="utf-8")

                    # --- AI detection ---
                    def after_ai_check(has_error):
                        if has_error:
                            speak("Possible code issue detected.")
                            show_fix_popup(self.file_path, code, self.root)

                    def ai_detect_thread():
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4.1-mini",
                                messages=[
                                    {"role": "system",
                                     "content": "You are an expert Arduino code checker. Detect if the code has any syntax or logical errors. "
                                                "Return 'YES' if errors exist, 'NO' if code is correct."},
                                    {"role": "user", "content": code}
                                ]
                            )
                            answer = response.choices[0].message.content.strip().upper()
                            after_ai_check("YES" in answer)
                        except Exception as e:
                            print(f"[AI DETECT ERROR] {e}")

                    threading.Thread(target=ai_detect_thread, daemon=True).start()

                except Exception as e:
                    print(f"[FILE READ ERROR] {e}")
        else:
            print(f"[MONITOR] File {self.file_path} not found, skipping check.")

        self.root.after(CHECK_INTERVAL_MS, self.poll_file)

# ---------------- FILE SELECT ----------------
def select_file(root: tk.Tk):
    while True:
        speak("Please select your Arduino .ino file.")
        file = filedialog.askopenfilename(filetypes=[("Arduino Sketch", "*.ino")], title="Select Arduino .ino file")
        if not file:
            speak("No file selected. Exiting.")
            return None
        if not file.endswith(".ino"):
            speak("Wrong file selected. Please select an Arduino .ino file.")
            continue
        return Path(file)

# ---------------- MONITOR CONTROL DIALOG ----------------
def monitor_control_dialog(root: tk.Tk, monitor: FileMonitor):
    dlg = tk.Toplevel(root)
    dlg.title("Monitor Control")
    dlg.geometry("300x120")
    tk.Label(dlg, text="Real-time monitoring active.", font=("Arial", 12)).pack(pady=10)

    def stop_monitor():
        monitor.stop_monitor()
        dlg.destroy()

    def monitor_another_file():
        monitor.stop_monitor()
        dlg.destroy()
        start_monitor(root)

    tk.Button(dlg, text="Stop Fixer", command=stop_monitor, bg="red", fg="white", width=15).pack(pady=5)
    tk.Button(dlg, text="Monitor Another File", command=monitor_another_file, bg="blue", fg="white", width=20).pack(pady=5)

# ---------------- START MONITOR ----------------
def start_monitor(root: tk.Tk):
    file_path = select_file(root)
    if file_path:
        monitor = FileMonitor(file_path, root)
        monitor_control_dialog(root, monitor)

# ---------------- MAIN ----------------
def main():
    global selected_voice
    root = tk.Tk()
    root.title("Arduino AI Assistant")
    root.geometry("450x250")

    tk.Label(root, text="Arduino AI Code Fixer", font=("Arial", 14, "bold")).pack(pady=10)

    # --- Voice selection ---
    tk.Label(root, text="Select Voice:", font=("Arial", 12)).pack()
    voice_options = ["en-IN-NeerjaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "en-GB-LibbyNeural"]
    voice_dropdown = ttk.Combobox(root, values=voice_options, font=("Arial", 11))
    voice_dropdown.current(0)
    voice_dropdown.pack(pady=5)

    def set_voice():
        global selected_voice
        selected_voice = voice_dropdown.get()
        speak(f"Voice set to {selected_voice}")

    tk.Button(root, text="Set Voice", command=set_voice, font=("Arial", 12), bg="blue", fg="white").pack(pady=5)

    # --- Start Monitoring button ---
    tk.Button(root, text="Start Monitoring Arduino File", command=lambda: start_monitor(root),
              font=("Arial", 12), width=30).pack(pady=15)

    speak("Starting Arduino AI assistant for live monitoring.")
    root.mainloop()

if __name__ == "__main__":
    main()
