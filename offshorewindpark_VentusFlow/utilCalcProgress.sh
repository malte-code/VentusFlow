#!/bin/bash
# Dieses Skript berechnet den Fortschritt einer OpenFOAM-Simulation.
# Es liest die startTime und endTime aus der Datei system/controlDict aus,
# berechnet die Gesamtsimulationsdauer und setzt diese als 100%.
# Anschließend wird im Ordner processor nach numerischen Unterordnern gesucht,
# wobei der höchste Zahlenwert als aktuelle Simulationszeit angenommen wird.
# Daraus wird der prozentuale Fortschritt errechnet.

# --- 1. Parameter aus controlDict auslesen ---
CONTROL_DICT="system/controlDict"

if [ ! -f "$CONTROL_DICT" ]; then
    echo "Die Datei $CONTROL_DICT wurde nicht gefunden."
    exit 1
fi

# Suche nach Zeilen, die mit "startTime" bzw. "endTime" beginnen und nicht kommentiert sind.
startTime=$(grep -E "^[[:space:]]*startTime[[:space:]]" "$CONTROL_DICT" | grep -v "^//" | head -1 | awk '{print $2}' | tr -d ';')
endTime=$(grep -E "^[[:space:]]*endTime[[:space:]]" "$CONTROL_DICT" | grep -v "^//" | head -1 | awk '{print $2}' | tr -d ';')

if [ -z "$startTime" ] || [ -z "$endTime" ]; then
    echo "startTime oder endTime konnten nicht gefunden werden."
    exit 1
fi

# Berechne die Gesamtsimulationsdauer
totalTime=$(echo "$endTime - $startTime" | bc)

if [ "$totalTime" -eq 0 ]; then
    echo "Die Simulationsdauer ist 0, Berechnung nicht möglich."
    exit 1
fi

echo "Gesamtsimulationsdauer: $totalTime"

# --- 2. Aktuellen Fortschritt aus Ordnern im processor ermitteln ---
# Hier wird im Ordner "processor" (bitte ggf. anpassen) nach Unterordnern gesucht,
# deren Namen ausschließlich aus Zahlen bestehen.
PROCESSOR_DIR="processor0"

if [ ! -d "$PROCESSOR_DIR" ]; then
    echo "Der Ordner $PROCESSOR_DIR wurde nicht gefunden. Suche im Root-Verzeichnis..."
    PROCESSOR_DIR="."  # Suche im aktuellen Arbeitsverzeichnis
fi

# Durchlaufe alle Unterordner und filtere numerische Namen
maxFolder=$(for d in "$PROCESSOR_DIR"/*; do
    if [ -d "$d" ]; then
        base=$(basename "$d")
        if [[ $base =~ ^[0-9]+$ ]]; then
            echo $base
        fi
    fi
done | sort -n | tail -n 1)

if [ -z "$maxFolder" ]; then
    echo "Keine numerischen Ordner in $PROCESSOR_DIR gefunden."
    exit 1
fi

echo "Aktueller Zeitschritt: $maxFolder"

# --- 3. Prozentualen Fortschritt berechnen ---
progress=$(echo "scale=2; ($maxFolder / $totalTime) * 100" | bc -l)

echo "Fortschritt der Simulation: $progress %"