# ZeitplanOptimizer
A tool for creating customized timetables (for schools with special requirements)

#############################################################
###                                                       ###
###   Anleitung zu 'Stundenplan Optimizer' Installation   ###
###                                                       ###
#############################################################

# Einige externe Programme werden verwendet:

# Python
Wenn Sie noch nicht Python installiert haben, installieren Sie am besten miniconda (Das ist eine leichte Version von Anaconda, ein Version Manager für Python)

-> Von https://conda.io/miniconda.html die entsprechende Version von Miniconda installieren. (Download instruction folgen)

# Python package
Einige Python Skripts sind gebraucht, um Excel Tabellen zu bearbeiten und anderes tun:
-	Pyomo (Modelling framework)
-	Openpyxl (read excel)
-	Xlsxwriter (write excel)
-	Argparse (interface to command line)

-> In dem Start Menu, suche nach „Anaconda Prompt“: es sollte einen Command line öffnen.
-> In dem command line, schreiben:
   Pip install pyomo
   Pip install openpyxl
   Pip install xlsxwriter
   Pip install argparse

# Cbc solver
Das ist ein “open source“ (also frei) Solver, von der Coin-OR Projekt. 

-> Am besten das ganze Projekt aus https://www.coin-or.org/download/binary/OptimizationSuite/ herunterladen. Da gibt es viele Möglichkeiten, wähle einfache die späteste Windows Version.
-> Nach dem Download, öffne das Ordner und extrahiere es in einem beliebigen Ordner

# Den Programm selbst
-> Den können Sie jetzt aus https://github.com/AmbroiseIdoine/ZeitplanOptimizer herunterladen

In dem gleichen Ordner finden sich verschiedene Datei:
-	Example_data.xlsx, School_data.xlsx, School_data_nadistrasse.xlsx: input Beispiele. (Um ihr eigenes Problem einzugeben sollten Sie eine von dieser Datei Kopieren und anpassen.)
-	Program.xlsm: Main interface
-	Data_loader_message.txt, Model_log.txt: Log Datei von die Preprocessing und Optimierung Skripts: Die kann man lesen zum Debuggen.
-	Data_loader7.py, pyomo_model.py, write_excel6.py:  diese Skripts sind für den Preprocessing, Optimierung und Postprocessing verantwortlich (NICHT ÄNDERN!)
-	Main2.6.mos: Programm in Mosel (Nicht benutzt)
-	run_command.bat: batch Skript um den Model zu starten

# Prüfen, dass es läuft:

-> Öffnen Sie den Excel Datei „Program.xlms“ (bitte Makros aktivieren!)

In die Parameter, „example_data.xlsx“ sollte als source file eingegeben sein, und 200 als maximal Laufzeit (für größere Model ist aber 1200s oder 3600s besser geeignet)

-> Auf „Read Data“ klicken
-> Wenn das fertig ist auf „Run Optimizer“ klicken: 

Ein Fenster wird geöffnet, und es dauert eine Weile, bis etwas passiert. Dann sehen Sie den Optimizer Lösungsverfahren. Am Ende schließt        sich die Fenster automatisch.

-> Auf „Write Results“ klicken

Jetzt können Sie normalerweise die Zeitpläne öffnen:

-> Klicken Sie einfach auf eine der 3 Buttons recht um den entsprechende Zeitplan im Excel zu öffnen

# Wenn alles funktioniert hat können Sie jetzt anfangen, ihre eigene Inputs zu geben!

###
# (Bitte beachten Sie die Fehlermeldung, nachdem Sie auf "Data Loader" klicken: 
# Es ist nämlich sehr schwer, die ganze Input Datei ohne Fehler zu schreiben)
###
