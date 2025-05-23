/*
Author: Malte Schudek
Repository: https://github.com/malte-code/VentusFlow
File: frontend/src/main.js
*/

// ======================================================================
// Global Styles
// 
// Importiere die globalen CSS-Stile der Anwendung.
import './styles/style.css';

// ======================================================================
// OpenLayers Style- und POINT Geometrie-Klassen
// 
// Diese Klassen werden für das Styling von Vektorfeatures verwendet.
// - Style: Basisklasse für die Definition von Stilregeln.
// - Icon: Zeigt Bild-Symbole (z. B. für Icons) an.
// - Stroke, RegularShape, Fill: Für Linien, geometrische Formen (z. B. Pfeilköpfe) und Füllungen.
import { Style, Icon, Stroke, RegularShape, Fill, Text } from 'ol/style';
// Point: Zum Erzeugen von Punkt-Geometrien, z. B. für den Pfeilkopf.
import Point from 'ol/geom/Point';
// Definiert einen Icon-Stil für Windturbinen. Dieser Stil kann dann 
// auf Punktfeatures angewendet werden, um statt eines einfachen Punktes 
// ein Windturbinen-Symbol anzuzeigen.
import windturbinenIcon from '../assets/windturbine.svg';
const turbineIconStyle = new Style({
  image: new Icon({
    src: windturbinenIcon, // Pfad zum SVG-Icon (relativ zur index.html)
    scale: 0.5,                    // Passe den Skalierungsfaktor an
    anchor: [0.5, 0.9],              // Zentriert horizontal und am unteren Rand verankert
  }),
});

// ======================================================================
// OpenLayers Feature- und POLYGON Geometrie-Klassen
//
// - Feature: Erzeugt einzelne Vektorfeatures.
// - LineString: Repräsentiert Liniengeometrien, z. B. für den Windrichtungspfeil.
// - Polygon: Zum Erzeugen von Polygonen, z. B. Rechtecke.
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import { Polygon } from 'ol/geom';
// Definiere einen Stil für Rechtecke/Quadrate (Polygone)
const rectangleStyle = function(feature) {
  // For text positioning, we'll use the center of the rectangle
  const geometry = feature.getGeometry();
  const extent = geometry.getExtent();
  const centerX = (extent[0] + extent[2]) / 2;
  const centerY = (extent[1] + extent[3]) / 2;
  
  return [
    // Base style (existing stroke and fill)
    new Style({
      stroke: new Stroke({
        color: 'blue',  // Rahmenfarbe
        width: 2        // Rahmenbreite
      }),
      fill: new Fill({
        color: 'rgba(0, 0, 255, 0.1)'  // Füllfarbe mit Transparenz
      })
    }),
    // Text style for label
    new Style({
      text: new Text({
        text: 'Simulation Area',
        font: '16px Arial',
        fill: new Fill({
          color: 'rgba(0, 0, 255, 0.8)'
        }),
        stroke: new Stroke({
          color: 'white',
          width: 3
        }),
        offsetY: 0,
        geometry: new Point([centerX, centerY])
      })
    })
  ];
};

// ======================================================================
// Karten- und Layer-Klassen
// 
// Diese Klassen ermöglichen das Erstellen einer Karte und das Hinzufügen verschiedener Layer.
// - Map: Repräsentiert die Karte.
// - View: Bestimmt den Blickwinkel und die Zoomstufe.
// - TileLayer: Wird für Hintergrundkarten (z. B. OSM) verwendet.
// - OSM: OpenStreetMap als Kartenquelle.
import { Map, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import OSM from 'ol/source/OSM';

// ======================================================================
// Vektor-Layer und Quellen
// 
// - VectorSource: Speichert Vektorfeatures, z. B. gezeichnete Formen.
// - VectorLayer: Rendert die Vektorfeatures auf der Karte.
import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';

// ======================================================================
// Interaktionen: Zeichnen und Auswählen
// 
// - Draw: Ermöglicht das Zeichnen von Features (z. B. Rechtecke).
// - createRegularPolygon: Hilfsfunktion für regelmäßige Polygone.
// - Select: Ermöglicht das Auswählen von Features per Klick.
// - click: Definiert die Klickbedingung für die Auswahl.
import Draw, { createRegularPolygon } from 'ol/interaction/Draw';
import Select from 'ol/interaction/Select';
import { click } from 'ol/events/condition';

// ======================================================================
// Interaktionen: Verschieben
//
// - Translate: Ermöglicht das Verschieben von Features.
// - Collection: Hilft beim Verwalten von Gruppen von Features.
import Translate from 'ol/interaction/Translate';
import Collection from 'ol/Collection';
import { rotate } from 'ol/coordinate';
import { parse } from 'ol/expr/expression';

// ======================================================================
// Globale Variablen
// ======================================================================
let drawInteraction = null;       // Interaktion zum Zeichnen von Formen
let currentShape = null;
let squareAngleRadian = null;     // Winkel des Shapes (in Radiant)
let translateInteraction = null;  // Interaktion zum Verschieben des Shapes
let activeLayer = 'none';         // Aktuell aktiver Layer ('points', 'simarea', 'none')
let editModeActive = false;       // Toggle-Status für Edit-Modus

// Globale Variablen für die Zeichenebenen
let turbineSource = null;         // Vektorquelle für Turbinen (Punkte)
let turbineLayer = null;          // Vektorlayer für Turbinen
let simAreaSource = null;         // Vektorquelle für Simulationsgebiet (Rechtecke/Quadrate)
let simAreaLayer = null;          // Vektorlayer für Simulationsgebiet

// ======================================================================
// Karten- und Zeichenebenen-Erstellung
// ======================================================================

/**
 * Erstellt die Basiskarte
 */
function erstelleKarte() {
  const rasterLayer = new TileLayer({
    source: new OSM(),
  });
  const karte = new Map({
    target: 'map',
    layers: [rasterLayer],
    view: new View({
      center: [0, 0],
      zoom: 2,
    }),
  });
  return karte;
}
const map = erstelleKarte();

/**
 * Erstellt die Zeichenebenen für die gezeichneten Features
 */
function erstelleZeichenEbenen(map) {
  // Layer für Turbinen (Punkte)
  turbineSource = new VectorSource();
  turbineLayer = new VectorLayer({
    source: turbineSource,
    style: turbineIconStyle,
    zIndex: 10 // Standard z-index
  });
  
  // Layer für Simulationsgebiet (Rechtecke/Quadrate)
  simAreaSource = new VectorSource();
  simAreaLayer = new VectorLayer({
    source: simAreaSource,
    style: rectangleStyle,
    zIndex: 10 // Standard z-index
  });
  
  // Layer zur Karte hinzufügen
  map.addLayer(simAreaLayer);
  map.addLayer(turbineLayer);
}
erstelleZeichenEbenen(map);

/**
 * Erstellt WakeLayer für wakerectangles// Neuen VectorSource und Layer für "RectangleWake" definieren:
 *  */
const wakeSource = new VectorSource();
const wakeLayer = new VectorLayer({
  source: wakeSource,
  style: function(feature) {
    // Get the center of the wake polygon for text positioning
    const extent = feature.getGeometry().getExtent();
    const centerX = (extent[0] + extent[2]) / 2;
    const centerY = (extent[1] + extent[3]) / 2;
    
    return [
      // Base style (existing stroke and fill)
      new Style({
        stroke: new Stroke({
          color: 'red',
          width: 2,
        }),
        fill: new Fill({
          color: 'rgba(255, 0, 0, 0.1)',
        })
      }),
      // Text style for label
      new Style({
        text: new Text({
          text: 'Wake Region',
          font: '14px Arial',
          fill: new Fill({
            color: 'rgba(255, 0, 0, 0.8)'
          }),
          stroke: new Stroke({
            color: 'white',
            width: 3
          }),
          offsetY: 0,
          // Position at center of polygon
          geometry: new Point([centerX, centerY])
        })
      })
    ];
  },
  zIndex: 5 // Lower than main layers
});
map.addLayer(wakeLayer);

/**
 * Erstellt SphereRadiusLayer zur Visualisierung des Einflussbereichs von Turbinen
 */
const sphereRadiusSource = new VectorSource();
const sphereRadiusLayer = new VectorLayer({
  source: sphereRadiusSource,
  style: function(feature) {
    // For text positioning, we can use the center of the circle
    // Since each circle is created around a turbine, we can get its center from the geometry
    const geometry = feature.getGeometry();
    const extent = geometry.getExtent();
    const centerX = (extent[0] + extent[2]) / 2;
    const centerY = (extent[1] + extent[3]) / 2;
    
    return [
      // Base style (existing stroke and fill)
      new Style({
        stroke: new Stroke({
          color: 'rgba(0, 128, 255, 0.8)', // Blauer Rahmen
          width: 1.5,
          dashArray: [5, 5] // Gestrichelte Linie
        }),
        fill: new Fill({
          color: 'rgba(0, 128, 255, 0.1)', // Leicht transparentes Blau
        })
      }),
      // Text style for label
      new Style({
        text: new Text({
          text: 'Sphere Radius',
          font: '12px Arial',
          fill: new Fill({
            color: 'rgba(0, 128, 255, 0.8)'
          }),
          stroke: new Stroke({
            color: 'white',
            width: 3
          }),
          offsetY: 0,
          geometry: new Point([centerX, centerY])
        })
      })
    ];
  },
  zIndex: 5 // Lower than main layers
});
map.addLayer(sphereRadiusLayer);

// ======================================================================
// Layer Hierarchy Management
// ======================================================================

/**
 * Setzt den aktiven Layer basierend auf der Dropdown-Auswahl und passt die Ebenen entsprechend an
 * @param {string} selectionType - Der im Dropdown ausgewählte Typ ('Point', 'Rectangle', 'Square', 'None')
 */
function setActiveLayer(selectionType) {
  // Zurücksetzen der z-Indizes
  turbineLayer.setZIndex(10);
  simAreaLayer.setZIndex(10);
  
  // Aktiven Layer basierend auf der Auswahl setzen
  if (selectionType === 'Point') {
    activeLayer = 'points';
    turbineLayer.setZIndex(20); // Turbinen nach oben
    console.log('Turbinen-Layer ist nun aktiv und wurde nach oben verschoben');
  } else if (selectionType === 'Rectangle' || selectionType === 'Square') {
    activeLayer = 'simarea';
    simAreaLayer.setZIndex(20); // Simulationsgebiet nach oben
    console.log('Simulationsgebiet-Layer ist nun aktiv und wurde nach oben verschoben');
  } else {
    activeLayer = 'none';
    console.log('Kein Layer ist aktiv');
  }
  
  // Aktualisiere auch die Select-Interaktion, falls vorhanden und Edit-Modus aktiv
  if (editModeActive) {
    if (selectInteraction) {
      // Selektierte Features zurücksetzen
      selectInteraction.getFeatures().clear();
      map.removeInteraction(selectInteraction);
    }
    
    // Nur neu aktivieren, wenn ein aktiver Layer existiert
    if (activeLayer !== 'none') {
      aktiviereSelectInteraktion();
    } else {
      selectInteraction = null;
    }
  }
  
  // Translate-Interaktion zurücksetzen
  if (translateInteraction) {
    map.removeInteraction(translateInteraction);
    translateInteraction = null;
  }
}

// ======================================================================
// Tooltip
// ======================================================================


// ======================================================================
// Toolbar-Setup
// ======================================================================

/**
 * Initialisiert die Toolbar und bindet die Event-Listener
 */
function einrichtenToolbar() {
  const formenDropdown = document.getElementById('shapesDropdown');
  const clearShapesButton = document.getElementById('clearShapesButton');
  const windSlider = document.getElementById('windDirectionSlider');
  const selectShapesButton = document.getElementById('selectShapesButton');
  
  einrichtenFormenDropdown(formenDropdown);
  einrichtenSelectInteraktion(selectShapesButton);
  einrichtenWindSlider(windSlider);
  einrichtenLoeschenButton(clearShapesButton);
  
  // Neue Events für Breite und Tiefe: Bei Änderung wird das Shape entsprechend skaliert
  document.getElementById('widthInput').addEventListener('change', () => {
    if (!currentShape) return;
    const newWidth = parseFloat(document.getElementById('widthInput').value);
    const dimensionen = ermittleDimensionen(currentShape.getGeometry(), squareAngleRadian);
    const factor = newWidth / dimensionen.width;
    skaliereBreite(factor);
  });
  document.getElementById('depthInput').addEventListener('change', () => {
    if (!currentShape) return;
    const newDepth = parseFloat(document.getElementById('depthInput').value);
    const dimensionen = ermittleDimensionen(currentShape.getGeometry(), squareAngleRadian);
    const factor = newDepth / dimensionen.depth;
    skaliereTiefe(factor);
  });
}
einrichtenToolbar();

// ======================================================================
// Panels (events)
// ======================================================================
// Toggle-Funktion für das togglePanelRight
document.getElementById('togglePanelRight').addEventListener('click', function() {
  const panel = document.getElementById('PanelRight');
  panel.classList.toggle('collapsed');
  
  // Optional: Ändere den Buttontext, um den aktuellen Zustand anzuzeigen
  const btn = document.getElementById('togglePanelRight');
  if (panel.classList.contains('collapsed')) {
    btn.textContent = '»'; // Zeigt "expand" an
  } else {
    btn.textContent = '«'; // Zeigt "collapse" an
  }
});

document.getElementById('toggleTurbinenPanel').addEventListener('click', function() {
  const panel = document.getElementById('TurbinenPanel');
  panel.classList.toggle('collapsed');
  
  const btn = document.getElementById('toggleTurbinenPanel');
  if (panel.classList.contains('collapsed')) {
    btn.textContent = '«'; // Panel ist eingeklappt, Button zeigt "öffnen"
  } else {
    btn.textContent = '»'; // Panel ist ausgeklappt, Button zeigt "schließen"
  }
});

//turbines

//Turbinen-Parameter
const turbineSpecs = {
  NREL6MW_17: {
    rotorRadius: 77,
    tipSpeedRatio: 6.8,
    hubHeights: [90, 100, 110],

    // mögliche zukünftige Werte (siehe backend process_input.py und offshorewindpark_VentusFlow/constant/*TurbineType*/* for input structure of full turbinedata (airfoils, elementProfiles, elementData (turbinesFoam input (https://github.com/fcgaleazzo/turbinesFoam))) ))
    //(im backend) sollten eine Werte beartet werden.
    //  Werte sollten in Abhängigkeit der initalConditions sein für Turbine1. Turbine2 (im wake von Turbine1) könnte während der Simulation andere Werte haben. Die Simulation ist Laufzeitmodifikation "runTimeModifiable yes;" mit dem output der v_mean in der Rotorebene könnte pro Zeitschritt tsr berechnet werden und in fvOptions eingesetzt werden. 
    // nBlades: 3,                // Anzahl der Rotorblätter
    // omega: 9.2,                // Winkelgeschwindigkeit [rad/s]
    // //rpm: omega * 60 / (2 * Math.PI), // Drehzahl [U/min]
    // pitchAngle: 2.0,           // Blattwinkel [Grad]
    // yawAngle: 0.0,             // Gierwinkel [Grad]
    // bladeGeometry: [           // Geometrie der Rotorblätter an verschiedenen Radien
    //   { r: 3.5, chord: 4.2, twist: 13.5, airfoil: "FFA-W3-301" },   // r: Radius [m], chord: Profiltiefe [m], twist: Verdrehung [Grad], airfoil: Profilname
    //   { r: 10, chord: 4.0, twist: 10.0, airfoil: "FFA-W3-301" },
    //   { r: 30, chord: 3.0, twist: 5.0, airfoil: "NACA64-618" },
    //   // ... weitere Radialpunkte
    //]
  },

  NREL15MW_17: {
    rotorRadius: 110,
    tipSpeedRatio: 8.5,
    hubHeights: [140, 150, 160], // Mehrere mögliche Nabenhöhen

  }
};

//Parameter-Panel
document.getElementById('turbineTypeDropdown').addEventListener('change', () => {
  const turbineType = document.getElementById('turbineTypeDropdown').value;
  const specs = turbineSpecs[turbineType];
  if (specs) {
    document.getElementById('rotorRadius').textContent = specs.rotorRadius;
    document.getElementById('tipSpeedRatio').textContent = specs.tipSpeedRatio;

    // Hubhöhen-Dropdown füllen
    const hubHeightDropdown = document.getElementById('hubHeightDropdown');
    hubHeightDropdown.innerHTML = '';
    specs.hubHeights.forEach(hh => {
      const option = document.createElement('option');
      option.value = hh;
      option.textContent = hh;
      hubHeightDropdown.appendChild(option);
    });
    // Optional: ersten Wert als Standard setzen
    hubHeightDropdown.value = specs.hubHeights[0];
  }
});


// Wake-Regionen
document.getElementById('wakeDepth').addEventListener('change', () => {
  updateWakeLayer(); // Aktualisiert die Wake-Regionen
});

document.getElementById('sphereRadius').addEventListener('change', () => {
  updateWakeLayer(); // Aktualisiert die Wake-Regionen
});


// ======================================================================
// Formen-Zeichnen und -Bearbeiten im drawlayer
// ======================================================================

/**
 * Bindet den Event-Listener an das Dropdown zur Formenauswahl.
 * Für Rechtecke/Quadrate: Entferne das alte Rechteck (currentShape), falls vorhanden.
 * Für Punkte: Nichts ändern (Punkte werden separat gespeichert).
 */
function einrichtenFormenDropdown(dropdown) {
  dropdown.addEventListener('change', (event) => {
    const ausgewählteForm = event.target.value;
    console.log(`Ausgewählte Form: ${ausgewählteForm}`);
    
    // Layer-Hierarchie aktualisieren
    setActiveLayer(ausgewählteForm);
    
    if (ausgewählteForm !== 'None') {
      hinzufuegenZeichenInteraktion(ausgewählteForm);
    } else {
      // Bei "None" die Zeicheninteraktion entfernen
      if (drawInteraction) {
        map.removeInteraction(drawInteraction);
        drawInteraction = null;
      }
    }
  });
}

/**
 * Fügt die Zeichnungs-Interaktion hinzu, um Formen zu erstellen
 */
function hinzufuegenZeichenInteraktion(formTyp) {
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
  }
  
  let source;
  if (formTyp === 'Point') {
    source = turbineSource;
  } else {
    source = simAreaSource;
  }
  
  if (formTyp === 'Rectangle') {
    drawInteraction = new Draw({
      source: source,
      type: 'LineString',
      maxPoints: 2,
      geometryFunction: (koordinaten, geometry) => {
        if (!geometry) {
          geometry = new Polygon([]);
        }
        const [start, end] = koordinaten;
        const minX = Math.min(start[0], end[0]);
        const maxX = Math.max(start[0], end[0]);
        const minY = Math.min(start[1], end[1]);
        const maxY = Math.max(start[1], end[1]);
        geometry.setCoordinates([[
          [minX, minY], [maxX, minY],
          [maxX, maxY], [minX, maxY],
          [minX, minY]
        ]]);
        return geometry;
      }
    });
  } else if (formTyp === 'Square') {
    drawInteraction = new Draw({
      source: source,
      type: 'Circle',
      geometryFunction: createRegularPolygon(4)
    });
  } else if (formTyp === 'Point') {
    drawInteraction = new Draw({
      source: source,
      type: 'Point',
      style: null // Verwende den Layer-Stil (Turbine-Icon) – nicht den von Draw gesetzten
    });
  } else {
    console.warn(`Unbekannter Formtyp: ${formTyp}`);
    return;
  }
  
  // Beim Starten des Zeichnens: Nur bei Rechtecken/Quadraten wird das alte Rechteck entfernt.
  drawInteraction.on('drawstart', () => {
    console.log(`Zeichenvorgang für ${formTyp} gestartet`);
  });
  
  // Beim Zeichnen:
  drawInteraction.on('drawend', (event) => {
    if (formTyp === 'Point') {
      // Read turbine panel parameter values
      const turbineParams = {
        turbineType: document.getElementById('turbineTypeDropdown').value,
        hubHeight: parseFloat(document.getElementById('hubHeight').value),
        rotorRadius: parseFloat(document.getElementById('rotorRadius').textContent),
        tipSpeedRatio: parseFloat(document.getElementById('tipSpeedRatio').textContent),
        sphereRadius: parseFloat(document.getElementById('sphereRadius').value)
      };

      // Attach parameters to the point feature
      event.feature.setProperties(turbineParams);
      // Für Punkte: Füge sie hinzu, ohne currentShape zu überschreiben.
      event.feature.setStyle(null); // Damit der Layer-Stil greift
      
      // Sicherstellen, dass der Punkt im Source ist, bevor wir die Layer aktualisieren
      // Kleine Verzögerung, um sicherzustellen, dass wake und sphere aktualisiert werden
      setTimeout(() => {
        updateWakeLayer(); // Aktualisiere die Wake-Layer
        updateSphereRadiusLayer(); // Aktualisiere die Sphere-Radius-Layer
      }, 1);
    } 
    else if (formTyp === 'Rectangle' || formTyp === 'Square') {
      if (currentShape) {
        simAreaSource.removeFeature(currentShape);
        console.log('Vorheriges Rechteck/Quadrat entfernt (Zeichenvorgang beendet)');
      }
      currentShape = event.feature;
      const coords = currentShape.getGeometry().getCoordinates()[0];
      updateWakeLayer();
      updateSphereRadiusLayer(); // Aktualisiere Sphere-Radius nach dem Zeichnen
      berechneWinkel(coords);
      // Setze den Winkel initial auf 0° (du kannst dies anpassen)
      squareAngleRadian = 0;
      aktualisiereWindSlider();
      rotiereShape();
      aktualisierePfeil();
      hinzufuegenTranslateInteraktion();
      aktualisiereDimensionenFelder();

      
    }
  });
  
  map.addInteraction(drawInteraction);
  console.log(`Zeichen-Interaktion für ${formTyp} aktiviert`);
}


/**
 * Fügt die Translate-Interaktion hinzu, um das aktuelle Shape zu verschieben
 * Translation wird nur erlaubt, wenn der entsprechende Formtyp im Dropdown ausgewählt ist
 */
function hinzufuegenTranslateInteraktion() {
  if (translateInteraction) {
    map.removeInteraction(translateInteraction);
  }
  
  if (currentShape) {
    translateInteraction = new Translate({
      features: new Collection([currentShape]),
      // Filter-Funktion, die vor jeder Translation prüft, ob der Shape-Typ erlaubt ist
      filter: function(feature) {
        // Nur Features aus dem aktiven Layer können verschoben werden
        const featureType = feature.getGeometry().getType();
        
        if (activeLayer === 'points' && featureType === 'Point') {
          return true;
        } else if (activeLayer === 'simarea' && featureType === 'Polygon') {
          return true;
        }
        
        console.log(`Verschieben nicht erlaubt: ${featureType} ist nicht im aktiven Layer ${activeLayer}`);
        return false;
      }
    });
    
    map.addInteraction(translateInteraction);
    translateInteraction.on('translateend', () => {
      console.log('Shape verschoben');
      aktualisierePfeil();
      aktualisiereDimensionenFelder();
      updateWakeLayer();
      updateSphereRadiusLayer();
    });
    console.log('Translate-Interaktion hinzugefügt für den aktiven Layer');
  }
}

// ======================================================================
// Berechnungen (Winkel, Rotation, Dimensionen)
// ======================================================================

/**
 * Berechnet den Winkel des Shapes anhand der ersten beiden Punkte
 */
function berechneWinkel(koordinaten) {
  const [p1, p2] = koordinaten;
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  let radians = Math.atan2(dy, dx);
  if (radians < 0) {
    radians += 2 * Math.PI;
  }
  squareAngleRadian = parseFloat(radians.toFixed(10));
  console.log(`Berechneter Winkel: ${(squareAngleRadian * 180 / Math.PI).toFixed(2)}°`);
}

/**
 * Berechnet die Dimensionen (Breite und Tiefe) des Shapes
 * Breite: Abstand orthogonal zur Windrichtung
 * Tiefe: Abstand entlang der Windrichtung
 * @param {ol/geom/Geometry} geometry 
 * @param {number} windAngle - in Radiant
 * @returns {object} { width, depth }
 */
function berechneDimensionen(geometry, windAngle) {
  const coords = geometry.getCoordinates()[0];
  const cosA = Math.cos(windAngle);
  const sinA = Math.sin(windAngle);
  let minParallel = Infinity, maxParallel = -Infinity;
  let minOrthogonal = Infinity, maxOrthogonal = -Infinity;
  
  coords.forEach(coord => {
    const x = coord[0], y = coord[1];
    // Projektion entlang der Windrichtung (parallel)
    const projParallel = x * cosA + y * sinA;
    // Projektion orthogonal (Breite)
    const projOrthogonal = -x * sinA + y * cosA;
    if (projParallel < minParallel) minParallel = projParallel;
    if (projParallel > maxParallel) maxParallel = projParallel;
    if (projOrthogonal < minOrthogonal) minOrthogonal = projOrthogonal;
    if (projOrthogonal > maxOrthogonal) maxOrthogonal = projOrthogonal;
  });
  
  return {
    depth: maxParallel - minParallel,
    width: maxOrthogonal - minOrthogonal
  };
}

/**
 * Rotiert das aktuelle Shape basierend auf squareAngleRadian
 */
function rotiereShape() {
  if (currentShape && squareAngleRadian !== null) {
    const geometry = currentShape.getGeometry();
    const center = geometry.getInteriorPoint().getCoordinates();
    const currentRotation = geometry.get('rotation') || 0;
    geometry.rotate(-currentRotation, center);
    geometry.rotate(squareAngleRadian, center);
    geometry.set('rotation', squareAngleRadian);
    console.log(`Shape rotiert zu ${(squareAngleRadian * 180 / Math.PI).toFixed(2)}°`);
    aktualisierePfeil();
    updateWakeLayer();
  } else {
    console.warn('Kein Shape oder Winkel definiert, um zu rotieren');
  }
}

/**
 * Ermittelt die Breite (orthogonal zur Windrichtung) und Tiefe (parallel zur Windrichtung)
 * basierend auf den Eckpunkten des Polygons.
 * @param {ol/geom/Geometry} geometry - Das Geometry-Objekt des Shapes
 * @param {number} windAngle - Der Winkel (in Radiant) für die Windrichtung
 * @returns {object} { width, depth }
 */
function ermittleDimensionen(geometry, windAngle) {
  const coords = geometry.getCoordinates()[0];
  const cosA = Math.cos(windAngle);
  const sinA = Math.sin(windAngle);
  let minParallel = Infinity, maxParallel = -Infinity;
  let minOrthogonal = Infinity, maxOrthogonal = -Infinity;
  
  coords.forEach(coord => {
    const x = coord[0], y = coord[1];
    // Projektion entlang der Windrichtung (parallel)
    const projParallel = x * cosA + y * sinA;
    // Projektion orthogonal (Breite)
    const projOrthogonal = -x * sinA + y * cosA;
    if (projParallel < minParallel) minParallel = projParallel;
    if (projParallel > maxParallel) maxParallel = projParallel;
    if (projOrthogonal < minOrthogonal) minOrthogonal = projOrthogonal;
    if (projOrthogonal > maxOrthogonal) maxOrthogonal = projOrthogonal;
  });
  
  return {
    depth: maxParallel - minParallel,
    width: maxOrthogonal - minOrthogonal
  };
}

/**
 * Aktualisiert die Input-Felder für Breite und Tiefe
 */
function aktualisiereDimensionenFelder() {
  if (currentShape && squareAngleRadian !== null) {
    const dimensionen = ermittleDimensionen(currentShape.getGeometry(), squareAngleRadian);
    document.getElementById('widthInput').value = dimensionen.width.toFixed(2);
    document.getElementById('depthInput').value = dimensionen.depth.toFixed(2);
  }
}

/**
 * Skaliert das aktuelle Shape in Breite (orthogonal zur Windrichtung)
 * @param {number} faktor - Skalierungsfaktor für die Breite
 */
function skaliereBreite(faktor) {
  if (!currentShape) return;
  const geometry = currentShape.getGeometry();
  const center = geometry.getInteriorPoint().getCoordinates();
  const coords = geometry.getCoordinates()[0];
  const cosA = Math.cos(squareAngleRadian);
  const sinA = Math.sin(squareAngleRadian);
  
  const neueKoords = coords.map(coord => {
    const dx = coord[0] - center[0];
    const dy = coord[1] - center[1];
    // Projektion in Windrichtung (parallel) – bleibt unverändert
    const projParallel = dx * cosA + dy * sinA;
    // Projektion orthogonal (Breite) – wird skaliert
    const projOrth = -dx * sinA + dy * cosA;
    const newParallelX = projParallel * cosA;
    const newParallelY = projParallel * sinA;
    const newOrthX = projOrth * faktor * (-sinA);
    const newOrthY = projOrth * faktor * cosA;
    return [center[0] + newParallelX + newOrthX, center[1] + newParallelY + newOrthY];
  });
  if (neueKoords.length > 0) {
    neueKoords[neueKoords.length - 1] = neueKoords[0];
  }
  geometry.setCoordinates([neueKoords]);
  console.log(`Shape Breite skaliert um Faktor ${faktor}`);
  aktualisierePfeil();
  aktualisiereDimensionenFelder();
}

/**
 * Skaliert das aktuelle Shape in Tiefe (parallel zur Windrichtung)
 * @param {number} faktor - Skalierungsfaktor für die Tiefe
 */
function skaliereTiefe(faktor) {
  if (!currentShape) return;
  const geometry = currentShape.getGeometry();
  const center = geometry.getInteriorPoint().getCoordinates();
  const coords = geometry.getCoordinates()[0];
  const cosA = Math.cos(squareAngleRadian);
  const sinA = Math.sin(squareAngleRadian);
  
  const neueKoords = coords.map(coord => {
    const dx = coord[0] - center[0];
    const dy = coord[1] - center[1];
    // Projektion in Windrichtung (parallel) – wird skaliert
    const projParallel = dx * cosA + dy * sinA;
    // Projektion orthogonal – bleibt unverändert
    const projOrth = -dx * sinA + dy * cosA;
    const newParallelX = projParallel * faktor * cosA;
    const newParallelY = projParallel * faktor * sinA;
    const newOrthX = projOrth * (-sinA);
    const newOrthY = projOrth * cosA;
    return [center[0] + newParallelX + newOrthX, center[1] + newParallelY + newOrthY];
  });
  if (neueKoords.length > 0) {
    neueKoords[neueKoords.length - 1] = neueKoords[0];
  }
  geometry.setCoordinates([neueKoords]);
  console.log(`Shape Tiefe skaliert um Faktor ${faktor}`);
  aktualisierePfeil();
  aktualisiereDimensionenFelder();
}



// ======================================================================
// Slider- und Eingabe-Interaktionen
// ======================================================================

/**
 * Initialisiert den Windrichtungs-Slider
 */
function einrichtenWindSlider(slider) {
  slider.addEventListener('input', (event) => {
    const radians = parseFloat(event.target.value) * Math.PI / 180;
    squareAngleRadian = radians;
    rotiereShape();
    aktualisierePfeil();
    aktualisiereWindSlider();
    slider.value = (squareAngleRadian * 180 / Math.PI).toFixed(2);
  });
  console.log('Windrichtungs-Slider eingerichtet');
}

/**
 * Aktualisiert die Anzeige des Windrichtungs-Sliders
 */
function aktualisiereWindSlider() {
  if (currentShape) {
    const slider = document.getElementById('windDirectionSlider');
    slider.value = (squareAngleRadian * 180 / Math.PI).toFixed(2);
    document.getElementById('windDirectionValue').textContent =
      `${(squareAngleRadian * 180 / Math.PI).toFixed(2)}°`;
  }
}

// ======================================================================
// Pfeil-Funktionen (Windrichtungspfeil)
// ======================================================================
function arrowStyleFunction(feature) {
  const geometry = feature.getGeometry();
  const coordinates = geometry.getCoordinates();
  const lastCoord = coordinates[coordinates.length - 1];
  // Berechne den Winkel des letzten Segments
  let rotation = 0;
  if (coordinates.length >= 2) {
    const penultimateCoord = coordinates[coordinates.length - 2];
    rotation = Math.atan2(penultimateCoord[1] - lastCoord[1], penultimateCoord[0] - lastCoord[0]);
    }
    return [
    // Style für die Linie:
    new Style({
      stroke: new Stroke({
        color: 'orange',
        width: 2,
      }),
    }),
    // Style für den Pfeilkopf:
    new Style({
      geometry: new Point(lastCoord),
      image: new RegularShape({
        fill: new Fill({ color: 'orange' }),
        points: 3,
        radius: 10,
        rotation: -rotation - Math.PI / 2, // 90° Rotation hinzufügen
        angle: 0,
      }),
    }),

    new Style({
      text: new Text({
        text: 'Windrichtung',
        font: '12px Arial',
        fill: new Fill({
          color: 'black',
        }),
        stroke: new Stroke({
          color: 'orange',
          width: 3,
        }),
        offsetY: 0,
      }),
      geometry: geometry,
    }),
  ];
}

/**
 * Erstellt ein Pfeil-Feature basierend auf dem Winkel, Mittelpunkt und der übergebenen Länge
 * @param {number} winkel - Winkel in Grad
 * @param {Array} center - [x, y]-Koordinaten des Mittelpunkts
 * @param {number} laenge - Die Länge des Pfeils
 * @returns {Feature}
 */
function erstellePfeilFeature(winkel, center, laenge, tiefe) {
  const offset = 0;
  const radians = (winkel * Math.PI) / 180;
  const startx = center[0] + ((tiefe/2)+offset) * Math.cos(radians);
  const starty = center[1] + ((tiefe/2)+offset) * Math.sin(radians);
  const endX = startx + ( tiefe/4) * Math.cos(radians);
  const endY = starty + ( tiefe/4) * Math.sin(radians);
  const koordinaten = [[endX, endY], [startx, starty]];
  return new Feature({
    geometry: new LineString(koordinaten),
  });
}


function aktualisierePfeil() {
  if (currentShape && squareAngleRadian !== null) {
    const center = currentShape.getGeometry().getInteriorPoint().getCoordinates();
    // Ermittle die Dimensionen, um die Tiefe zu erhalten
    const dimensionen = berechneDimensionen(currentShape.getGeometry(), squareAngleRadian);
    // Pfeillinienlänge = halbe Tiefe
    const laenge = dimensionen.depth / 4;
    const tiefe = dimensionen.depth;
    const pfeilFeature = erstellePfeilFeature(squareAngleRadian * 180 / Math.PI, center, laenge, tiefe);
    const pfeilSource = new VectorSource({
      features: [pfeilFeature],
    });
    if (arrowLayer) {
      map.removeLayer(arrowLayer);
    }
    arrowLayer = new VectorLayer({
      source: pfeilSource,
      style: arrowStyleFunction  // Hier wird der benutzerdefinierte Style angewendet
    });
    map.addLayer(arrowLayer);
    console.log(`Pfeil aktualisiert auf ${(squareAngleRadian * 180 / Math.PI).toFixed(2)}° mit Länge ${laenge}`);
  } else {
    console.warn('Kein Shape oder Winkel definiert, um den Pfeil zu erstellen');
  }
}


let arrowLayer = null;

// ======================================================================
// Wake-Rectangle-Funktionen
// ======================================================================
/**
 * Erstellt ein Wake-Rechteck (Polygon) um einen gegebenen Punkt.
 * Hier verwenden wir feste Maße (z. B. width = 100, height = 50). 
 * Diese Werte kannst Du natürlich anpassen.
 */
function createWakeRectangle(pointCoord, rotorRadius) {

  const sphereRadiusValue = parseFloat(document.getElementById('sphereRadius').value) * rotorRadius;
  const depthValue             = parseFloat(document.getElementById('wakeDepth').value)    * rotorRadius;

  const inletdepth = sphereRadiusValue;
  const wakedepth = depthValue;
  const halfwidth = sphereRadiusValue;
  // Define the rotation point based on the inlet depth
  const rotationPoint = [pointCoord[0], pointCoord[1]];

  const rectangleCoords = [
    [pointCoord[0] - wakedepth, pointCoord[1] - halfwidth],
    [pointCoord[0] + inletdepth, pointCoord[1] - halfwidth],
    [pointCoord[0] + inletdepth, pointCoord[1] + halfwidth],
    [pointCoord[0] - wakedepth, pointCoord[1] + halfwidth],
    [pointCoord[0] - wakedepth, pointCoord[1] - halfwidth]
  ];

  // Create the polygon and attach the rotation point as a property
  const polygon = new Polygon([rectangleCoords]);
  polygon.rotationPoint = rotationPoint;
  return polygon;
}

/**
 * Aktualisiert den WakeLayer:
 * - Löscht alle vorhandenen Features im wakeLayer.
 * - Durchläuft alle Punkt-Features im turbineSource und fügt für jeden ein Wake-Rechteck hinzu.
 */
function updateWakeLayer() {
  // Clear existing wake features
  wakeSource.clear();
  
  const pointFeatures = turbineSource.getFeatures();
  
  pointFeatures.forEach(pointFeature => {
    const coord = pointFeature.getGeometry().getCoordinates();
    // Get the rotorRadius from the feature’s properties
    const rotorRadius = pointFeature.get("rotorRadius");
    // Create the wake rectangle using the turbine’s rotorRadius
    const wakeRect = createWakeRectangle(coord, rotorRadius);
    wakeRect.rotate(squareAngleRadian, wakeRect.rotationPoint);
    const wakeFeature = new Feature({
      geometry: wakeRect
    });
    wakeSource.addFeature(wakeFeature);
  });
}

// ======================================================================
// Sphere-Radius-Funktionen (TODO add that sphereRadius dimension depends on Radius of turbine )
// ======================================================================

/**
 * Erstellt ein Kreispolygon um einen gegebenen Punkt mit dem angegebenen Radius.
 * @param {Array} center - Mittelpunkt des Kreises [x, y]
 * @param {number} radius - Radius des Kreises
 * @param {number} segments - Anzahl der Segmente (höher = glatter)
 * @returns {ol/geom/Polygon} Polygon in Kreisform
 */
function createCirclePolygon(center, radius, segments = 64) {
  const coords = [];
  const angleStep = 2 * Math.PI / segments;
  
  for (let i = 0; i < segments; i++) {
    const angle = i * angleStep;
    const x = center[0] + radius * Math.cos(angle);
    const y = center[1] + radius * Math.sin(angle);
    coords.push([x, y]);
  }
  
  // Schließen des Polygons
  coords.push(coords[0]);
  
  return new Polygon([coords]);
}

/**
 * Aktualisiert die SphereRadiusLayer:
 * - Löscht alle vorhandenen Features im sphereRadiusLayer
 * - Durchläuft alle Punkt-Features im turbineSource und fügt für jeden einen Kreis hinzu
 */
function updateSphereRadiusLayer() {
  // Alle bestehenden Sphere-Features entfernen
  sphereRadiusSource.clear();
  
  // Hole den aktuellen Wert für den Sphere-Radius
  const sphereRadiusValue = parseFloat(document.getElementById('sphereRadius').value);
  
  // Hole alle Punkt-Features aus dem turbineSource
  const pointFeatures = turbineSource.getFeatures();
  
  // Erstelle für jeden Punkt einen Kreis mit dem festgelegten Radius
  pointFeatures.forEach(pointFeature => {
    const coord = pointFeature.getGeometry().getCoordinates();
    const rotorRadius = pointFeature.get("rotorRadius");
    const circlePolygon = createCirclePolygon(coord, rotorRadius);
    const circleFeature = new Feature({
      geometry: circlePolygon
    });
    
    sphereRadiusSource.addFeature(circleFeature);
  });
  
  console.log(`SphereRadiusLayer aktualisiert: ${pointFeatures.length} Kreise mit Radius ${sphereRadiusValue}m gezeichnet.`);
}

// Event-Listener für Änderungen am Sphere-Radius-Input
document.getElementById('sphereRadius').addEventListener('change', () => {
  updateSphereRadiusLayer();
  updateWakeLayer(); // Da der Sphere-Radius auch die Wake-Regionen beeinflusst
});

// ======================================================================
// Select- und Clear-Interaktionen
// ======================================================================

/**
 * Initialisiert die Select-Interaktion für Formen
 */
function einrichtenSelectInteraktion(button) {
  button.addEventListener('click', () => {
    toggleEditMode(button);
  });
}

let selectInteraction = null;

/**
 * Schaltet den Edit-Modus ein oder aus
 * @param {HTMLElement} button - Der Edit-Button zum Anpassen des Styles
 */
function toggleEditMode(button) {
  editModeActive = !editModeActive;
  
  if (editModeActive) {
    // Edit-Modus aktivieren
    aktiviereSelectInteraktion();
    button.classList.add('active');
    button.style.backgroundColor = '#45a049'; // Grün für aktiv
    console.log('Edit-Modus aktiviert');
  } else {
    // Edit-Modus deaktivieren
    if (selectInteraction) {
      selectInteraction.getFeatures().clear();
      map.removeInteraction(selectInteraction);
      selectInteraction = null;
    }
    
    if (translateInteraction) {
      map.removeInteraction(translateInteraction);
      translateInteraction = null;
    }
    
    button.classList.remove('active');
    button.style.backgroundColor = '#ccc'; // Zurück zum Standard-Grau
    console.log('Edit-Modus deaktiviert');
  }
}

/**
 * Aktiviert die Select-Interaktion für den aktiven Layer
 */
function aktiviereSelectInteraktion() {
  // Zeichnen-Interaktion entfernen
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
  
  // Bestehende Select-Interaktion entfernen
  if (selectInteraction) {
    map.removeInteraction(selectInteraction);
  }
  
  // Filterfunktion für die Select-Interaktion basierend auf aktivem Layer
  const filterFunction = function(feature) {
    if (activeLayer === 'points') {
      return feature.getGeometry().getType() === 'Point';
    } else if (activeLayer === 'simarea') {
      return feature.getGeometry().getType() === 'Polygon';
    }
    // Bei "none" keine Features auswählbar
    return false;
  };
  
  // Neue Select-Interaktion erstellen
  selectInteraction = new Select({
    condition: click,
    multi: true,
    filter: filterFunction
  });
  
  map.addInteraction(selectInteraction);
  
  // Translate-Interaktion für ausgewählte Features hinzufügen
  selectInteraction.on('select', function(e) {
    // Entferne bestehende Translate-Interaktion falls vorhanden
    if (translateInteraction) {
      map.removeInteraction(translateInteraction);
    }
    
    // Prüfe, ob Features ausgewählt sind
    if (selectInteraction.getFeatures().getLength() > 0) {
      // Erstelle eine neue Translate-Interaktion für die ausgewählten Features
      translateInteraction = new Translate({
        features: selectInteraction.getFeatures()
      });
      
      map.addInteraction(translateInteraction);
      
      // Nach dem Verschieben der Features:
      translateInteraction.on('translateend', () => {
        console.log('Ausgewählte Features verschoben');
        // Wenn ein Simulationsgebiet-Feature verschoben wurde:
        const simAreaFeatures = selectInteraction.getFeatures().getArray().filter(f => 
          f.getGeometry().getType() === 'Polygon');
        
        if (simAreaFeatures.length > 0) {
          // Wenn das aktuelle Shape unter den verschobenen Features ist, aktualisiere
          const isCurrentShapeMoved = simAreaFeatures.some(f => f === currentShape);
          if (isCurrentShapeMoved && currentShape) {
            aktualisierePfeil();
            aktualisiereDimensionenFelder();
          }
        }
        
        // In jedem Fall die Visualisierungslayer aktualisieren
        updateWakeLayer();
        updateSphereRadiusLayer();
      });
    }
  });
  
  console.log(`Select-Interaktion aktiviert für ${activeLayer}`);
}

/**
 * Initialisiert den Button zum Löschen der Formen
 */
function einrichtenLoeschenButton(button) {
  button.addEventListener('click', () => {
    const ausgewählteFeatures = selectInteraction ? selectInteraction.getFeatures() : null;
    
    if (ausgewählteFeatures && ausgewählteFeatures.getLength() > 0) {
      // Nur ausgewählte Features löschen
      ausgewählteFeatures.forEach((feature) => {
        const geomType = feature.getGeometry().getType();
        if (geomType === 'Point') {
          turbineSource.removeFeature(feature);
        } else if (geomType === 'Polygon') {
          simAreaSource.removeFeature(feature);
          if (feature === currentShape) currentShape = null;
        }
      });
      ausgewählteFeatures.clear();
      console.log('Ausgewählte Formen gelöscht');
    } else {
      // Löschen aller Features des aktiven Layers
      if (activeLayer === 'points') {
        turbineSource.clear();
        console.log('Alle Turbinen gelöscht');
      } else if (activeLayer === 'simarea') {
        simAreaSource.clear();
        currentShape = null;
        console.log('Alle Simulationsgebiete gelöscht');
      } else {
        console.log('Kein aktiver Layer zum Löschen');
      }
    }
    
    // Visualisierungslayer aktualisieren
    updateWakeLayer();
    updateSphereRadiusLayer();
  });
}

// ======================================================================
// WebSocket-Verbindung zum Server herstellen (Einmal für Export & Bash-Skripte)
// ======================================================================
let socket;

function initializeWebSocket() {
  socket = new WebSocket("ws://localhost:3000");

  // Terminal-Output-Element abrufen
  const outputElement = document.getElementById("output");

  // Nachrichten vom Server empfangen
  socket.onmessage = function (event) {
    const outputElement = document.getElementById("output");
    try {
      const data = JSON.parse(event.data);
      if (data.type === "progress") {
        if ("progress" in data) {
          document.getElementById('progressBar').style.width = data.progress + '%';
        }
        return;
      }
      // Prüfe, ob es sich um eine Passphrase-Anforderung handelt
      if (data.type === "passphrase_required") {
        console.log("Passphrase-Anfrage erkannt, zeige Popup an");
        showPassphrasePrompt(data.user, data.host);
        return; // Beende die Funktion hier, um zu vermeiden, dass die Nachricht an das Ausgabeelement gesendet wird
      }
      
      // Falls es eine andere JSON-Nachricht ist, zeige sie als Text an
      outputElement.textContent += JSON.stringify(data) + "\n";
    } catch (e) {
      // Keine JSON-Nachricht, direkt ausgeben
      outputElement.textContent += event.data + "\n";
      
      // Aktualisiere die Eingabefelder für Breite und Tiefe, nachdem geänderte Werte empfangen wurden. Für simulationArea
      if (typeof event.data === 'string') {
        const widthMatch = event.data.match(/Width:\s*([\d\.]+)\s*meters/);
        if (widthMatch) {
          const width = parseFloat(widthMatch[1]);
          console.log(`Extrahierte Werte - Width: ${width}`);
          document.getElementById('widthInput').value = width;
          document.getElementById('widthInput').dispatchEvent(new Event('change'));
        }
        const lengthMatch = event.data.match(/Length:\s*([\d\.]+)\s*meters/);
        if (lengthMatch) {
          const length = parseFloat(lengthMatch[1]);
          console.log(`Extrahierte Werte - Length: ${length}`);
          document.getElementById('depthInput').value = length;
          document.getElementById('depthInput').dispatchEvent(new Event('change'));
        }
      }
    }
    
    // Automatisch nach unten scrollen
    outputElement.scrollTop = outputElement.scrollHeight;
  };

  // Fehlerbehandlung für WebSocket
  socket.onerror = function (error) {
    console.error("WebSocket-Fehler:", error);
    outputElement.textContent += "WebSocket-Fehler: Verbindung konnte nicht hergestellt werden.\n";
  };

  // Falls Verbindung abbricht, automatisch wieder verbinden
  socket.onclose = function () {
    console.warn("WebSocket getrennt, versuche Neustart...");
    outputElement.textContent += "WebSocket-Verbindung getrennt. Verbinde erneut...\n";
    setTimeout(initializeWebSocket, 2000); // Automatische Wiederverbindung nach 2 Sekunden
  };
}

// WebSocket initial starten
initializeWebSocket();

// ======================================================================
// Passphrase-Prompt-Funktionalität
// ======================================================================

// Passphrase-Prompt anzeigen
function showPassphrasePrompt(user, host) {
  console.log(`Zeige Passphrase-Prompt für ${user}@${host}`);
  
  // HTML-Modal verwenden
  const modalContainer = document.getElementById("passphrase-modal-container");
  
  // Titel und Beschreibung mit aktuellen Benutzerdaten aktualisieren
  document.getElementById("passphrase-title").textContent = "SSH-Key Passphrase benötigt";
  document.getElementById("passphrase-description").textContent = 
    `Bitte gib die Passphrase für deinen SSH-Key (${user}@${host}) ein:`;
  
  // Passphrase-Feld leeren und fokussieren
  const passphraseInput = document.getElementById("ssh-passphrase");
  passphraseInput.value = "";
  passphraseInput.placeholder = "SSH-Key Passphrase";
  
  // Event-Listener für Buttons
  document.getElementById("cancel-passphrase-button").onclick = function() {
    modalContainer.style.display = "none";
    // Sende Abbruchmeldung an den Server
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: "passphrase",
        canceled: true
      }));
    }
  };
  
  document.getElementById("submit-passphrase-button").onclick = sendPassphrase;
  
  // Enter-Taste für Passphrase-Eingabe
  passphraseInput.onkeyup = function(event) {
    if (event.key === "Enter") {
      sendPassphrase();
    }
  };
  
  // Modal anzeigen
  modalContainer.style.display = "flex";
  
  // Input-Feld fokussieren
  setTimeout(function() {
    passphraseInput.focus();
  }, 100);
}

// Passphrase an den Server senden
function sendPassphrase() {
  const passphraseInput = document.getElementById("ssh-passphrase");
  let passphrase = passphraseInput.value;
  
  if (!passphrase) {
    alert("Bitte gib die Passphrase für deinen SSH-Key ein.");
    return;
  }
  
  // Passphrase über WebSocket senden
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: "passphrase",
      passphrase: passphrase
    }));
    
    // Modal schließen
    document.getElementById("passphrase-modal-container").style.display = "none";
  } else {
    console.error("WebSocket nicht verbunden, Passphrase konnte nicht gesendet werden.");
  }
}

// ======================================================================
// Export-Funktion
// ======================================================================

function exportiereSimulationsdaten() {
  if (!currentShape) {
    alert('Kein Shape definiert für den Export.');
    return;
  }
  const rootFolder = document.getElementById('rootFolder').value;
  if (!rootFolder) {
    alert('Root Folder nicht definiert für den Export.');
    return;
  }
  
  // SIMULATION AREA /////////////////////////////////////////////////
  const cornerPoints = currentShape.getGeometry().getCoordinates()[0];
  cornerPoints.pop(); // Letzten Punkt entfernen, da es ein Duplikat des ersten ist

  const center = currentShape.getGeometry().getInteriorPoint().getCoordinates();
  center.pop(); // Letzten Punkt entfernen (ist glaub Halbierende oder so)

  const dimensionen = berechneDimensionen(currentShape.getGeometry(), squareAngleRadian);
  
  // TURBINES ////////////////////////////////////////////////////////
  const turbines = turbineSource.getFeatures()
    .map((t, index) => ({
      id: `Turbine_${index + 1}`,
      turbineType: t.get('turbineType'),
      coordinates: t.getGeometry().getCoordinates(),
      hubHeight: t.get('hubHeight'),
      rotorRadius: t.get('rotorRadius'),
      tipSpeedRatio: t.get('tipSpeedRatio'),
      sphereRadius: t.get('sphereRadius')
    }));
  //parts
  const towerCheckbox = document.getElementById('tower').checked;
  const hubCheckbox = document.getElementById('hub').checked;
  // WAKE REGIONS ////////////////////////////////////////////////////
  const wakeRegions = wakeSource.getFeatures()
    .map((feature, index) => {
      const coords = feature.getGeometry().getCoordinates()[0];
      // Compute the center of the wake region
      const center = feature.getGeometry().getInteriorPoint().getCoordinates();
      return { id: `WakeRegion_${index + 1}`, coordinates: coords, center: center };
    });


  // PARAM PANEL //////////////////////////////////////////////////////
  const panelParameters = {
    windSpeed: parseFloat(document.getElementById('windSpeed').value),
    turbIntensity: parseFloat(document.getElementById('turbIntensity').value),
    sphereRadius: parseFloat(document.getElementById('sphereRadius').value),
    hubHeight: parseFloat(document.getElementById('hubHeight').value),
    profileHeights: document.getElementById('profileHeights').value
                      .split(',')
                      .map(s => parseFloat(s.trim())),
    cellDensity: parseFloat(document.getElementById('cellDensity').value),
    startTime: parseFloat(document.getElementById('startTime').value),
    endTime: parseFloat(document.getElementById('endTime').value),
    deltaT: parseFloat(document.getElementById('deltaT').value),
    writeInterval: parseFloat(document.getElementById('writeInterval').value),
    computeCores: parseFloat(document.getElementById('computeCores').value)
  };

  // SSH-Konfiguration hinzufügen
  const user = document.getElementById('userInput').value;
  const host = document.getElementById('hostInput').value;
  const remoteDir = document.getElementById('remoteDirInput').value;

// JSON-Struktur
const exportDaten = {
  type: "export",
  // SSH-Konfiguration für Verbindung
  user: user,
  host: host,
  remoteDir: remoteDir,
  rootFolder: rootFolder,
  
  // Bisherige Daten
  simulationArea: {
    coordinates: cornerPoints,
    center: center,
    dimensions: {
      width: dimensionen.width,
      depth: dimensionen.depth
    },
    rotationAngle: squareAngleRadian
  },
  wakeRegions: wakeRegions,

  turbines:{
    turbine: turbines,
    stallType: document.getElementById('stallType').value,
    stallModel: document.getElementById('stallModel').value,
    endEffects: document.getElementById('endEffectsModel').value,
    hubCheckbox: hubCheckbox,
    towerCheckbox: towerCheckbox
  },
  environment: {
    wind: {
      direction: (squareAngleRadian + Math.PI) % (2 * Math.PI), // Windrichtung um 180° gedreht
      speed: panelParameters.windSpeed,
      turbulenceIntensity: panelParameters.turbIntensity,
      profileHeights: panelParameters.profileHeights
    },
    cellDensity: panelParameters.cellDensity
  },
  Solver: {
    startTime: panelParameters.startTime,
    endTime: panelParameters.endTime,
    deltaT: panelParameters.deltaT,
    writeInterval: panelParameters.writeInterval,
    computeCores: panelParameters.computeCores
  }
};

// Simulationsdaten über WebSocket senden
if (socket.readyState === WebSocket.OPEN) {
  socket.send(JSON.stringify(exportDaten));
} else {
  console.error("WebSocket nicht verbunden, Export fehlgeschlagen.");
}
}
document.getElementById('exportButton').addEventListener('click', exportiereSimulationsdaten);
// // ======================================================================
// // OpenFOAM Simulation Control
// // ======================================================================
function sendCommandToServer(command, customCommand) {
  const user = document.getElementById('userInput').value;
  const host = document.getElementById('hostInput').value;
  const remoteDir = document.getElementById('remoteDirInput').value;

  if (!user || !host || !remoteDir) {
    console.error("User, Host oder Remote Directory nicht definiert (main.js).");
    return;
  }

  const commandData = {
    type: "command",
    command: command,
    user: user,
    host: host,
    remoteDir: remoteDir,
  };

  if (customCommand) {
    commandData.customCommand = customCommand;
  }

  // WebSocket-Nachricht senden
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(commandData));
  } else {
    console.error("WebSocket nicht verbunden, Kommando kann nicht gesendet werden.");
  }
}

// Event-Listener für die Buttons
document.getElementById('LocalToRemoteButton').addEventListener('click', () => sendCommandToServer('sync'));
document.getElementById('allCleanButton').addEventListener('click', () => sendCommandToServer('clean'));
document.getElementById('allPreButton').addEventListener('click', () => sendCommandToServer('pre'));
document.getElementById('allRunSlurmButton').addEventListener('click', () => sendCommandToServer('run'));
document.getElementById('CalcStatusButton').addEventListener('click', () => sendCommandToServer('status'));
document.getElementById('allPostButton').addEventListener('click', () => sendCommandToServer('post'));
document.getElementById('getVTKButton').addEventListener('click', () => sendCommandToServer('VTK'));
// document.getElementById('allRunButton').addEventListener('click', () => sendCommandToServer('all'));
// document.getElementById('customButton').addEventListener('click', () => {
//   const custo
