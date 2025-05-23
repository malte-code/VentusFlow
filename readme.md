# VentusFlow WebGUI – Offshore Windpark Simulation (LES, Actuator Line)

**Autor:** Malte Schudek  
**Hochschule:** Universität Stuttgart, HLRS  
**Betreuer:** Prof. Dr.-Ing. Dr. h.c. Hon. Prof. Michael M. Resch, Uwe Woessner, Dr.-Ing.  

**Studienarbeit Energietechnik** | April 2025 | Bericht Nr. 001  
**Repository:** [github.com/malte-code/VentusFlow](https://github.com/malte-code/VentusFlow)  
**Datei:** `README.md`
---

# VentusFlowWebGUI

Willkommen bei **VentusFlowWebGUI** – einer webbasierten Benutzeroberfläche, die mithilfe von [OpenLayers](https://openlayers.org/) ein grafisches Werkzeug zur Definition von Turbinenpositionen, Windrichtung und Simulationsgebiet für OpenFOAM bereitstellt. Dieses Projekt ist in **Node.js** und **Vite** (Frontend-Build-Tool) implementiert. Das Frontend kommuniziert über einen WebSocket-Server (Node.js) mit einem **Python**-Programm, das den OpenFOAM-Case generiert.  
Das Backend (server.js) übernimmt außerdem die Steuerung von OpenFOAM-Simulationen auf einem Remote-Server oder Cluster per SSH.

---
## Inhaltsverzeichnis
1. [Projektüberblick](#projektüberblick)
3. [Installation & Setup](#installation--setup)
4. [Start der Anwendung](#start-der-anwendung)
5. [Funktionen und Nutzung](#funktionen-und-nutzung)
   - [Simulationsgebiet](#simulationsgebiet)
   - [Turbinenpositionen](#turbinenpositionen)
   - [Windrichtung](#windrichtung)
   - [Export der Daten](#export-der-daten)
   - [OpenFOAM Control Panel](#openfoam-control-panel)
6. [Technische Details](#technische-details)
   - [Frontend](#frontend)
   - [Backend](#backend)
   - [Python-Verarbeitung](#python-verarbeitung)
9. [Lizenz](#lizenz)

---

## Projektüberblick

Ziel von **VentusFlowWebGUI** ist es, ein einfaches grafisches Werkzeug bereitzustellen, mit dem Sie:
- Ein **rechteckiges Simulationsgebiet** definieren und es bei Bedarf rotieren können.  
- **Windturbinen** auf einer Karte platzieren und verschieben können.
- Die **Windrichtung** über einen Slider einstellen können (wodurch sich auch das Simulationsgebiet mitdreht).
- Einen lauffähigen Simulation-Case generien, 
- Communication mit Server/Cluster, um OpenFOAM-Simulationen direkt über ein Control-Panel steuern können.

## Installation & Setup

1. **Voraussetzungen**:
   - Node.js (Version 16 oder höher)
   - npm 
   - Python (liegt in virtueller Umgebung vor. (für Paketverwaltung))
   - Server/Cluster mit OpenFOAM oder lokal 

2. **Installation**:
   ```bash
   # Klone das Repository
   git clone https://github.com/malte-code/VentusFlowWebGUI.git
   cd VentusFlowWebGUI
   
   # Installiere Node.js-Abhängigkeiten 
   npm install
   # wenn weiterentwicklung gewünscht
   npm start

   # wenn Remote Cluster funtkionen genutzt werden sollen, aktuallisere ssh-agent pfad im serve script eintrag der package.json datei (lauffähiger build wird mitgebliefert)
   npm run build
   npm run serve

   aktuallisere ssh config in index.html unter: Server Connection Setting
   ```


## Start der Anwendung
```
Die Anwendung besteht aus zwei Teilen, die gleichzeitig laufen müssen: dem Frontend (Vite) und dem Backend (Node.js). Das Projekt verwendet `concurrently`, um beide Komponenten gleichzeitig zu starten:

# Starte die Anwendung mit Server im Entwicklungsmodus
npm start
# Starte nur das Frontend im Entwicklungsmodus
npm dev

# Alternativ: Baue die Anwendung (npm install notwendig) oder starte sie im Produktionsmodus (ein build befindet sich in /dist)
npm run build
npm run serve


Nach dem Start ist die Anwendung unter `http://localhost:3000` (oder einem anderen Port, der in der Konsole angezeigt wird) erreichbar.

```

## Funktionen und Nutzung

### Taskleiste
- **Layer Droptdown**: Wählen Sie im Dropdown-Menü "Simulationsgebiet" und zeichnen Sie ein Rechteck auf der Karte, um den Simulationsbereich zu definieren.
Jeder Formtyp wird auf einem eigenen Layer der dann aktuell bearbeitet werden kann definiert. Ein wechsel des Dropdowneintrags, ändert den aktiven layer, der bearbetiet werden kann
- **Rotation**: Rotieren die Windrichtung und das Simualtinsgebiet simultan über den Slider
- **edit shapes**: Im aktivierten Editmodus, können objekte des aktiven Layers durch anklicken ausgewählt und anschließend verschoben werden.
- **🗑️ (delete)**
alle Objekte des Aktiven Layers werden gelöscht, wenn kein objekt durch edit ausgewählt ist, ansonsten wird nur das ausgewählte Objekt gelöscht.

### Sidepanels (einklappbar)
- **Turbinen Panel (links)**: Verwenden Sie die Eingabefelder des linken toggle Fensters, um die Attribute des Turbinenobjekts definieren, das als nächstes initialisiert auf der karte gesetzt wird.
Wake Verfeinerungsgebiete werden für alle exitierenden Turbinenobjekte des Turbienlayers angepasst.
- **Parameterpanel (rechts)**: Verändern der Dimensionen des Simualtionsgebietes, umgebungsparameter und Löser Einstellugnen

### Export der Daten 
Über den Exportbutton wird der OpenFOAM-Case erstellt und die ssh Verbindung konfiguriert. (Case wird immer generiert)
Bei Nutzung eines ssh-Agenten, kann ohne passphraseeingabe mit dem "abbrechen" Button die konfiguration erstellt werden.
Ohne Agenten ist eine passphrase eingabe notwendig (unsicher, da das passwort zur laufzwit der Anwendung in Klartext gespeichert wird)
Sidepanel 


### OpenFOAM Control Panel
- **Local to Remote**: Synchronisiert lokale Dateien mit dem Remote-Server.
- **Allclean**: Bereinigt vorherige Simulationsergebnisse.
- **Allpre**: Führt die Vorbereitungsschritte für die Simulation durch.
- **Allrun (Slurm)**: startet die Simulatin als slurm job.
- **Status**: Zeigt den aktuellen Status der Simulationen.
- **Allpost**: Rekonstruiert parallelisierung und erstelt VTK Dateien.
- **Get VTK**: Lädt VTK-Dateien für die Visualisierung herunter.

## Technische Details

### Frontend

- **OpenLayers**: Für die interaktive Karte und Vektorzeichnungen.
- **Vite**: Als Build-Tool und Entwicklungsserver.
- Die Hauptanwendungslogik befindet sich in `frontend/src/main.js`, die HTML-Struktur in `frontend/index.html` und die Styles in `frontend/src/styles/style.css`.

### Backend

- **Node.js mit Express**: Dient als Basis für den WebSocket-Server (es werden keine eigenen HTTP-API-Endpunkte oder statischen Dateien ausgeliefert).
- **WebSocket (ws)**: Für die gesamte Echtzeit-Kommunikation zwischen Frontend und Backend (z.B. Export, SSH-Kommandos, Fortschrittsabfragen).
- **SSH2**: Für die Verbindung mit dem Remote-Server zur Ausführung von OpenFOAM-Befehlen.
- Die Server-Implementierung befindet sich in `backend/server.js`.

### Python-Verarbeitung
- Das Python-Skript `backend/process_input.py` konvertiert die JSON-Asugabe des frontend in OpenFOAM-kompatible Dateien. 


## MIT Lizenz
Copyright (c) 2024 – VentusFlowWebGUI Projekt