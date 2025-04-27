# VentusFlowWebGUI

Willkommen bei **VentusFlowWebGUI** – einer webbasierten Benutzeroberfläche, die mithilfe von [OpenLayers](https://openlayers.org/) ein interaktives Werkzeug zur Definition von Turbinenpositionen, Windrichtung und Simulationsgebiet für Strömungs- bzw. CFD-Simulationen bereitstellt. Dieses Projekt ist in **Node.js** und **Vite** (Frontend-Build-Tool) implementiert und kommuniziert über ein Backend-Skript (Node.js) mit einem **Python**-Programm, welches die weiteren Schritte zur OpenFOAM-Simulation ausführt.

---

## Inhaltsverzeichnis
1. [Projektüberblick](#projektüberblick)
2. [Verzeichnisstruktur](#verzeichnisstruktur)
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
7. [Debugging & Fehlersuche](#debugging--fehlersuche)
8. [Mögliche Erweiterungen & Alternativen](#mögliche-erweiterungen--alternativen)
9. [Lizenz](#lizenz)

---

## Projektüberblick

Ziel von **VentusFlowWebGUI** ist es, ein einfaches grafisches Werkzeug bereitzustellen, mit dem Sie:
- Ein **rechteckiges Simulationsgebiet** definieren und es bei Bedarf rotieren können.  
- **Windturbinen** (als Punkte) auf einer Karte platzieren und verschieben können.
- Die **Windrichtung** über einen Slider einstellen können.
- Die gesammelten Daten exportieren und an OpenFOAM-Simulationen übergeben können.
- OpenFOAM-Simulationen direkt über ein Control-Panel steuern können.

## Verzeichnisstruktur

```
VentusFlowWebGUI/
├── backend/                   # Server-seitige Komponenten
│   ├── process_input.py       # Python-Skript zur Verarbeitung der Eingabedaten
│   ├── server.js              # Node.js-Server mit Express und WebSocket
│   └── simulation_parameters.json # Exportierte Simulationsparameter
├── frontend/                  # Client-seitige Komponenten
│   ├── assets/
│   │   └── windturbine.svg    # SVG-Icon für Windturbinen
│   ├── index.html             # Haupt-HTML-Datei
│   └── src/
│       ├── components/        # Wiederverwendbare UI-Komponenten
│       ├── main.js            # Hauptskript für die Kartenimplementierung
│       └── styles/
│           └── style.css      # CSS-Styles für die Anwendung
├── dist/                      # Kompilierte Dateien (nach npm run build)
├── package-lock.json          # NPM-Abhängigkeiten (automatisch generiert)
├── package.json               # NPM-Konfiguration und Skripte
├── readme.md                  # Diese Dokumentation
└── vite.config.mjs            # Vite-Konfiguration für das Build-System
```

## Installation & Setup

1. **Voraussetzungen**:
   - Node.js (Version 16 oder höher) und npm
   - Python (für die Backend-Verarbeitung)
   - OpenFOAM (für die eigentliche Simulation)

2. **Installation**:
   ```bash
   # Klone das Repository
   git clone https://github.com/yourusername/VentusFlowWebGUI.git
   cd VentusFlowWebGUI
   
   # Installiere Node.js-Abhängigkeiten
   npm install
   ```

## Start der Anwendung

Die Anwendung besteht aus zwei Teilen, die gleichzeitig laufen müssen: dem Frontend (Vite-Entwicklungsserver) und dem Backend (Node.js-Server). Das Projekt verwendet `concurrently`, um beide Komponenten gleichzeitig zu starten:

```bash
# Starte die Anwendung im Entwicklungsmodus
npm start

# Alternativ: Baue die Anwendung und starte sie im Produktionsmodus
npm run build
npm run serve
```

Nach dem Start ist die Anwendung unter `http://localhost:3000` (oder einem anderen Port, der in der Konsole angezeigt wird) erreichbar.

## Funktionen und Nutzung

### Simulationsgebiet

- **Rechteck-Tool**: Wählen Sie im Dropdown-Menü "Rectangle" und zeichnen Sie ein Rechteck auf der Karte, um den Simulationsbereich zu definieren.
- **Größenanpassung**: Verwenden Sie die Eingabefelder für Breite und Tiefe, um die Dimensionen des Simulationsgebiets präzise anzupassen.
- **Rotation**: Die Rotation des Simulationsgebiets erfolgt automatisch mit der Windrichtung.

### Turbinenpositionen

- **Turbinen platzieren**: Wählen Sie im Dropdown-Menü "Point" und klicken Sie auf die Karte, um Windturbinen zu platzieren.
- **Turbinen verschieben**: Wählen Sie eine Turbine mit dem Auswahlwerkzeug und verschieben Sie sie an eine neue Position.
- **Wake-Rechtecke**: Um jede Turbine wird ein "Wake-Rechteck" angezeigt, das den Nachlaufbereich darstellt.

### Windrichtung

- Verwenden Sie den Windrichtungsslider, um die Windrichtung einzustellen.
- Ein Pfeil auf der Karte zeigt die aktuelle Windrichtung an.
- Das Simulationsgebiet richtet sich automatisch nach der Windrichtung aus.

### Export der Daten

- Geben Sie SSH-Verbindungsdaten ein (Benutzername, Host, Remote-Verzeichnis).
- Klicken Sie auf den "Export"-Button, um die Simulationsdaten zu exportieren.
- Die Daten werden als JSON gespeichert und durch den Python-Prozessor für OpenFOAM aufbereitet.

### OpenFOAM Control Panel

- **Local to Remote**: Synchronisiert lokale Dateien mit dem Remote-Server.
- **Allclean**: Bereinigt vorherige Simulationsergebnisse.
- **Allpre**: Führt die Vorbereitungsschritte für die Simulation durch.
- **Allrun (Slurm)**: Startet die Simulation auf einem Slurm-Cluster.
- **Status**: Zeigt den aktuellen Status der Simulationen.
- **Allpost**: Führt die Nachverarbeitungsschritte aus.
- **Get VTK**: Lädt VTK-Dateien für die Visualisierung herunter.

## Technische Details

### Frontend

- **OpenLayers**: Für die interaktive Karte und Vektorzeichnungen.
- **Vite**: Als Build-Tool und Entwicklungsserver.
- Die Hauptanwendungslogik befindet sich in `frontend/src/main.js`, die HTML-Struktur in `frontend/index.html` und die Styles in `frontend/src/styles/style.css`.

### Backend

- **Node.js mit Express**: Stellt eine HTTP-API und statische Dateien bereit.
- **WebSocket (ws)**: Für Echtzeit-Kommunikation zwischen Frontend und Backend.
- **SSH2**: Für die Verbindung mit dem Remote-Server zur Ausführung von OpenFOAM-Befehlen.
- Die Server-Implementierung befindet sich in `backend/server.js`.

### Python-Verarbeitung

- Das Python-Skript `backend/process_input.py` konvertiert die JSON-Eingabedaten in OpenFOAM-kompatible Konfigurationen.
- Es erstellt die notwendigen Dateien für die Simulationsdurchführung.

## Debugging & Fehlersuche

- **Frontend-Logs**: Überprüfen Sie die Browser-Konsole für JavaScript-Fehler.
- **Backend-Logs**: Überprüfen Sie die Terminal-Ausgabe des Node.js-Servers.
- **Verbindungsprobleme**: Bei SSH-Verbindungsproblemen prüfen Sie Ihre Netzwerkverbindung und SSH-Konfiguration.
- **Terminal-Ausgabe**: Das Terminal-Fenster in der WebGUI zeigt die Ausgabe von Remote-Befehlen an.

## Mögliche Erweiterungen & Alternativen

- **Erweiterte Turbinen-Parameter**: Anpassung von Turbinenhöhe, Durchmesser und anderen Parametern.
- **3D-Visualisierung**: Integration einer 3D-Ansicht für die Simulationsergebnisse.
- **Automatisierte Optimierung**: Algorithmische Platzierung von Turbinen für optimale Energieausbeute.

## Lizenz

Copyright (c) 2024 – VentusFlowWebGUI Projekt