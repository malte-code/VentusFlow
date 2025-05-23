# VentusFlow WebGUI – Offshore Windpark Simulation (LES, Actuator Line)

**Autor:** Malte Schudek  
**Hochschule:** Universität Stuttgart, HLRS  
**Betreuer:** Prof. Dr.-Ing. Dr. h.c. Hon. Prof. Michael M. Resch, Uwe Woessner, Dr.-Ing.  

**Studienarbeit Energietechnik** | April 2025 | Bericht Nr. 001  
**Repository:** [github.com/malte-code/VentusFlow](https://github.com/malte-code/VentusFlow)  
**Datei:** `frontend/README.md`
---


# README: frontend/index.html

## Übersicht

Die Datei `index.html` bildet das Grundgerüst der Benutzeroberfläche für die VentusFlowWebGUI. Sie enthält die gesamte HTML-Struktur für die Kartenanzeige, die Toolbar, die Parameter- und Turbinenpanels, die Simulationssteuerung sowie Modale für die SSH-Verbindung. Die eigentliche Logik und Interaktivität wird über das JavaScript-Modul `src/main.js` bereitgestellt.

---

## Hauptbestandteile der HTML-Struktur

### 1. Kartenbereich
- `<div id="map"></div>`
  - Platzhalter für die OpenLayers-Karte.

### 2. Toolbar
- `<div id="toolbar"> ... </div>`
  - **Dropdown:** Auswahl des aktiven Layers (Turbine, Simulationsgebiet, None).
  - **Windrichtungs-Slider:** Einstellung der Windrichtung (0–360°).
  - **Edit-Button:** Aktiviert den Edit-Modus für Shapes.
  - **Löschen-Button:** Löscht Shapes des aktiven Layers oder selektierte Features.
  - **Export-Button:** Exportiert die aktuellen Simulationsdaten und startet den Case-Export.
  - **Progress Bar:** Zeigt Fortschritt der laufenden Simulation auf dem Cluster an.

### 3. Parameter Panel (Rechts)
- `<div id="PanelRight"> ... </div>`
  - **Simulationsgebiet:** Eingabe für Breite und Tiefe.
  - **Umgebungsparameter:** Windgeschwindigkeit, Turbulenz, Profilhöhen, Zellendichte.
  - **Löser-Einstellungen:** Start-/Endzeit, Zeitschritt, Schreibintervall, Compute Cores (Kerne die am Cluster angefragt werden).
  - **Toggle-Button:** Panel ein-/ausklappbar.

### 4. Turbinen Panel (Links)
- `<div id="TurbinenPanel"> ... </div>`
  - **Turbinentyp & Nabenhöhe:** Auswahl verschiedener Turbinen und deren Parameter.
  - **Rotor- und TSR-Anzeige:** Zeigt aktuelle Werte an.
  - **Wake- und Einflussbereich:** Einstellungen für Wake-Region und Einflussradius.
  - **Berechnungsmodelle:** Auswahl von Stall- und EndEffects-Modellen.
  - **Komponenten:** Auswahl, ob Tower und Hub berücksichtigt werden.
  - **Toggle-Button:** Panel ein-/ausklappbar.

### 5. Terminal Output Panel
- `<div id="terminal-output"> ... </div>`
  - Zeigt Ausgaben und Statusmeldungen des Backends an.

### 6. OpenFOAM Control Buttons
- **PRE-Bereich (links):**
  - Local->Remote, Allclean, Allpre
- **SOLVER & POST-Bereich (rechts):**
  - Allrun.slurm, Status, Allpost, Get VTK

### 7. Passphrase-Modal für SSH
- `<div id="passphrase-modal-container"> ... </div>`
  - Eingabe der SSH-Passphrase und Serververbindungsdaten (Root Folder, Username, Host, Remote Directory).

### 8. JavaScript-Einbindung
- `<script type="module" src="/src/main.js"></script>`
  - Bindet die Hauptlogik und Interaktivität ein.

---

## Hinweise zur Erweiterung und Anpassung

- **IDs und Klassen:**
  - Die IDs der HTML-Elemente sind exakt auf die Logik in `main.js` abgestimmt. Änderungen an den IDs erfordern Anpassungen im JavaScript.
- **Panels und Buttons:**
  - Die Panels sind einklappbar und können um weitere Parameter oder Einstellungen ergänzt werden.
- **Modale:**
  - Das Passphrase-Modal kann erweitert werden, um weitere Authentifizierungsoptionen oder Verbindungsparameter zu unterstützen.
- **Responsivität:**
  - Die Struktur ist für Desktop optimiert, kann aber mit CSS-Änderungen responsiv gestaltet werden.

---

## Abhängigkeiten

- [OpenLayers](https://openlayers.org/) (über das eingebundene JavaScript)
- Die eigentliche Logik wird über `src/main.js` bereitgestellt.
- Die Styles werden über die eingebundenen CSS-Dateien geladen (z.B. `styles/style.css`).

---

## Fazit

`index.html` stellt die komplette Benutzeroberfläche für die VentusFlowWebGUI bereit. Sie ist so strukturiert, dass alle wichtigen Interaktions- und Eingabeelemente für die Simulation, Steuerung und Visualisierung von Windparks mit OpenFOAM enthalten sind. Die eigentliche Funktionalität wird durch das zugehörige JavaScript und CSS ergänzt.
