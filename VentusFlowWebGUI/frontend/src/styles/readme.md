# Author: Malte Schudek
# Repository: https://github.com/malte-code/VentusFlow
# File: frontend/src/styles/readme.md

# README: frontend/src/styles/style.css

## Übersicht

Die Datei `style.css` enthält das gesamte Styling für das Frontend der VentusFlowWebGUI. Sie definiert das Layout, die Farben, die Größen und das Aussehen aller zentralen UI-Komponenten wie Karte, Toolbar, Panels, Terminal, Modale und Buttons. Das CSS sorgt für eine übersichtliche, moderne und funktionale Benutzeroberfläche.

---

## Hauptbestandteile und Struktur

### 1. CSS-Variablen
- Definiert zentrale Layoutgrößen wie Toolbar-Höhe, Panel-Breite, Terminal-Höhe und Margins als CSS-Variablen (`:root`).

### 2. Grundlayout
- **Body/HTML:** Setzt Margin und Höhe auf 100% für ein flexibles Layout.
- **#map:** Positioniert die Karte absolut, sodass sie den Hauptbereich zwischen Toolbar und Terminal einnimmt.

### 3. Toolbar
- **#toolbar:** Fixiert die Toolbar am oberen Rand, sorgt für horizontale Ausrichtung und Styling der Bedienelemente.
- **Dropdowns, Slider, Buttons:** Einheitliche Größen, Abstände und Hover-Effekte für eine intuitive Bedienung.

### 4. Side Panels (Parameter- und Turbinenpanel)
- **#PanelRight, #TurbinenPanel:** Feste Breite, Höhe und Positionierung links/rechts. Panels sind ein-/ausklappbar und enthalten strukturierte Parameterzeilen.
- **Toggle-Buttons:** Für das Ein- und Ausklappen der Panels, mit Hover-Effekt.
- **Parameterzeilen:** Einheitliches Styling für Labels, Inputs, Selects und Checkboxen.

### 5. Terminal und OpenFOAM Control
- **#terminal-output:** Fixiert am unteren Rand, nimmt die Breite zwischen den Panels ein. Schwarzer Hintergrund, grüne Schrift für klassischen Terminal-Look.
- **#OFLeftButtons, #OFRightButtons:** Steuerungsbereiche für OpenFOAM-Kommandos, jeweils links und rechts neben dem Terminal.

### 6. Modale (Passwort/Passphrase)
- **#passphrase-modal-container, #password-modal-container:** Zentrierte, halbtransparente Overlays mit abgerundeten, weißen Modalfenstern für SSH-Passworteingabe und Verbindungsdaten.
- **Formularelemente:** Einheitliche Eingabefelder und Buttons mit klaren Hover-Effekten.

### 7. Progress Bar
- **#progressContainer, #progressBar:** Zeigt Fortschritt bei Export/Simulation an.

### 8. Sonstiges
- **Tooltip, nicht genutzte Modale:** Platz für zukünftige Erweiterungen.
- **Import von OpenLayers-Styles:** Stellt sicher, dass die OpenLayers-Karte korrekt dargestellt wird.

---

## Hinweise zur Anpassung und Erweiterung

- **Responsivität:** Das Layout ist für Desktop optimiert, kann aber durch Anpassung der Variablen und Media Queries responsiv gestaltet werden.
- **Farbschema:** Farben und Größen können zentral über die CSS-Variablen angepasst werden.
- **Komponenten:** Neue Panels, Buttons oder Modale können einfach im bestehenden Stil ergänzt werden.
- **OpenLayers:** Der Import von `ol/ol.css` ist notwendig für die korrekte Darstellung der Karte und Vektorfeatures.

---

## Fazit

`style.css` sorgt für ein klares, modernes und funktionales Erscheinungsbild der VentusFlowWebGUI. Die Datei ist modular aufgebaut und ermöglicht eine einfache Anpassung und Erweiterung des Frontend-Designs.
