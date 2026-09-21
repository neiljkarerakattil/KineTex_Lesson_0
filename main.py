#combined main 
#LatexParser Imports
import re
from dataclasses import dataclass 
from typing import List     
from typing import Union as TUnion 

#Manim_Render Imports

from manim import *

from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
from kokoro_mv import KokoroService
from manim_voiceover.services.recorder import RecorderService

from accessible_math_reader import MathReader, VerbosityLevel

import numpy as np

#KineTex Imports

import sys,os
import json
from pathlib import Path
from PySide6.QtGui import QFont, QKeySequence, QAction
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPlainTextEdit, QDialog,
                               QVBoxLayout, QHBoxLayout, QCheckBox, QSpinBox, QProgressDialog,
                               QLabel, QPushButton, QFontComboBox, QMenuBar, QProgressBar, 
                               QFileDialog, QMessageBox, QComboBox, QWidget, QLineEdit)


# =========================================================
# AST NODE TYPES
# =========================================================

@dataclass
class Title:
    text: str
    modifier: str = ""

@dataclass
class Section:
    text: str
    modifier: str = ""

@dataclass
class Subsection:
    text: str
    modifier: str = ""

@dataclass
class Body:
    text: str
    modifier: str = ""

@dataclass
class Pause:
    duration: float
    modifier: str = ""

@dataclass
class Clear:
    text: str
    modifier: str = ""

@dataclass
class Voiceover:
    text: str
    modifier: str = ""

@dataclass
class Usepackage:
    text: str
    modifier: str = ""

@dataclass
class Explanation:
    text: str
    modifier: str = ""

@dataclass
class Tabular:
    text: str
    args: str
    modifier: str = ""

@dataclass
class Figure:
    filename: str
    modifier: str = ""

@dataclass
class Equation:
    steps: List[str]
    modifier: str = ""
    #duration: float

@dataclass
class Itemize:
    text: str
    modifier: str = ""
    #duration: float

Node = TUnion[Title, Section, Subsection, Body, Pause, Clear, Voiceover, Usepackage, Explanation, Tabular, Figure, Equation, Itemize]


# =========================================================
# LatexParser
# =========================================================

class LatexInterpreter:

    def __init__(self):

        #self.begin_env = re.compile(r"\\begin(\!)?\{([^}]*)\}(.*)")
        self.begin_env = re.compile(r"\\begin([*!+\-]*)\{([^}]*)\}(.*)") #searches for modifiers: *!+\- 
        self.end_env = re.compile(r"\\end\{(.+?)\}")
        self.command = re.compile(r"\\(\w+)([*!+\-]*)\{(.*?)\}")
        self.comment = re.compile(r"(?<!\\)%")

    def strip_comment(self, line):
        backslashes = 0

        for i, c in enumerate(line):

            if c == "\\":
                backslashes += 1
                continue

            if c == "%":
                if backslashes % 2 == 0:
                    return line[:i]

            backslashes = 0

        return line

    def parse(self, filename: str) -> List[Node]:

        nodes: List[Node] = []

        env = None
        buffer: List[str] = []

        with open(filename, "r", encoding="utf-8") as f:

            for raw_line in f:
                line = self.strip_comment(raw_line).rstrip()

                if not line:
                    continue

                # =================================================
                # BEGIN ENVIRONMENT
                # =================================================
                begin = self.begin_env.fullmatch(line)
                if begin:
                    modifier = begin.group(1) #checks for the presence of "!"
                    env = begin.group(2)
                    args = begin.group(3).strip()

                    buffer = []
                    continue

                # =================================================
                # END ENVIRONMENT
                # =================================================
                end = self.end_env.fullmatch(line)
                if end:

                    env_name = end.group(1)

                    if env_name != env:
                        raise ValueError(
                            f"Mismatched environment: expected {env}, got {env_name}"
                        )

                    if env == "equation":
                        nodes.append(Equation(buffer.copy(),modifier))

                    elif env == "explanation":
                        nodes.append(Explanation("\n".join(buffer),modifier))

                    elif env == "tabular":
                        nodes.append(Tabular("\n".join(buffer), args, modifier))

                    elif env == "figure":
                        nodes.append(Figure("\n".join(buffer),modifier))
                    
                    elif env == "text":
                        nodes.append(Body("\n".join(buffer),modifier))

                    elif env == "itemize":
                        nodes.append(Itemize("\n".join(buffer),modifier))

                    else:
                        nodes.append(Explanation("\n".join(buffer),modifier))

                    env = None
                    buffer = []
                    args = None
                    modifier = None
                    continue

                # =================================================
                # INSIDE ENVIRONMENT
                # =================================================
                cmd = self.command.fullmatch(line)

                if env is not None:
                    
                    if cmd:

                        name = cmd.group(1)
                        modifier = cmd.group(2) or ""
                        arg = cmd.group(3)

                        if name == "caption":
                            nodes.append(Explanation(arg, modifier))
                            continue
                        
                        # ignore unknown commands inside environments
                        buffer.append(line)
                        continue
                    
                    buffer.append(line)
                    continue

                # =================================================
                # OUTSIDE ENVIRONMENT COMMANDS
                # =================================================

                elif cmd:
                    name = cmd.group(1) 
                    modifier = cmd.group(2) or ""
                    arg = cmd.group(3) or ""

                    if name == "title":
                        nodes.append(Title(arg,modifier))
                        continue

                    elif name == "section":
                        nodes.append(Section(arg,modifier))
                        continue

                    elif name == "usepackage":
                        nodes.append(Usepackage(arg,modifier))
                        continue

                    elif name == "subsection":
                        nodes.append(Subsection(arg,modifier))
                        continue

                    elif name == "pause":
                        nodes.append(Pause(float(arg),modifier))
                        continue

                    elif name == "clear":
                        nodes.append(Clear(arg,modifier))

                    elif name == "voiceover":
                        nodes.append(Voiceover(arg,modifier))
                        continue
                    
                    elif name == "text":
                        nodes.append(Body(arg,modifier))
                        continue

                    else:
                        nodes.append(Body(line,modifier))
                        continue

                else:
                    nodes.append(Body(line,modifier = ""))
                    continue


                # =================================================
                # FALLBACK TEXT (optional)
                # =================================================
                #buffer.append(line)

        return nodes

#===========================================================
# Manim Render
#===========================================================

    
class LatexRender(VoiceoverScene):

    def __init__(self, inputFilename="Example video.txt", theme="NCSU", **kwargs):

        self.inputFilename = inputFilename
        self.theme = theme

        #call the parent Scene initialization
        super().__init__(**kwargs)


    def initialize_parser(self):

        parser = LatexInterpreter()
        nodes = parser.parse(self.inputFilename)

        return nodes


    def initialize_scene(self):

        self.protected_header_items = []

        if self.theme == "NCSU":

            self.header_bar = Rectangle(
                width=config.frame_width, 
                height=0.2, 
                fill_color="#CC0000", 
                fill_opacity=1.0, 
                stroke_width=0
            )
            self.header_bar.to_edge(UP, buff=0)

            self.add(self.header_bar) 
            self.protected_header_items.append(self.header_bar)


        required_packages = [r"""
            \usepackage{amsmath}
            \renewcommand{\labelitemi}{$\bullet$}
            \providecommand{\e}[1]{\ensuremath{\times 10^{#1}}}
            """
        ]
        for pkg in required_packages:
            config.tex_template.add_to_preamble(pkg)

    def initialize_variables(self):

        self.current_equation = None
        self.current_text = None
        self.current_paragraph = None

        self.title = None
        self.section = None
        self.section_text = None
        self.subsection = None

        self.subsection_num = 0
        self.section_num = 0

    def initialize_voiceover(self, muteVoiceover = False, autoVoiceover = True, recordVoiceover = False):
        self.muteVoiceover = muteVoiceover #if True, all voiceovers are muted (not implemented)
        self.autoVoiceover = autoVoiceover #if false, voiceovers are only generated by voiceover commands
        self.recordVoiceover = recordVoiceover and not muteVoiceover
        self.voiceoverBuffer = 1

        self.reader = MathReader()
        self.reader.set_verbosity(VerbosityLevel.CONCISE)

        if self.muteVoiceover:
            self.set_speech_service(GTTSService(lang="en", tld="com"))
        elif self.autoVoiceover :
            self.set_speech_service(KokoroService(voice="af_sarah", lang="en-us"))
            #self.set_speech_service(GTTSService(lang="en", tld="com"))
        elif recordVoiceover:
            self.set_speech_service(RecorderService())

        

    def scaleToFit(self,object,area=[0.4,1]):
        #Adjust size to fit on screen
        max_width = config.frame_width*area[0] - 0.5
        max_height = config.frame_height*area[1] - 0.5

        if object.width > max_width:
            object.scale(max_width / object.width)

        if object.height > max_height:
            object.scale(max_height / object.height)

        return object

    def prepare_voiceover(self, text):
        text = text.replace("\n", " ")

        spoken = self.reader.to_speech(text)

        return spoken

    def cmdUsepackage(self, arg, modifier = ""): 
        config.tex_template.add_to_preamble(arg)

    def cmdPause(self, arg, modifier = ""):
        print(f"###Cmd_Pse: {float(arg)}")
        self.wait(float(arg))

        

    def cmdClear(self, arg, modifier = ""):
        if arg == "" or arg == "*":
            self.play(*[FadeOut(mob, run_time = 0.2) for mob in self.mobjects])
            self.remove(*[mob for mob in self.mobjects if mob not in self.protected_header_items])
            self.section = None
            self.subsection = None
            self.current_text = None
            self.current_equation = None
            self.current_paragraph = None

        else:
            # Parse the input string into a list of names
            items_to_clear = [item.strip() for item in arg.split(",")]

            # Map the string names to their corresponding self.attribute names
            mapping = {
                "title": "title",
                "section": "section",
                "subsection": "subsection",
                "paragraph": "current_paragraph",
                "itemize": "current_paragraph",
                "equation": "current_equation",
                "explanation": "current_text",
                "table": "current_equation",
                "figure": "current_equation"
            }

            # Separate out valid mobjects and track which attributes need resetting
            clear_animations = []
            attributes_to_reset = []

            for item in items_to_clear:
                if item in mapping:
                    attr_name = mapping[item]
                    mobject = getattr(self, attr_name, None)
                    
                    # Only animate if the object exists and isn't already None
                    if mobject is not None:
                        clear_animations.append(FadeOut(mobject))
                        attributes_to_reset.append(attr_name)
                else:
                    print(f"Item named '{item}' not found. Cannot be cleared")

            # Play all fade-out animations at the same time
            if clear_animations:
                self.play(*clear_animations)

            # Reset the respective attributes to None after the animation finishes
            for attr_name in attributes_to_reset:
                setattr(self, attr_name, None)

            
            
            self.wait_for_voiceover()

            self.wait(self.voiceoverBuffer)
            



    def cmdVoiceover(self, text, modifier = ""):

        self.wait_for_voiceover()
        self.wait(self.voiceoverBuffer/2)

        if not self.muteVoiceover:
            self.add_voiceover_text(text)

    def playEquation(self, step, modifier = ""):
        print(f"###Env_Eqn: {step}")
        equation = MathTex(step)
        self.scaleToFit(equation, [0.5,0.5])

        if self.current_paragraph:
                equation.shift(3*LEFT)

        if "!" in modifier:
            print("spoken equations are currently experimental")
            spoken = self.prepare_voiceover(step)
            self.cmdVoiceover(spoken)

        if self.current_equation is None:
            self.play(Write(equation))
        else:
            self.play(
                FadeTransform(
                    self.current_equation,
                    equation
                )
            )

        self.wait(1)

        self.wait_for_voiceover()
        
        self.current_equation = equation
    
    def playExplanation(self, text, modifier = ""):
        print(f"###Env_Exp: {text}")
        explanation = Tex(rf"\begin{{minipage}}{{15em}}{text}\end{{minipage}}").scale(1).shift(3 * DOWN)
        self.scaleToFit(explanation,[0.5,0.5])

        if "!" in modifier:
            self.cmdVoiceover(text)
    
        if self.current_paragraph:
            explanation.shift(3*LEFT)

        if self.current_text is None:
            self.play(Write(explanation))
        else:
            self.play(Unwrite(self.current_text, run_time=0.5, reverse=False),Write(explanation))

        self.wait(1)

        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)
        
        self.current_text = explanation

    def playTable(self, text, args, modifier = ""):
        print(f"###Env_Tab: {args}")
        table_text = f"\\begin{{tabular}}{args}\n{text}\n\\end{{tabular}}"
        
        equation = Tex(rf"\begin{{minipage}}{{15em}}{table_text}\end{{minipage}}").scale(1)

        if self.current_paragraph:
            self.scaleToFit(equation,[0.5,0.7])
            equation.shift(3*LEFT)
        else:
            self.scaleToFit(equation,[1,0.7])

        if self.current_equation is None:
            self.play(Write(equation))
        else:
            self.play(
                ReplacementTransform(
                    self.current_equation,
                    equation
                )
            )

        self.wait(1)
        
        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)

        self.current_equation = equation

    def playFigure(self, filename, modifier = ""):
        print(f"###Env_Figure: {filename}")
        
        equation = ImageMobject(filename)

        if "!" in modifier:
            print("spoken equations are currently experimental")
            self.cmdVoiceover(filename)

        if self.current_paragraph:
            self.scaleToFit(equation,[0.5,0.7])
            equation.shift(3*LEFT)
        else:
            self.scaleToFit(equation,[1,0.7])

        if self.current_equation is None:
            self.play(FadeIn(equation))
        else:
            self.play(
                FadeOut(self.current_equation),
                FadeIn(equation)
            )
        
        self.wait(1)

        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)

        self.current_equation = equation

    def playParagraph(self, text, modifier = ""):
        print(f"###Cmd_Pse: {"Writing Pragraph"}")

        width = 15
        max_height = config.frame_height*2 - 1

        while True:
            paragraph = Tex(
                rf"\begin{{minipage}}{{{width}em}}{text}\end{{minipage}}"
            )
            print(f"width = {width}")
            if paragraph.height < max_height:
                text_speed = (width - 15)/15 + 1
                break
            width += 2
            if width >= 30:
                print("error text too long")
                print (f"width = {width}")
                break

        #paragraph = Tex(rf"\begin{{minipage}}{{20em}}{text}\end{{minipage}}")
        self.scaleToFit(paragraph, [0.4,1])
        #paragraph.to_edge(RIGHT, buff=0.5)
        paragraph.shift(3 * RIGHT)

        if self.current_paragraph is None:
            
            animations = []

            if self.current_text is not None:
                animations.append(
                    self.current_text.animate.shift(3*LEFT)
                )

            if self.current_equation is not None:
                target = self.current_equation.copy()
                self.scaleToFit(target, [0.4,0.5])
                target.shift(3*LEFT)
                animations.append(
                    ReplacementTransform(self.current_equation,target)
                )
                self.current_equation = target

            if animations:
                self.play(*animations)
        
        if "!" in modifier:
            self.cmdVoiceover(text)

        if self.current_paragraph is None:
            self.play(Write(paragraph))
        else:
            self.play(Unwrite(self.current_paragraph, run_time=0.5, reverse=False))
            self.wait(0.1)
            self.play(Write(paragraph))

        self.wait(1)

        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)
        
        self.current_paragraph = paragraph

    def playTitle(self, text, modifier = ""):
        print(f"###Cmd_Ttl: {text}")

        if "!" in modifier:
            self.cmdVoiceover(text)

        self.remove(*[mob for mob in self.mobjects if mob not in self.protected_header_items])
        self.section = None
        self.subsection = None
        self.current_text = None
        self.current_equation = None
        self.current_paragraph = None

        if self.title == None:
            self.title = Tex(text)
            self.scaleToFit(self.title,[1,1])
            self.play(Write(self.title))
            self.wait(self.voiceoverBuffer)
            self.wait_for_voiceover()
            self.play(Unwrite(self.title))
        else:
            new_title = Tex(text)
            self.scaleToFit(new_title,[1,1])
            self.play(Write(new_title))
            self.wait(self.voiceoverBuffer)
            self.wait_for_voiceover()
            self.play(Unwrite(new_title))
            self.title = new_title

    
    def playSection(self, text, modifier = ""):
        print(f"###Cmd_Sec: {text}")
        self.section_num += 1
        self.subsection_num = 0
        self.section_text = text

        if "!" in modifier:
            self.cmdVoiceover(text=("section " + str(self.section_num) + " "+ str(text)))

        self.remove(*[mob for mob in self.mobjects if mob not in self.protected_header_items])
        self.subsection = None
        self.current_text = None
        self.current_equation = None
        self.current_paragraph = None

        if self.section == None:
            self.section = Tex(str(self.section_num) + "." + str(self.subsection_num)+ " " + str(self.section_text))
            self.play(Write(self.section))
            self.wait(1)
            self.wait_for_voiceover()
            self.play(self.section.animate.scale(0.8).to_edge(UL))
        else:
            new_section = Tex(str(self.section_num) + "." + str(self.subsection_num)+ " " + str(self.section_text))
            self.play(Write(new_section))
            self.wait(1)
            self.wait_for_voiceover()
            self.play(new_section.animate.scale(0.8).to_edge(UL))
            self.section = new_section

    def playSubsection(self,text, modifier = ""):
        print(f"###Cmd_Ssc: {text}")

        
        if self.section == None:
                raise ValueError(
                    "Section needs to be assigned before the subsection"
                    )
        else:
            if "*" not in modifier:
                self.subsection_num += 1

            new_section = Tex(str(self.section_num) + "." + str(self.subsection_num)+ " " + str(self.section_text)).scale(0.8).to_edge(UL)
            self.play(TransformMatchingTex(self.section,new_section))
            self.section = new_section
            
        
        new_subsection = Tex(str(text)).scale(0.5).to_edge(UL)
        new_subsection.shift(DOWN*0.5)

        if "!" in modifier:
            self.cmdVoiceover(text= ("section " + str(self.section_num) + " point " + str(self.subsection_num)+ " " + str(text)))
        
        if self.subsection == None:
            self.play(Write(new_subsection))
        else:
            self.play(Unwrite(self.subsection, run_time=0.5, reverse=False),Write(new_subsection))
        
        self.wait(1)

        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)

        self.subsection = new_subsection

    def playItemizeLatex(self, text, modifier):
        print(f"###Cmd_Pse: {"Writing Itemize"}")

        width = 15
        max_height = config.frame_height*2 - 1

        while True:
            paragraph = Tex(
                rf"""
                \begin{{minipage}}{{{width}em}}
                \begin{{itemize}}
                {text}
                \end{{itemize}}
                \end{{minipage}}
                """
            )

            paragraph = Tex(
                rf"""
                \begin{{itemize}}
                {text}
                \end{{itemize}}
                """
            )
            
            print(f"width = {width}")
            if paragraph.height < max_height:
                text_speed = (width - 15)/15 + 1
                break
            width += 2
            if width >= 30:
                print("error text too long")
                print (f"width = {width}")
                break

        #paragraph = Tex(rf"\begin{{minipage}}{{20em}}{text}\end{{minipage}}")
        self.scaleToFit(paragraph, [0.4,1])
        #paragraph.to_edge(RIGHT, buff=0.5)
        paragraph.shift(3 * RIGHT)

        if self.current_paragraph is None:
            
            animations = []

            if self.current_text is not None:
                animations.append(
                    self.current_text.animate.shift(3*LEFT)
                )

            if self.current_equation is not None:
                target = self.current_equation.copy()
                self.scaleToFit(target, [0.4,0.5])
                target.shift(3*LEFT)
                animations.append(
                    ReplacementTransform(self.current_equation,target)
                )
                self.current_equation = target

            if animations:
                self.play(*animations)

        if "!" in modifier:

            voicebuffer = []
            pattern = re.compile(
                r'\\item(?:\[([^\]]*)\])?\s*(.*?)(?=\\item|$)', #search for item content until next \item
                re.DOTALL
            )
            for m in pattern.finditer(text):
                label = m.group(1) or ""
                item_text = m.group(2).strip()

                voicebuffer.append(item_text)

            voiceitems = ".  . ".join(voicebuffer)

            self.cmdVoiceover(voiceitems)
            

        if self.current_paragraph is None:
            self.play(Write(paragraph))
        else:
            self.play(Unwrite(self.current_paragraph,run_time=0.5, reverse=False))
            self.wait(0.1)
            self.play(Write(paragraph))

        self.wait(1)

        self.wait_for_voiceover()

        self.wait(self.voiceoverBuffer)
        
        self.current_paragraph = paragraph


    def construct(self):

        nodes = self.initialize_parser()
        self.initialize_scene()
        self.initialize_variables()
        self.initialize_voiceover()
        

        for node in nodes:
            print(node)

        for node in nodes:

            if isinstance(node, Equation):

                for step in node.steps:

                    cmd = re.match(r"\\(\w+)([*!+\-]*)\{(.*?)\}", step)

                    if cmd:

                        name = cmd.group(1)
                        modifier = cmd.group(2) or ""
                        arg = cmd.group(3)

                        if name == "pause":
                            self.cmdPause(arg,modifier)
                            continue

                        elif name == "caption":
                            self.playExplanation(arg,modifier)
                            continue

                        elif name == "label":
                            self.playExplanation(arg,modifier)
                            continue

                        elif name == "text":
                            self.playExplanation(arg,modifier)
                            continue

                        elif name == "voiceover":
                            self.cmdVoiceover(arg,modifier)
                            continue

                        else:
                            self.playEquation(step,node.modifier)
                            continue
                    
                    else:
                        self.playEquation(step,node.modifier)

            elif isinstance(node, Itemize):
                self.playItemizeLatex(node.text,node.modifier)

            elif isinstance(node, Explanation):
                self.playExplanation(node.text,node.modifier)

            elif isinstance(node, Usepackage):
                self.cmdUsepackage(node.text,node.modifier)

            elif isinstance(node, Tabular):
                self.playTable(node.text,node.args,node.modifier)

            elif isinstance(node, Figure):
                self.playFigure(node.filename,node.modifier)

            elif isinstance(node, Body):
                self.playParagraph(node.text,node.modifier)

            elif isinstance(node, Pause):
                self.cmdPause(node.duration,node.modifier)

            elif isinstance(node, Clear):
                self.cmdClear(node.text,node.modifier)

            elif isinstance(node, Voiceover):
                self.cmdVoiceover(node.text,node.modifier)

            elif isinstance(node, Title):
                self.playTitle(node.text,node.modifier) 

            elif isinstance(node, Section):
                self.playSection(node.text,node.modifier)

            elif isinstance(node, Subsection):
                self.playSubsection(node.text,node.modifier)

            else:
                print("Parser Encoding Error")

def render_manim():
    inputFilename = "New Text Document.txt"
    outputFilename = inputFilename.removesuffix(".txt")
    
    config.output_file = outputFilename
    
    config.preview = True          # Corresponds to '-p'
    config.quality = "high_quality" # Corresponds to 'ql' (480p, 15fps)
    config.disable_caching = False  # Corresponds to '--disable_caching'

    theme = "NCSU"

    if theme == "NCSU":
    
        config.background_color = WHITE
    
        Text.set_default(color=BLACK)
        Tex.set_default(color=BLACK, stroke_color=BLACK, background_stroke_opacity=0.0)
        MathTex.set_default(color=BLACK, stroke_color=BLACK, background_stroke_opacity=0.0)
    
    scene = LatexRender(inputFilename=inputFilename, theme = theme)
    scene.render()

def render_from_UI(inputFile, outputFile, settings):
    inputFilename = inputFile
    outputFilename = outputFile
    
    config.output_file = outputFilename
    
    config.preview = settings["preview"]         # Corresponds to '-p'
    config.quality = settings["quality"] # Corresponds to 'ql' (480p, 15fps)
    config.disable_caching = settings["disable_caching"]  # Corresponds to '--disable_caching'

    if settings["theme"] == "NCSU":

        config.background_color = WHITE

        Text.set_default(color=BLACK)
        Tex.set_default(color=BLACK, stroke_color=BLACK, background_stroke_opacity=0.0)
        MathTex.set_default(color=BLACK, stroke_color=BLACK, background_stroke_opacity=0.0)

    scene = LatexRender(inputFilename=inputFilename, theme = settings["theme"])
    scene.render()


# =========================================================
# KineTex Lesson
# =========================================================


def get_app_directory() -> Path:
    """Returns the base directory of the running script or compiled .exe file."""
    if getattr(sys, 'frozen', False):
        # Running as a compiled .exe (PyInstaller sets sys.frozen)
        return Path(sys.executable).parent
    else:
        # Running as a normal Python script
        return Path(__file__).resolve().parent

class ConfigManager:
    """Handles background loading, saving, and storing configuration state."""

    APP_DIR = get_app_directory()
    DEFAULT_VIDEO_DIR = APP_DIR / "output"

    DEFAULT_CONFIG = {
        "font_family": "Courier New",
        "font_size": 12,
        "line_wrapping": True,
        "quality" : "high_quality",
        "preview" : True,
        "disable_caching" : False,
        "theme" : "NCSU",
        "output_directory": str(DEFAULT_VIDEO_DIR)
    }

    def __init__(self):
        self.filepath = self.APP_DIR / "config.json"
        self.data = self.DEFAULT_CONFIG.copy()
        self.load()
        
        # 2. Automatically create the video directory if it doesn't exist
        self.ensure_output_dir_exists()

    def ensure_output_dir_exists(self):
        #Creates the configured output directory if it is missing
        try:
            target_path = Path(self.data["output_directory"])
            target_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Could not create output directory: {e}")

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except IOError:
            print("Failed to write config file.")

class PreferencesDialog(QDialog):
    """The Settings Window UI built entirely inside PySide6."""
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("Preferences")
        self.setModal(True)  # Lock focus to this window until closed
        
        layout = QVBoxLayout(self)

        # 1. Font Selection UI
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Family:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.config.data["font_family"]))
        font_layout.addWidget(self.font_combo)
        layout.addLayout(font_layout)

        # 2. Font Size UI
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Font Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(self.config.data["font_size"])
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)

        # 3. Line Wrap UI
        self.wrap_cb = QCheckBox("Enable Line Wrapping (default True)")
        self.wrap_cb.setChecked(self.config.data["line_wrapping"])
        layout.addWidget(self.wrap_cb)

        # 3. Preview UI
        self.prev_cb = QCheckBox("Enable Preview (default True)")
        self.prev_cb.setChecked(self.config.data["preview"])
        layout.addWidget(self.prev_cb)

        # 3. Preview UI
        self.cach_cb = QCheckBox("Disable Caching (default False)")
        self.cach_cb.setChecked(self.config.data["disable_caching"])
        layout.addWidget(self.cach_cb)

        # 3. Quality UI (Dropdown)
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Rendering Quality (default high)"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["production_quality","high_quality","low_quality","example_quality"])  # Added dropdown items [1]
        self.quality_combo.setCurrentText(self.config.data["quality"])  # Set initial state
        quality_layout.addWidget(self.quality_combo)
        layout.addLayout(quality_layout)

        # 3. Theme UI (Dropdown)
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme (default NCSU)"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["NCSU", "default"])  # Added dropdown items [1]
        self.theme_combo.setCurrentText(self.config.data["theme"])  # Set initial state
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # 4. Output Directory UI (Path + Browse Button)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Folder (Default 'output')"))
        
        self.dir_input = QLineEdit()
        self.dir_input.setText(self.config.data["output_directory"])
        self.dir_input.setReadOnly(True)  # Forces user to use the browser to avoid typos
        dir_layout.addWidget(self.dir_input)
        
        browse_btn = QPushButton("Open Output Folder...")
        browse_btn.clicked.connect(self.browse_folder)
        dir_layout.addWidget(browse_btn)
        
        layout.addLayout(dir_layout)

        

        # 4. Save/Cancel Actions
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Apply & Save")
        save_btn.clicked.connect(self.accept_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def browse_folder(self):
        """Opens native OS folder selection dialog."""
        selected_dir = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory", 
            self.dir_input.text()
        )
        if selected_dir:  # Ensure they didn't hit cancel
            self.dir_input.setText(selected_dir)

    def accept_settings(self):
        #Pushes UI choices back into the config manager and closes
        self.config.data["font_family"] = self.font_combo.currentFont().family()
        self.config.data["font_size"] = self.size_spin.value()
        self.config.data["line_wrapping"] = self.wrap_cb.isChecked()
        self.config.data["preview"] = self.prev_cb.isChecked()
        self.config.data["quality"] = self.quality_combo.currentText()
        self.config.data["disable_caching"] = self.cach_cb.isChecked()
        self.config.data["theme"] = self.theme_combo.currentText()

        self.config.data["output_directory"] = self.dir_input.text()
        self.config.ensure_output_dir_exists()

        
        self.config.save()  # Commit to file
        self.accept()       # Close dialog with positive result

class RenderWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, input_file, output_file, settings, cancel_checker):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.cancel_checker = cancel_checker # A function that returns True if user clicked cancel
        self.settings = settings

    def run(self):
        try:
            # Your exact rendering function runs safely in the background here
            render_from_UI(
                inputFile=self.input_file, 
                outputFile=self.output_file,
                settings = self.settings
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class CodeEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize background configuration manager
        self.config = ConfigManager()

        self.current_input_file = None
        self.current_output_file = None

        self.preview_config = self.config.data["preview"]
        self.quality_config = self.config.data["quality"]
        self.disable_caching_config = self.config.data["disable_caching"]
        
        self.theme_config = self.config.data["theme"]

        self.output_directory = Path(self.config.data["output_directory"])

        
        self.init_ui()

        

    def init_ui(self):
        # 1. Main Window Settings
        self.setWindowTitle("PySide6 Code Editor")
        self.resize(1000, 800)

        # 2. Setup Central Text Widget
        self.text_area = QPlainTextEdit(self)
        # Set a monospaced font ideal for coding
        font = QFont("Courier New", 12)
        self.text_area.setFont(font)
        # Configure tab distance to 4 spaces
        self.text_area.setTabStopDistance(40) 

        # Update text visuals
        font_name = self.config.data["font_family"]
        font_size = self.config.data["font_size"]
        self.text_area.setFont(QFont(font_name, font_size))
        
        # Update behaviors
        if self.config.data["line_wrapping"]:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        
        # 3. Setup Layout Container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0) # Edge-to-edge text look
        layout.addWidget(self.text_area)
        self.setCentralWidget(container)

        # Create a status label and progress bar
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False) # Hides percentage numbers for loading animation

        self.cancel_button = QPushButton("Cancel Render")
        self.cancel_button.setEnabled(False) # Disabled by default
        self.is_cancelled = False
        self.cancel_button.clicked.connect(self.request_render_cancel)
        self.statusBar().addWidget(self.cancel_button)

        self.statusBar().addWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.progress_bar)

        # 4. Create Menu System
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        # Action: New File
        new_action = QAction("&New", self, shortcut=QKeySequence.New, triggered=self.file_new)
        # Action: Open File
        open_action = QAction("&Open...", self, shortcut=QKeySequence.Open, triggered=self.file_open)
        # Action: Save File
        save_action = QAction("&Save", self, shortcut=QKeySequence.Save, triggered=self.file_save)
        # Action: Save As
        save_as_action = QAction("Save &As...", self, shortcut="Ctrl+Shift+S", triggered=self.file_save_as)
        # Action: Settings
        settings_actions = QAction("&Preferences...", self, shortcut="Ctrl+P", triggered=self.file_settings)
        # Action: Exit
        exit_action = QAction("&Exit", self, shortcut="Ctrl+Q", triggered=self.close)

        # Add all actions to the File menu
        file_menu.addActions([new_action, open_action, save_action, save_as_action, settings_actions])
        file_menu.addSeparator()
        #file_menu.add someAction(exit_action)

        run_menu = menubar.addMenu("&Run")

        # Action: Run Latex Manim
        self.run_action = QAction("&Run w/o Saving", self, shortcut="Ctrl+Shift+R", triggered=self.file_run)
        # Action: Save andRun Latex Manim
        self.save_run_action = QAction("Save and &Run", self, shortcut="Ctrl+R", triggered=self.file_save_run)
        # Action: Set Output File
        #output_file_action = QAction("&Output Settings", self, shortcut="Ctrl+O", triggered=self.run_output)

        #run_settings_action = QAction("&Settings", self, shortcut="Ctrl+Shift+R", triggered=self.run_settings)

        # Add all actions to the Run menu
        run_menu.addActions([self.save_run_action, self.run_action])#, output_file_action, run_settings_action])
        run_menu.addSeparator()

        #self.file_open()
        #filrune_menu.add someAction(exit_action)

    # --- File Operations ---
    def file_new(self):
        self.text_area.clear()
        self.current_input_file = None
        self.update_title()

    def file_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Input txt File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding='utf-8')
                self.text_area.setPlainText(content)
                self.current_input_file = file_path
                self.set_output_file()
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file:\n{str(e)}")

    def file_save(self):
        if self.current_input_file:
            try:
                Path(self.current_input_file).write_text(self.text_area.toPlainText(), encoding='utf-8')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")
        else:
            self.file_save_as()

    def file_save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Input As", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.current_input_file = file_path
            self.set_output_file()
            self.file_save()
            self.update_title()

    def file_save_run(self):

        try:
            self.file_save()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")
            return
        
        self.file_run()
        
        

    def file_run(self):

        try:
            self.set_output_file()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not run file:\n{str(e)}")
            return
        

        # 1. Update UI state to "Loading/Busy"
        self.status_label.setText("Rendering video... Please wait.")
        self.progress_bar.setRange(0, 0) # Trigger the looping animation

        self.run_action.setEnabled(False)
        self.save_run_action.setEnabled(False)

        self.cancel_button.setEnabled(True) 

        settings = {
            "preview": self.preview_config,
            "quality": self.quality_config,
            "disable_caching": self.disable_caching_config,
            "theme": self.theme_config
            }

        # 2. Worker setup (Pass a function to check if cancelled)
        self.render_thread = QThread()
        self.render_worker = RenderWorker(
            self.current_input_file, 
            self.current_output_file, 
            settings,
            cancel_checker=lambda: self.is_cancelled
        )
        self.render_worker.moveToThread(self.render_thread)

        # 3. Connection hooks
        self.render_thread.started.connect(self.render_worker.run)
        
        # Crucial: Quit the thread loop FIRST, then run the UI completion logic
        self.render_worker.finished.connect(self.render_thread.quit)
        self.render_worker.error.connect(self.render_thread.quit)
        
        # UI Updates hook into the thread finishing, not the worker finishing
        self.render_thread.finished.connect(lambda: self.on_render_finished(success=True))
        # Note: If you need to catch the specific error string from the worker, 
        # we save it to an instance variable right before quitting:
        self.render_worker.error.connect(self.handle_worker_error)

        # Safe memory cleanup
        self.render_worker.finished.connect(self.render_worker.deleteLater)
        self.render_thread.finished.connect(self.render_thread.deleteLater)

        self.render_thread.start()

    def handle_worker_error(self, err_msg):
        # Helper to capture the error string and pass it along
        self.last_error_msg = err_msg
        # Trigger UI finish with a failure state
        self.on_render_finished(success=False, error_msg=err_msg)


    def request_render_cancel(self):
        """Triggered when user clicks 'Cancel Render' button."""
        self.is_cancelled = True
        self.status_label.setText("Stopping rendering process...")
        
        # Check if thread exists and is running before touching it
        if hasattr(self, 'render_thread') and self.render_thread and self.render_thread.isRunning():
            self.render_thread.terminate() 
            self.render_thread.wait()      
        
        self.on_render_finished(success=False, error_msg="Render aborted by user.")

    def on_render_finished(self, success: bool, error_msg: str = ""):
        # 1. Reset progress bar
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # 2. Re-enable inputs, turn cancel button BACK off
        self.run_action.setEnabled(True)
        self.save_run_action.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 3. Clear thread reference to avoid double-termination
        self.render_thread = None

        # 4. Display Status
        if success and not self.is_cancelled and not error_msg:
            self.status_label.setText("Success: Video completed!")
        elif "aborted" in error_msg or self.is_cancelled:
            self.status_label.setText("Process cancelled.")
        else:
            self.status_label.setText("Error occurred.")
            QMessageBox.critical(self, "Error", f"Could not run file:\n{error_msg}")

    def file_settings(self):
        # Launches the preferences UI window.
        dialog = PreferencesDialog(self, self.config)

        # If user clicks "Apply & Save", update main window live
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings()

    def apply_settings(self):
        # Refreshes the main text editor UI features using configuration data.

        # Update text visuals
        font_name = self.config.data["font_family"]
        font_size = self.config.data["font_size"]
        self.text_area.setFont(QFont(font_name, font_size))

        self.preview_config = self.config.data["preview"]
        self.quality_config = self.config.data["quality"]
        self.disable_caching_config = self.config.data["disable_caching"]

        self.theme_config =  self.config.data["theme"]

        self.output_directory = self.config.data["output_directory"]
        
        self.set_output_file()

        # Update behaviors
        if self.config.data["line_wrapping"]:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def set_output_file(self):
        if self.current_input_file:
            self.current_output_file = Path(self.output_directory) / str(Path(self.current_input_file).name).removesuffix(".txt")


    def update_title(self):
        if self.current_input_file:
            name = Path(self.current_input_file).name
            self.setWindowTitle(f"KineTeX Lesson Editor - {name}")
        else:
            self.setWindowTitle("KineTeX Lesson Editor")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = CodeEditor()
    editor.show()
    sys.exit(app.exec())

