import hashlib
import threading
import tempfile
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from google import genai
from google.genai.errors import APIError
import asyncio
import edge_tts
import pygame
import time

# ---------------- SETTINGS ----------------
# !!! REPLACE WITH YOUR ACTUAL GEMINI API KEY !!!
GEMINI_API_KEY = "Api Key here"
CHECK_INTERVAL_MS = 1000 # 1 second polling for real-time detection

# ---------------- INITIALIZE GEMINI CLIENT ----------------
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"[GEMINI CLIENT ERROR] Could not initialize the client: {e}")
    # In a real application, you might exit or disable AI features here.

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
            if not client:
                 callback(code) # Use original code if client failed to init
                 return

            speak("Fixing code using AI, please wait.")
            
            # --- GEMINI API Call for Fixing ---
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {"role": "user", "parts": [{"text": f"You are an expert Arduino code fixer. Correct syntax and logic errors while keeping structure unchanged. Do not add any extra text, only return the corrected code. Fix the following code:\n\n{code}"}]}
                ]
            )
            
            fixed_code = response.text
            callback(fixed_code)
            
        except APIError as e:
            print(f"[AI FIX API ERROR]: {e}")
            messagebox.showerror("AI Error", f"Gemini API Error during fix: {e}")
            callback(code) # Return original code on API failure
        except Exception as e:
            print(f"[AI FIX ERROR]: {e}")
            callback(code)

    threading.Thread(target=ai_thread, daemon=True).start()

# ---------------- POPUP ----------------
def show_fix_popup(file_path: Path, old_code: str, root: tk.Tk):
    def apply_fix():
        def after_fix(fixed_code):
            if file_path.exists():
                # Hash check to prevent continuous fixing loop if file write triggers monitor
                new_hash = hashlib.md5(fixed_code.encode('utf-8')).hexdigest()
                global monitor_instance
                if monitor_instance:
                    monitor_instance.last_hash = new_hash
                
                file_path.write_text(fixed_code, encoding="utf-8")
                speak("The code has been fixed successfully.")
                messagebox.showinfo("Fixed", "AI has corrected the file.")
            popup.destroy()

        # Pass the global monitor instance's code hash to the callback
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
                            if not client:
                                after_ai_check(False) # Assume no error if client failed to init
                                return

                            # --- GEMINI API Call for Detection ---
                            detection_prompt = (
                                "You are an expert Arduino code checker. Detect if the code has any syntax or logical errors. "
                                "Return 'YES' if errors exist, 'NO' if code is correct. "
                                "ONLY return 'YES' or 'NO' and nothing else. Code to check:\n\n"
                                f"{code}"
                            )
                            
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[
                                    {"role": "user", "parts": [{"text": detection_prompt}]}
                                ]
                            )
                            
                            answer = response.text.strip().upper()
                            after_ai_check("YES" in answer)
                            
                        except APIError as e:
                            print(f"[AI DETECT API ERROR] {e}")
                            after_ai_check(False) # Treat API error as no error detected for safety
                        except Exception as e:
                            print(f"[AI DETECT ERROR] {e}")
                            after_ai_check(False)

                    threading.Thread(target=ai_detect_thread, daemon=True).start()

                except Exception as e:
                    print(f"[FILE READ ERROR] {e}")
            else:
                # print("[MONITOR] File hash unchanged, skipping check.")
                pass
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
    dlg.geometry("300x160")
    dlg.protocol("WM_DELETE_WINDOW", lambda: None) # Disable closing with X button
    
    tk.Label(dlg, text="Real-time monitoring active:", font=("Arial", 12)).pack(pady=5)
    tk.Label(dlg, text=f"{monitor.file_path.name}", font=("Courier", 10)).pack()

    def stop_monitor():
        global monitor_instance
        monitor_instance.stop_monitor()
        monitor_instance = None
        dlg.destroy()

    def monitor_another_file():
        global monitor_instance
        monitor_instance.stop_monitor()
        monitor_instance = None
        dlg.destroy()
        start_monitor(root)

    ttk.Button(dlg, text="Stop Fixer", command=stop_monitor, width=30).pack(pady=5)
    ttk.Button(dlg, text="Monitor Another File", command=monitor_another_file, width=30).pack(pady=5)

# ---------------- START MONITOR ----------------
monitor_instance = None # Global variable to hold the monitor instance

def start_monitor(root: tk.Tk):
    global monitor_instance
    if monitor_instance:
        messagebox.showwarning("Already Monitoring", "Please stop the current monitoring session before starting a new one.")
        return
        
    file_path = select_file(root)
    if file_path:
        monitor_instance = FileMonitor(file_path, root)
        monitor_control_dialog(root, monitor_instance)

# ---------------- MAIN ----------------
def main():
    global selected_voice
    root = tk.Tk()
    root.title("Arduino AI Assistant (Gemini)")
    root.geometry("450x300")
    
    # Set a modern style for the ttk widgets
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TButton', font=('Arial', 11), padding=10)
    style.configure('TCombobox', font=('Arial', 11), padding=5)

    tk.Label(root, text="Arduino AI Code Fixer (Gemini)", font=("Arial", 14, "bold")).pack(pady=10)

    # --- Voice selection ---
    tk.Label(root, text="Select Voice:", font=("Arial", 12)).pack()
    voice_options = ["en-IN-NeerjaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "en-GB-LibbyNeural"]
    voice_dropdown = ttk.Combobox(root, values=voice_options, font=("Arial", 11), state="readonly")
    voice_dropdown.set(selected_voice)
    voice_dropdown.pack(pady=5)

    def set_voice():
        global selected_voice
        selected_voice = voice_dropdown.get()
        speak(f"Voice set to {selected_voice}")

    ttk.Button(root, text="Set Voice", command=set_voice).pack(pady=5)

    # --- Start Monitoring button ---
    ttk.Button(root, text="Start Monitoring Arduino File", command=lambda: start_monitor(root)).pack(pady=15)

    speak("Starting Arduino AI assistant for live monitoring.")
    root.mainloop()

if __name__ == "__main__":
    main()
