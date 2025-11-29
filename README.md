🤖 Arduino AI Code Fixer with Voice Alerts

This project provides a real-time monitoring tool for Arduino (.ino) sketch files, leveraging Large Language Models (LLMs) like Google Gemini or OpenAI to automatically detect and fix common syntax or logical errors, with voice alerts for notifications.

It is designed to enhance the Arduino development workflow by catching mistakes immediately after you save your file, long before you attempt to compile.

✨ Features

Real-time File Monitoring: Watches a selected .ino file for changes every second.

AI Error Detection: Uses an LLM (Gemini or OpenAI) to quickly check the new code for errors.

Automatic Fixing: If an error is detected, a pop-up appears, offering to send the code to the AI for an automatic fix and rewrite the file.

Voice Notifications: Uses edge-tts for spoken alerts, informing the user about file changes, error detection, and successful fixes.

Dual LLM Support: Separate scripts (Gemini.py and Open AI.py) allow flexibility in choosing your preferred AI backend.

🛠️ Prerequisites

Before running the script, ensure you have Python 3.x installed and a working API key for your chosen AI service (Gemini or OpenAI).

Dependencies

Install the required Python packages using pip:

pip install google-genai openai pygame edge-tts


🚀 Setup and Installation

1. Configure API Keys

You must insert your API key into the respective Python file:

For Gemini: Open Gemini.py and replace "Api Key here" with your actual Gemini API key:

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"


For OpenAI: Open Open AI.py and replace "Your Api Key here" with your actual OpenAI API key:

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"


2. Run the Script

Choose the script for your desired AI backend and run it from your terminal:

Using Gemini:

python Gemini.py


Using OpenAI:

python "Open AI.py"


💡 Usage

Launch the Application: Run the chosen Python script (Gemini.py or Open AI.py).

Select Voice: Use the dropdown menu to choose your preferred voice for alerts. Click "Set Voice."

Start Monitoring: Click the "Start Monitoring Arduino File" button. A file selection dialog will appear.

Choose Your Sketch: Navigate to and select the .ino file you are actively editing.

Develop: As you write code and save changes to the .ino file:

The script will hash the file content and check for changes.

If a change is detected, it asks the AI if an error exists.

If the AI returns 'YES', a pop-up will appear with an audible alert ("Possible code issue detected.").

Fix: Click "Fix Code" in the pop-up to automatically send the current code to the AI for correction and rewrite the file with the fixed version.

⚙️ Configuration (Advanced)

Both Gemini.py and Open AI.py contain configurable settings at the top of the file:

Setting

Description

Default Value

CHECK_INTERVAL_MS

The frequency (in milliseconds) the script checks the file for changes.

1000 (1 second)

GEMINI_MODEL (Gemini only)

The Gemini model used for detection and fixing.

"gemini-2.5-flash"

OPENAI_MODEL (OpenAI only)

The OpenAI model used for detection and fixing.

"gpt-3.5-turbo"

🛑 Stopping the Monitor

Once monitoring has started, a "Monitor Control" dialog will appear.

Click "Stop Fixer" to terminate the current monitoring session and close the dialog.

Click "Monitor Another File" to stop the current session and immediately restart the file selection process.
