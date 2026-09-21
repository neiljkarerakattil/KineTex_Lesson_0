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

## Installation

1) Download the main.py file into a folder of your choice. It must be in a folder. Do not put it directly into the Downloads folder, as a lot of other files will be generated in this folder.

2) Download requirements.txt and put it into the same folder

3) Create a virtual environment for this project (recommended):
* Open your terminal (macOS/Linux) or Command Prompt/PowerShell (Windows) and use cd to go to the directory where you want to store your project:
'''
cd path/to/your/project
'''
* Run the creation command. You can name your environment folder whatever you like, but .venv or venv are standard conventions:
'''
python3 -m venv .venv
'''
(use "python" instead of "python3" if using windows)

* Before you can use the environment, you must activate it. The command varies depending on your operating system and shell:
'''
source .venv/bin/activate
'''

4) Install Dependencies
* Run this line of code in the terminal with the virtual environment.
'''
pip install -r requirements.txt
'''

5) Run main.py 
'''
python3 main.py
'''

