# Author: Malte Schudek
# Repository: https://github.com/malte-code/VentusFlow
# File: frontend/src/readme.md

# README: frontend/src/main.js

## Übersicht

Die Datei `main.js` ist das zentrale Einstiegsskript für das Frontend der VentusFlowWebGUI. Sie steuert die gesamte Interaktion mit der OpenLayers-Karte, die Layer- und Feature-Logik, die UI-Elemente (Toolbar, Panels), die Export- und Simulationssteuerung sowie die Kommunikation mit dem Backend-Server über WebSockets.

---

## Hauptbestandteile

### 1. **OpenLayers-Kartenlogik**

- **Basiskarte:**  
  Erstellt eine OpenLayers-Karte mit OpenStreetMap als Hintergrund.
- **Layer:**  
  - **Turbinen-Layer:** Zeigt Windturbinen als Icons.
  - **Simulationsgebiet-Layer:** Zeigt das Simulationsgebiet als Rechteck/Polygon.
  - **Wake-Layer:** Visualisiert Wake-Regionen hinter Turbinen.
  - **Sphere-Radius-Layer:** Zeigt Einflussbereiche (Kreise) um Turbinen.

### 2. **Feature-Styles**

- Definiert individuelle Styles für:
  - Turbinen (Icon)
  - Simulationsgebiet (blaues Rechteck mit Label)
  - Wake-Regionen (rotes Rechteck mit Label)
  - Einflussbereiche (blauer Kreis mit Label)
  - Windrichtungspfeil (oranger Pfeil mit Label)

### 3. **Interaktionen**

- **Zeichnen:**  
  Nutzer:innen können Punkte (Turbinen) und Rechtecke (Simulationsgebiet) auf der Karte platzieren.
- **Verschieben:**  
  Features können im Edit-Modus verschoben werden.
- **Auswählen:**  
  Features können selektiert und gezielt bearbeitet oder gelöscht werden.
- **Skalieren/Rotieren:**  
  Das Simulationsgebiet kann in Breite/Tiefe skaliert und rotiert werden (z.B. mit Slider für Windrichtung).

### 4. **Toolbar & Panels**

- **Dropdown-Menü:**  
  Auswahl des aktiven Layers (Turbinen, Simulationsgebiet, etc.).
- **Buttons:**  
  - Formen löschen
  - Edit-Modus aktivieren
  - Exportieren
  - Simulationssteuerung (z.B. Allclean, Allpre, Allrun, Status, Allpost, Get VTK)
- **Panels:**  
  - Rechte und linke Sidepanels für Parameter- und Turbineneinstellungen (auf- und zuklappbar).

### 5. **Parameter- und Wake-Logik**

- **Turbinenparameter:**  
  Auswahl und Verwaltung verschiedener Turbinentypen und deren Eigenschaften.
- **Wake-Regionen:**  
  Automatische Berechnung und Visualisierung von Wake-Regionen hinter Turbinen.
- **Einflussbereiche:**  
  Visualisierung des Einflussradius um jede Turbine.

### 6. **Export & Backend-Kommunikation**

- **WebSocket-Verbindung:**  
  Aufbau und Verwaltung der Verbindung zum Backend-Server.
- **Export:**  
  Überträgt die aktuellen Simulationsdaten (Geometrie, Turbinen, Parameter) an das Backend.
- **SSH/Passphrase:**  
  Verwaltung der Passphrase-Eingabe für SSH-Verbindungen (bei Bedarf).
- **Simulationssteuerung:**  
  Senden von Kommandos an das Backend zur Steuerung von OpenFOAM (z.B. Sync, Clean, Pre, Run, Status, Post, VTK).

---

## Codestruktur und Logik

Die Datei `main.js` ist modular aufgebaut und gliedert sich in mehrere Funktionsbereiche, die jeweils klar voneinander getrennt sind. Die wichtigsten Komponenten und deren Zusammenspiel sind:

### 1. Initialisierung und Layer-Setup
- **Karteninitialisierung:** Die OpenLayers-Karte wird mit OpenStreetMap als Basiskarte erstellt.
- **Layer:** Es werden verschiedene Vektor-Layer für Turbinen, Simulationsgebiet, Wake-Regionen und Einflussbereiche (Sphere-Radius) angelegt und gestylt.

### 2. Feature- und Interaktionslogik
- **Zeichnen:** Nutzer:innen können über Interaktionen Punkte (Turbinen) und Rechtecke (Simulationsgebiet) auf der Karte platzieren. Die Zeicheninteraktion ist dynamisch an den aktiven Layer gebunden.
- **Editieren und Verschieben:** Über einen Edit-Modus können Features ausgewählt und verschoben werden. Die Translate-Interaktion ist nur für den jeweils aktiven Layer aktiv.
- **Skalieren und Rotieren:** Das Simulationsgebiet kann in Breite und Tiefe skaliert sowie rotiert werden. Die Transformationen werden direkt auf die Geometrie angewendet und die UI-Elemente (z.B. Slider) steuern diese Operationen.

### 3. UI-Elemente und Panels
- **Toolbar:** Über Dropdowns und Buttons werden Layer gewechselt, Formen gelöscht, der Edit-Modus aktiviert und die Export- sowie Simulationsfunktionen ausgelöst.
- **Sidepanels:** Parameter- und Turbinen-Panel sind ein- und ausklappbar und ermöglichen die Eingabe und Anpassung von Simulationsparametern und Turbineneigenschaften.

### 4. Wake- und Einflussbereich-Logik
- **Wake-Regionen:** Für jede Turbine wird automatisch eine Wake-Region berechnet und visualisiert. Änderungen an Parametern oder Turbinenpositionen aktualisieren die Wake-Layer dynamisch.
- **Sphere-Radius:** Um jede Turbine wird ein Einflussbereich als Kreis angezeigt, dessen Größe sich an den Turbinenparametern orientiert.

### 5. Backend-Kommunikation
- **WebSocket:** Die gesamte Kommunikation mit dem Backend (Export, Simulationssteuerung, SSH/Passphrase) läuft über eine WebSocket-Verbindung. Status- und Fehlermeldungen werden direkt an die UI weitergegeben.
- **Export und Steuerbefehle:** Die aktuellen Simulationsdaten und Steuerbefehle (z.B. Sync, Clean, Run) werden über dedizierte Funktionen an das Backend gesendet.

### 6. Modularität und Erweiterbarkeit
- Die Funktionen sind so gestaltet, dass sie leicht erweitert oder angepasst werden können (z.B. für neue Turbinentypen, weitere Layer oder zusätzliche Simulationsparameter).
- Die IDs der UI-Elemente sind mit der HTML-Struktur abgestimmt, sodass eine klare Trennung zwischen Logik und Darstellung besteht.

**Zusammengefasst:**
`main.js` verbindet Kartenlogik, UI-Interaktion und Backend-Kommunikation in einer modularen Struktur. Die Layer- und Feature-Logik ist eng an OpenLayers angelehnt, während die Simulations- und Exportfunktionen über WebSockets mit dem Backend orchestriert werden. Änderungen an der Karte oder den Parametern wirken sich unmittelbar auf die Visualisierung und die exportierten Daten aus.


## Erweiterbarkeit & Hinweise

- **Modularisierung:**  
  Viele Funktionen sind bereits modular aufgebaut und können leicht erweitert werden (z.B. für neue Turbinentypen oder weitere Layer).
- **UI-Elemente:**  
  Die IDs der HTML-Elemente müssen mit denen in der `index.html` übereinstimmen.
- **Backend-Kommunikation:**  
  Die WebSocket-Logik ist zentral für Export und Simulationssteuerung. Fehler- und Statusmeldungen werden direkt an die UI weitergegeben.
- **OpenLayers:**  
  Die Layer- und Feature-Logik ist eng an OpenLayers-Standards angelehnt und kann mit deren API-Dokumentation erweitert werden.

---

## Abhängigkeiten

- [OpenLayers](https://openlayers.org/) (Karten- und Vektorlogik)
- WebSocket (Browser-API)
- Standard-HTML/JS (UI, Events)

---

## Fazit

`main.js` bildet das Herzstück der Benutzerinteraktion im Frontend. Es verbindet die Kartenlogik, die UI und die Backend-Kommunikation zu einer intuitiven Oberfläche für die Definition und Steuerung von OpenFOAM-Simulationen.

---

**Tipp:**  
Für eine schnelle Übersicht empfiehlt sich ein Blick auf die Layer-Initialisierung, die Toolbar-Events und die WebSocket-Logik. Wer neue Features ergänzen will, sollte die bestehenden modularen Funktionen als Vorlage nutzen.
