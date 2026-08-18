# VentusFlow WebGUI – Offshore Windpark Simulation (LES, Actuator Line)

**Autor:** Malte Schudek  
**Hochschule:** Universität Stuttgart, HLRS  
**Betreuer:** Prof. Dr.-Ing. Dr. h.c. Hon. Prof. Michael M. Resch, Dr.-Ing. Uwe Woessner

**Forschungsarbeit Energietechnik** | April 2025 | Bericht Nr. 001  
**Repository:** [github.com/malte-code/VentusFlow](https://github.com/malte-code/VentusFlow)  
**Datei:** `README.md`

---

## VentusFlowWebGUI

Willkommen bei **VentusFlowWebGUI** – einer webbasierten Benutzeroberfläche, die mithilfe von [OpenLayers](https://openlayers.org/) ein grafisches Werkzeug zur Definition von Turbinenpositionen, Windrichtung und Simulationsgebiet für OpenFOAM bereitstellt.

Dieses Projekt ist in **Node.js** und **Vite** (Frontend-Build-Tool) implementiert.  
Das Frontend kommuniziert über einen WebSocket-Server (Node.js) mit einem **Python**-Programm, das den OpenFOAM-Case generiert.  
Das Backend (`server.js`) übernimmt außerdem die Steuerung von OpenFOAM-Simulationen auf einem Remote-Server oder Cluster per SSH.

---

## Inhaltsverzeichnis

1. [Projektüberblick](#projektüberblick)
2. [Installation & Start](#installation--start)
3. [Funktionen und Nutzung](#funktionen-und-nutzung)
    - [Simulationsgebiet](#simulationsgebiet)
    - [Turbinenpositionen](#turbinenpositionen)
    - [Windrichtung](#windrichtung)
    - [Export der Daten](#export-der-daten)
    - [OpenFOAM Control Panel](#openfoam-control-panel)
4. [Technische Details](#technische-details)
    - [Frontend](#frontend)
    - [Backend](#backend)
    - [Python-Verarbeitung](#python-verarbeitung)
5. [Lizenz](#mit-lizenz)

---

## Projektüberblick

Ziel von **VentusFlowWebGUI** ist es, ein einfaches grafisches Werkzeug bereitzustellen, mit dem Sie:

- Ein **rechteckiges Simulationsgebiet** definieren und es bei Bedarf rotieren können.
- **Windturbinen** auf einer Karte platzieren und verschieben können.
- Die **Windrichtung** über einen Slider einstellen können (wodurch sich auch das Simulationsgebiet mitdreht).
- Einen lauffähigen Simulation-Case generieren.
- Kommunikation mit Server/Cluster, um OpenFOAM-Simulationen direkt über ein Control-Panel steuern zu können.

---

## Installation & Start

### 1. Voraussetzungen

- Node.js (Version 16 oder höher)
- npm
- Python (liegt in virtueller Umgebung vor, für Paketverwaltung)
- Server/Cluster mit OpenFOAM oder lokal

### 2. Installation & Start

```bash
# Klone das Repository
git clone https://github.com/malte-code/VentusFlow.git
cd VentusFlow

# Installiere die Frontend-Abhängigkeiten
cd VentusFlowWebGUI
npm install

# Starte die Anwendung mit Server im Entwicklungsmodus
npm start

# Starte nur das Frontend im Entwicklungsmodus
npm run dev

# Alternativ: Build der Anwendung für Produktion
npm run build

# Optional: Produktions-Preview mit Server-Start
npm run serve
```

Nach dem Start ist die Anwendung unter `http://localhost:3000` (oder einem anderen Port, der in der Konsole angezeigt wird) erreichbar.

### 3. Projektstruktur

```text
VentusFlow/
├── README.md
├── LICENSE
├── VentusFlowWebGUI/
│   ├── backend/
│   │   ├── process_input.py
│   │   ├── server.js
│   │   └── simulation_parameters.json
│   ├── frontend/
│   ├── package.json
│   └── dist/
├── offshorewindpark_VentusFlow/
│   ├── system/
│   ├── constant/
│   └── Allpre
└── .github/
```

> Das Repository enthält sowohl die WebGUI als auch den zugehörigen OpenFOAM-Case/Simulationsteil. Die eigentliche Web-App wird in `VentusFlowWebGUI/` gestartet.

### 3. Voreinstellungen der OpenFOAM Umgebung

Füge folgende Einstellungen in deine `.bashrc` ein:

```bash
### OpenFOAM SETTINGS ###
########################

# OpenFOAM-Version und ThirdParty-Verzeichnis festlegen
export WM_PROJECT_DIR=/home/hpcschud/OpenFOAM/OpenFOAM-v2212/OpenFOAM-v2212
export WM_THIRD_PARTY_DIR=/home/hpcschud/OpenFOAM/OpenFOAM-v2212/ThirdParty-v2212

# OpenFOAM-Umgebung sourcen
source $WM_PROJECT_DIR/etc/bashrc

# OpenFOAM-Binärdateien und wmake-Tools zum PATH hinzufügen
export PATH="$WM_PROJECT_DIR/platforms/linux64GccDPInt32Opt/bin:$WM_PROJECT_DIR/wmake:$PATH"

# LD_LIBRARY_PATH für OpenFOAM-Bibliotheken anpassen
export LD_LIBRARY_PATH="$WM_PROJECT_DIR/platforms/linux64GccDPInt32Opt/lib:$WM_THIRD_PARTY_DIR/platforms/linux64GccDPInt32/lib:$LD_LIBRARY_PATH"

### turbinesFoam SETTINGS ###
############################

# Pfad zu turbinesFoam festlegen
export TURBINESFOAM_DIR=/home/hpcschud/OpenFOAM/turbinesFoam

# turbinesFoam-Binärdateien zum PATH hinzufügen
export PATH="$TURBINESFOAM_DIR/platforms/linux64GccDPInt32Opt/bin:$PATH"

# turbinesFoam-Bibliotheken zum LD_LIBRARY_PATH hinzufügen
export LD_LIBRARY_PATH="$TURBINESFOAM_DIR/platforms/linux64GccDPInt32Opt/lib:$LD_LIBRARY_PATH"
```

> Die korrekte `.bashrc` muss in `backend/process_input.py` bei "Allrun.slurm" gesetzt sein.

---

## Funktionen und Nutzung

### Taskleiste

- **Layer Dropdown**: Wählen Sie im Dropdown-Menü "Simulationsgebiet" und zeichnen Sie ein Rechteck auf der Karte, um den Simulationsbereich zu definieren.  
  Jeder Formtyp wird auf einem eigenen Layer definiert, der dann aktuell bearbeitet werden kann. Ein Wechsel des Dropdown-Eintrags ändert den aktiven Layer, der bearbeitet werden kann.
- **Rotation**: Rotieren Sie die Windrichtung und das Simulationsgebiet simultan über den Slider.
- **Edit shapes**: Im aktivierten Editmodus können Objekte des aktiven Layers durch Anklicken ausgewählt und anschließend verschoben werden.
- **🗑️ (Delete)**:  
  Alle Objekte des aktiven Layers werden gelöscht, wenn kein Objekt durch Edit ausgewählt ist, ansonsten wird nur das ausgewählte Objekt gelöscht.

### Sidepanels (einklappbar)

- **Turbinen Panel (links)**: Verwenden Sie die Eingabefelder des linken Toggle-Fensters, um die Attribute des Turbinenobjekts zu definieren, das als nächstes initialisiert auf der Karte gesetzt wird.  
  Wake-Verfeinerungsgebiete werden für alle existierenden Turbinenobjekte des Turbinenlayers angepasst.
- **Parameterpanel (rechts)**: Verändern Sie die Dimensionen des Simulationsgebietes, Umgebungsparameter und Löser-Einstellungen.

### Export der Daten

Über den Export-Button wird der OpenFOAM-Case erstellt und die SSH-Verbindung konfiguriert. (Case wird immer generiert)  
Bei Nutzung eines SSH-Agenten kann ohne Passphrase-Eingabe mit dem "Abbrechen"-Button die Konfiguration erstellt werden.  
Ohne Agenten ist eine Passphrase-Eingabe notwendig (unsicher, da das Passwort zur Laufzeit der Anwendung in Klartext gespeichert wird).

### OpenFOAM Control Panel

- **Local to Remote**: Synchronisiert lokale Dateien mit dem Remote-Server.
- **Allclean**: Bereinigt vorherige Simulationsergebnisse.
- **Allpre**: Führt die Vorbereitungsschritte für die Simulation durch.
- **Allrun (Slurm)**: Startet die Simulation als Slurm-Job.
- **Status**: Zeigt den aktuellen Status der Simulationen.
- **Allpost**: Rekonstruiert Parallelisierung und erstellt VTK-Dateien.
- **Get VTK**: Lädt VTK-Dateien für die Visualisierung herunter.

---

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

- Das Python-Skript `backend/process_input.py` konvertiert die JSON-Ausgabe des Frontends in OpenFOAM-kompatible Dateien.

---

## GPLv3 Lizenz

Dieses Projekt steht unter der GNU General Public License Version 3 (GPLv3).  
Siehe die Datei `LICENSE` für weitere Details.

Copyright (c) 2024 – VentusFlowWebGUI Projekt
