# Author: Malte Schudek
# Repository: https://github.com/malte-code/VentusFlow
# File: backend/readme.md

# README: Backend (server.js & process_input.py)

## Übersicht

Das Backend der VentusFlowWebGUI besteht aus zwei zentralen Komponenten:
- `server.js`: Node.js-Server für WebSocket-Kommunikation, SSH-Management und Steuerung der OpenFOAM-Simulationen auf einem Remote-Cluster.
- `process_input.py`: Python-Skript zur Verarbeitung der vom Frontend exportierten Simulationsdaten (JSON) und zur Generierung aller notwendigen OpenFOAM-Konfigurationsdateien und Hilfsskripte.

---

## 1. server.js

### Aufgaben und Logik

- **WebSocket-Server:**
  - Stellt einen WebSocket-Server bereit, über den das Frontend mit dem Backend kommuniziert.
  - Alle wichtigen Aktionen (Export, Simulationssteuerung, SSH-Authentifizierung) laufen über WebSocket-Nachrichten.

- **SSH-Management:**
  - Verbindet sich per SSH (über das `ssh2`-Modul) mit einem Remote-Server oder HPC-Cluster.
  - Unterstützt Authentifizierung via SSH-Agent oder Passphrase (inkl. Modal für Passphrase-Eingabe im Frontend).
  - Überträgt Dateien per SFTP (z.B. für Sync und VTK-Download).
  - Führt Remote-Kommandos aus (Allclean, Allpre, Allrun, Status, Allpost, VTK-Transfer etc.).

- **Export-Workflow:**
  - Empfängt Exportdaten (JSON) vom Frontend.
  - Speichert die Simulationsparameter als JSON-Datei.
  - Startet das Python-Skript `process_input.py` zur Generierung der OpenFOAM-Inputdateien.
  - Testet und verwaltet die SSH-Konfiguration für spätere Simulationsschritte.

- **Simulationssteuerung:**
  - Nimmt Kommandos vom Frontend entgegen (z.B. Sync, Clean, Pre, Run, Status, Post, VTK) und führt sie auf dem Remote-Server aus.
  - Überwacht den Fortschritt (z.B. durch periodisches Polling von Status/Progress).

- **Fehler- und Statusmanagement:**
  - Gibt Status- und Fehlermeldungen direkt an das Frontend weiter.
  - Verarbeitet Passphrase- und Verbindungsfehler benutzerfreundlich.

### Typischer Ablauf
1. Nutzer:innen definieren im Frontend Geometrie, Turbinen und Parameter.
2. Export-Button sendet die Daten als JSON an das Backend.
3. `server.js` speichert die Daten und ruft `process_input.py` auf.
4. Nach erfolgreichem Export kann das Frontend per WebSocket Kommandos an das Backend senden, um die Simulation auf dem Cluster zu steuern.
5. Ergebnisse (z.B. VTK-Dateien) können zurückübertragen werden.

---

## 2. process_input.py

### Aufgaben und Logik

- **Verarbeitung der Simulationsdaten:**
  - Liest die vom Frontend exportierte JSON-Datei mit allen Simulationsparametern, Geometrien, Turbinen, Wake-Regionen und Umgebungsbedingungen.
  - Extrahiert und validiert alle relevanten Werte für die OpenFOAM-Konfiguration.

- **Verwendete Klassen:**
  - **SimulationArea:** Kapselt die Geometrie, Rotation und Dimensionen des Simulationsgebiets. Stellt Methoden zur Berechnung und Transformation der Simulationsfläche bereit.
  - **WakeRegion:** Repräsentiert Wake-Regionen (Nachlaufgebiete) hinter Turbinen, inklusive Geometrie und Gruppierungslogik für überlappende Regionen.
  - **WindTurbines:** Modelliert einzelne Windturbinen mit Typ, Position und technischen Parametern (z.B. Nabenhöhe, Rotorradius, TSR).
  - **Environment:** Enthält Umgebungsparameter wie Windgeschwindigkeit, Windrichtung, Turbulenz und Profilhöhen.
  - **SolverParameters:** Speichert Zeiteinstellungen, Zeitschrittweite, Schreibintervall und Anzahl der Rechenkerne für die Simulation.

- **Hauptfunktionen (werden direkt aufgerufen):**
  - **get_simulation_data:** Lädt und validiert die Simulationsdaten aus der JSON-Datei. Eignet sich als Einstiegspunkt für alle weiteren Verarbeitungsschritte.
  - **get_case_folder:** Ermittelt das Zielverzeichnis für die zu generierenden OpenFOAM-Dateien basierend auf den Simulationsdaten.
  - **compute_mesh_parameters:** Berechnet die Zellgrößen, Skalierungsfaktoren und Dimensionen für das Simulationsgebiet und die Mesh-Auflösung.
  - **create_allclean_script:** Erstellt das Skript `Allclean`, das zur Bereinigung des Simulationsverzeichnisses vor einem neuen Lauf dient.
  - **create_allpre_script:** Generiert das Skript `Allpre`, das alle Vorbereitungsschritte für die Simulation (z.B. Mesh-Generierung, Setzen von Regionen) automatisiert.
  - **create_blockMeshDict:** Erstellt die zentrale OpenFOAM-Meshdatei `blockMeshDict` basierend auf den Geometrie- und Auflösungsparametern.
  - **create_nut_file, create_U_file, create_p_file:** Erzeugen die Anfangsbedingungen für Viskosität, Geschwindigkeit und Druck im OpenFOAM-Case.
  - **create_initial_conditions_file:** Erstellt eine Datei mit den Anfangsbedingungen für die Simulation.
  - **create_inlet_conditions:** Generiert die Randbedingungen für den Einlass (z.B. Windprofil, Turbulenz).
  - **create_refine_files:** Erstellt die Refinement- und TopoSetDict-Dateien für verschiedene Verfeinerungsstufen des Meshs.
  - **create_topoSetDict_wakeregions:** Generiert die TopoSetDict-Datei für die Wake-Regionen.
  - **create_refineMeshDict_wakeregions:** Erstellt die Mesh-Refinement-Datei für die Wake-Regionen.
  - **create_allrun_script:** Erstellt das Skript `Allrun` zum Starten der Simulation.
  - **create_allpost_script:** Generiert das Skript `Allpost` für die Nachbearbeitung (z.B. VTK-Erstellung).
  - **create_allrun_slurm_script, create_allpost_slurm_script:** Erzeugen die Slurm-Skripte für die Ausführung auf dem Cluster.
  - **create_controlDict:** Erstellt die zentrale Steuerdatei `controlDict` für die Simulation.
  - **create_decomposeParDict:** Generiert die Parallelisierungsdatei für OpenFOAM.
  - **create_fvOptions:** Erstellt die Datei für zusätzliche OpenFOAM-Optionen (z.B. Turbinenmodellierung).
  - **create_writeForceAllTurbines:** Erstellt eine Datei zur Ausgabe der Turbinenkräfte.
  - **create_sampleSlice:** Generiert eine Datei für die Extraktion von Querschnittsdaten (z.B. für die Auswertung).
  - **print_simulation_summary:** Gibt eine Zusammenfassung der wichtigsten Simulationsparameter und generierten Dateien aus.

- **Automatisierung und Modularität:**
  - Die Datei ist modular aufgebaut: Für jeden wichtigen Schritt gibt es eine eigene Funktion (z.B. für die Erstellung einzelner Dicts oder Skripte).
  - Die Logik ist so ausgelegt, dass sie mit beliebigen, vom Frontend generierten Geometrien und Parametern umgehen kann.

- **Erweiterbarkeit:**
  - Neue Turbinentypen, zusätzliche Parameter oder weitere OpenFOAM-Features können durch Ergänzen der entsprechenden Funktionen und Datenstrukturen leicht integriert werden.

### Typischer Ablauf
1. Das Skript wird von `server.js` mit dem Pfad zur JSON-Datei aufgerufen.
2. Es liest die Simulationsdaten ein und verarbeitet sie.
3. Alle benötigten OpenFOAM-Inputdateien und Hilfsskripte werden im Zielverzeichnis erzeugt.
4. Die Simulation kann anschließend (vom Backend aus) auf dem Cluster gestartet werden.

---

## Zusammenspiel und Architektur

- Das Backend ist so konzipiert, dass das Frontend keinerlei OpenFOAM- oder SSH-Logik kennen muss.
- Die gesamte Simulationsvorbereitung, -steuerung und -auswertung läuft über die beiden Backend-Komponenten.
- Die Kommunikation ist klar getrennt: WebSocket für Steuerung und Status, Python für die eigentliche Dateigenerierung.
- Die Architektur ist modular und leicht erweiterbar für neue Simulationsfeatures, Clusterumgebungen oder zusätzliche Auswertungen.

---

## Fazit

Das Backend der VentusFlowWebGUI ermöglicht eine vollständige, automatisierte Steuerung und Vorbereitung von OpenFOAM-Simulationen auf entfernten Clustern – von der grafischen Definition im Browser bis zur Ausführung und Ergebnissicherung auf dem HPC-System. Die Trennung in `server.js` (Kommunikation, SSH, Steuerung) und `process_input.py` (Dateigenerierung, OpenFOAM-Logik) sorgt für Übersichtlichkeit, Wartbarkeit und Erweiterbarkeit.
