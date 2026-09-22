# KineTex_Lesson

Kinetex_lesson is a video creation tool that uses a latex style input to create intuitive video. 

## Description
The main idea is to be able to convert simple latex documents into voiced presentations that are accessible to viewers while still having rich math.

The main features currently implemented are that latex style math is rendered and even voiced to a reasonable degree. The current version of Kinetex_Lesson supports figures, tables, and lists, as well as some video features like a voiceover, pause, and explanations. 

## Dependancies

### Python 3 is REQUIRED 

At a minimum, these are the dependencies that can be installed manually. However, the installation steps will attempt to install all these dependencies in a more automated way. This only needs to be used if the installer fails.

* manim
* manim_voiceover
* kokoro_mv
* accesible_math_reader
* numpy
* pyside6

## Important

* When the app runs, it might give a warning that SoX is missing. SoX is not required, but it can be installed to remove the Warning. If installed, SoX must be added to PATH manually.

## Installation & Setup

Follow these steps to set up the project on your local machine:

1. **Prepare your project folder:**
   Create a dedicated folder for this project and place both `main.py` and `requirements.txt` inside it. 
   *(Note: Avoid running this directly in your Downloads folder, as the application will generate additional files during execution).*

2. **Navigate to your project directory:**
   Open your terminal (macOS/Linux) or Command Prompt/PowerShell (Windows) and run:
   ```bash
   cd path/to/your/project
   ```

3. **Create a virtual environment:**
   Run the environment creation command for your operating system:
   * **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     ```
   * **Windows:**
     ```cmd
     python -m venv .venv
     ```

4. **Activate the virtual environment:**
   You must activate the environment before installing dependencies or running the script:
   * **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```
   * **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   *(You will know it worked when you see `(.venv)` appear at the beginning of your terminal prompt).*

5. **Install dependencies:**
   With the virtual environment activated, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Executing the Program

Whenever you want to run the program (including the first time), open your terminal and follow these steps. 

*Note: The first time you run the application, an active internet connection is required to download package assets.*

1. **Navigate to the project folder:**
   ```bash
   cd path/to/your/project
   ```

2. **Activate the virtual environment:**
   * **macOS / Linux:** `source .venv/bin/activate`
   * **Windows (Cmd):** `.venv\Scripts\activate.bat`
   * **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`

3. **Run the script:**
   * **macOS / Linux:**
     ```bash
     python3 main.py
     ```
   * **Windows:**
     ```cmd
     python main.py
     ```

