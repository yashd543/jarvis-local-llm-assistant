import requests
import speech_recognition as sr
import os
import re
import subprocess
import shutil
import urllib.parse

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2:2b"

SYSTEM_PROMPT = """
You are Jarvis, a smart AI assistant for Yash Dixit.
Be friendly, short, and helpful.
Reply in plain text only. Do not use emojis.
"""

chat_history = []


def clean_for_speech(text: str) -> str:
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # remove emojis/unicode
    text = text.replace("*", "").replace("#", "").replace("`", "")
    return text.strip()


def speak(text):
    print("\nJARVIS:", text)

    safe_text = clean_for_speech(text)
    safe_text = safe_text.replace("'", "").replace('"', "")

    os.system(
        f'powershell -Command "Add-Type -AssemblyName System.Speech; '
        f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{safe_text}\')"'
    )


def listen(timeout=8, phrase_time_limit=10):
    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("\n🎤 Listening...")
        r.adjust_for_ambient_noise(source, duration=0.6)

        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return ""

    try:
        query = r.recognize_google(audio)
        print("YOU:", query)
        return query.lower().strip()

    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Speech recognition service is not available.")
        return ""


def ask_ollama(text):
    global chat_history

    chat_history.append(f"User: {text}")
    chat_history = chat_history[-4:]  # speed

    full_prompt = SYSTEM_PROMPT.strip() + "\n\n" + "\n".join(chat_history) + "\nJarvis:"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "num_predict": 140,
            "temperature": 0.6
        }
    }

    print("⚡ Thinking (Ollama)...")
    res = requests.post(OLLAMA_URL, json=payload)
    res.raise_for_status()

    reply = res.json()["response"].strip()

    chat_history.append(f"Jarvis: {reply}")
    chat_history = chat_history[-4:]

    return reply


def open_url(url: str):
    # Most reliable way on Windows
    subprocess.Popen(["cmd", "/c", "start", "", url])


def run_command(command: str) -> bool:
    command = command.lower().strip()
    print("DEBUG COMMAND:", command)

    # -------- OPEN CHROME --------
    if "open chrome" in command:
        speak("Opening Chrome.")

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                print("DEBUG: Chrome path found:", path)
                subprocess.Popen([path])
                return True

        speak("Chrome not found. Opening Google in default browser.")
        open_url("https://google.com")
        return True

    # -------- OPEN VS CODE --------
    if "open vscode" in command or "open vs code" in command:
        speak("Opening VS Code.")

        vscode_paths = [
            rf"C:\Users\{os.getenv('USERNAME')}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]

        for path in vscode_paths:
            if os.path.exists(path):
                print("DEBUG: VS Code path found:", path)
                subprocess.Popen([path])
                return True

        if shutil.which("code"):
            print("DEBUG: VS Code found in PATH")
            subprocess.Popen(["code"])
            return True

        speak("VS Code not found.")
        return True

    # -------- OPEN WEBSITES --------
    if "open youtube" in command:
        speak("Opening YouTube.")
        open_url("https://youtube.com")
        return True

    if "open google" in command:
        speak("Opening Google.")
        open_url("https://google.com")
        return True

    if "open github" in command:
        speak("Opening GitHub.")
        open_url("https://github.com")
        return True

    # -------- SEARCH --------
    if command.startswith("search "):
        query = command.replace("search", "", 1).strip()
        if query:
            speak(f"Searching for {query}")
            q = urllib.parse.quote(query)
            open_url(f"https://www.google.com/search?q={q}")
            return True

    return False


def main():
    speak("Hello Yash. Say hey Jarvis followed by your command.")

    while True:
        heard = listen(timeout=8, phrase_time_limit=10)

        if heard == "":
            continue

        if "shutdown jarvis" in heard or heard in ["exit", "stop", "bye"]:
            speak("Goodbye Yash. Jarvis signing off.")
            break

        if "hey jarvis" not in heard:
            continue

        command = heard.replace("hey jarvis", "").strip()
        command = command.lower().strip()

        if command == "":
            speak("Yes Yash, tell me.")
            continue

        # Instant commands
        if run_command(command):
            continue

        # Otherwise AI
        reply = ask_ollama(command)
        speak(reply)


if __name__ == "__main__":
    main()