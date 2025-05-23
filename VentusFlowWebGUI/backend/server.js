/**
 * VentusFlow WebGUI – Offshore Windpark Simulation (LES, Actuator Line)
 * ---------------------------------------------------------------
 * Author: Malte Schudek
 * Hochschule: Universität Stuttgart, HLRS
 * Betreuer: Prof. Dr.-Ing. Dr. h.c. Hon. Prof. Michael M. Resch, Uwe Woessner, Dr.-Ing.
 * 
 * Studienarbeit Energietechnik | April 2025 | Bericht Nr. 001
 * 
 * Repository: https://github.com/malte-code/VentusFlow
 * File: backend/server.js
 */

const express = require('express');
const fs = require('fs');
const cors = require('cors');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const { Client } = require('ssh2');
const os = require('os');

const app = express();
const PORT = 3000;
const sshPort = 31022; // SSH-Port für den HPC-Cluster

function checkSSHAgent() {
  const sshAgent = process.env.SSH_AUTH_SOCK;
  if (!sshAgent || !fs.existsSync(sshAgent)) {
    console.error("SSH-Agent ist nicht verfügbar oder der Socket existiert nicht.");
    return false;
  }
  console.log("SSH-Agent ist verfügbar.");
  return true;
}

// HTTP-Server für WebSockets erstellen
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Middleware
app.use(express.json());
app.use(cors());

// SSH-Verbindungsverwaltung
let sshConnection = null;
let sshConfig = null;
let waitingForPassphrase = false;
let pendingCallback = null;
let sshPassphrase = null; // Speichert die Passphrase während der Server-Laufzeit

// WebSocket-Verbindung herstellen
wss.on("connection", (ws) => {
  console.log("Client verbunden.");
  
  // Start periodic polling every 10s for simulation progress
  const progressInterval = setInterval(() => {
    if (sshConfig && sshConfig.remoteDir) {
      executeSSHCommand(ws, 'progress', null, { suppressConnectionMessages: true });
    }
  }, 100000);

  ws.on("message", (message) => {
    try {
      const data = JSON.parse(message);
      if (data.type === "export") {
        handleExportRequest(ws, data);
      } else if (data.type === "command") {
        handleCommandRequest(ws, data);
      } else if (data.type === "passphrase") {
        handlePassphraseResponse(ws, data);
      } else {
        ws.send("Unbekannter Nachrichtentyp: " + data.type);
      }
    } catch (error) {
      console.error("Fehler beim Verarbeiten der WebSocket-Nachricht:", error);
      ws.send(`Fehler: ${error.message}`);
    }
  });

  ws.on("close", () => {
    console.log("Client getrennt.");
    clearInterval(progressInterval);
    // SSH-Verbindung bleibt bestehen, auch wenn Client getrennt wurde
  });
});

/**
 * Verarbeitet Export-Anforderungen
 */
function handleExportRequest(ws, data) {
  if (data.user && data.host) {
    // Prüfe, ob sich die SSH-Konfiguration geändert hat
    const configChanged = !sshConfig || 
                         sshConfig.user !== data.user || 
                         sshConfig.host !== data.host || 
                         sshConfig.remoteDir !== data.remoteDir;
    
    // Neue Konfiguration setzen
    sshConfig = {
      user: data.user,
      host: data.host,
      remoteDir: data.remoteDir
    };
    
    // Erst JSON speichern und Python ausführen, dann SSH-Verbindung testen
    handleExport(ws, data, () => {
      testSSHConnection(ws, () => {
        ws.send("Export abgeschlossen und SSH-Konfiguration gespeichert.");
      });
    });
  } else {
    ws.send("Fehler: User oder Host nicht angegeben!");
    handleExport(ws, data);
  }
}

/**
 * Verarbeitet Command-Anforderungen
 */
function handleCommandRequest(ws, data) {
  // Bei Command-Ausführung sicherstellen, dass SSH-Konfiguration vorhanden ist
  if (!sshConfig || !sshConfig.user || !sshConfig.host) {
    ws.send("SSH-Konfiguration fehlt. Bitte zuerst einen Export durchführen.");
    return;
  }
  
  // Prüfen, ob neue Konfiguration übergeben wurde
  if (data.user && data.host && 
      (sshConfig.user !== data.user || sshConfig.host !== data.host || sshConfig.remoteDir !== data.remoteDir)) {
    // SSH-Konfiguration aktualisieren
    sshConfig = {
      user: data.user,
      host: data.host,
      remoteDir: data.remoteDir
    };
    ws.send("SSH-Konfiguration aktualisiert.");
  }
  
  // Für jeden Befehl eine neue Verbindung öffnen
  executeSSHCommand(ws, data.command, data.customCommand);
}

/**
 * Verarbeitet die Passphrase-Antwort vom Client
 */
function handlePassphraseResponse(ws, data) {
  if (waitingForPassphrase) {
    waitingForPassphrase = false;
    
    if (data.canceled) {
      ws.send("SSH-Verbindung wurde vom Benutzer abgebrochen.");
      pendingCallback = null;
    } else if (data.passphrase) {
      // Speichere die Passphrase für zukünftige Verbindungen
      sshPassphrase = data.passphrase;
      // Verwende testConnectionWithPassphrase statt des nicht-definierten completeSSHConnection
      if (pendingCallback) {
        const homeDir = os.homedir();
        const keyPath = path.join(homeDir, '.ssh', 'id_ed25519');
        try {
          const keyFile = fs.readFileSync(keyPath);
          testSSHConnection(ws, pendingCallback);
        } catch (error) {
          ws.send(`Konnte SSH-Key nicht laden: ${error.message}`);
          ws.send("SSH-Verbindung nicht möglich ohne gültigen SSH-Key.");
        }
      }
      pendingCallback = null;
    } else {
      ws.send("Keine Passphrase angegeben.");
    }
  } else {
    ws.send("Es wurde keine Passphrase angefordert.");
  }
}

/**
 * Testet die SSH-Verbindung, um die Zugangsdaten zu validieren
 */
function testSSHConnection(ws, callback) {
  if (!sshConfig) {
    ws.send("SSH-Konfiguration fehlt. Bitte zuerst einen Export durchführen.");
    return;
  }

  ws.send(`Teste SSH-Verbindung zu ${sshConfig.user}@${sshConfig.host} über Port ${sshPort}...`);
  
  // Pfad zum SSH-Schlüssel
  const homeDir = os.homedir();
  const keyPath = path.join(homeDir, '.ssh', 'id_ed25519');
  let keyFile = null;
  
  try {
    keyFile = fs.readFileSync(keyPath);
    ws.send(`SSH-Key geladen aus: ${keyPath}`);
  } catch (error) {
    ws.send(`Konnte SSH-Key nicht laden: ${error.message}`);
    requestPassphrase(ws, callback);
    return;
  }

  // Zuerst mit gespeicherter Passphrase versuchen, falls vorhanden
  if (sshPassphrase) {
    ws.send("Versuche Verbindung mit gespeicherter Passphrase...");
    connectSSH(ws, sshPassphrase, keyFile, (conn) => {
      ws.send(`SSH-Verbindung zu ${sshConfig.host} erfolgreich hergestellt.`);
      ws.send("SSH-Konfiguration valide und für weitere Anfragen temporär gespeichert.");
      conn.end();
      if (callback) callback();
    }, (err) => {
      sshPassphrase = null;
      requestPassphrase(ws, callback);
    });
  } else {
    // Wenn keine Passphrase gespeichert ist, direkt nach einer fragen
    requestPassphrase(ws, callback);
  }
}

/**
 * Fordert eine Passphrase vom Client an
 */
function requestPassphrase(ws, callback) {
  waitingForPassphrase = true;
  pendingCallback = callback;
  
  // Sende Aufforderung an den Client, eine Passphrase einzugeben
  ws.send(JSON.stringify({
    type: "passphrase_required",
    user: sshConfig.user,
    host: sshConfig.host
  }));
  
  console.log(`SSH-Key-Passphrase angefordert für ${sshConfig.user}@${sshConfig.host}`);
  ws.send(`SSH-Key-Passphrase angefordert für ${sshConfig.user}@${sshConfig.host}`);
}

/**
 * Stellt sicher, dass eine SSH-Verbindung besteht oder erstellt eine neue.
 */
function ensureSSHConnection(ws, callback) {
  if (!sshConfig) {
    ws.send("SSH-Konfiguration fehlt. Bitte zuerst einen Export durchführen.");
    return;
  }

  if (sshConnection && sshConnection.connected) {
    // Verbindung besteht bereits
    ws.send("Bestehende SSH-Verbindung wird verwendet.");
    callback();
    return;
  }

  ws.send(`Stelle SSH-Verbindung her zu ${sshConfig.user}@${sshConfig.host} über Port ${sshPort}...`);
  
  // Pfad zum SSH-Schlüssel
  const homeDir = os.homedir();
  const keyPath = path.join(homeDir, '.ssh', 'id_ed25519');
  let keyFile = null;
  
  try {
    keyFile = fs.readFileSync(keyPath);
    ws.send(`SSH-Key geladen aus: ${keyPath}`);
  } catch (error) {
    ws.send(`Konnte SSH-Key nicht laden: ${error.message}`);
    requestPassphrase(ws, callback);
    return;
  }

  // Zuerst mit gespeicherter Passphrase versuchen, falls vorhanden
  if (sshPassphrase) {
    ws.send("Versuche Verbindung mit gespeicherter Passphrase...");
    connectSSH(ws, sshPassphrase, keyFile, (conn) => {
      ws.send(`SSH-Verbindung zu ${sshConfig.host} erfolgreich hergestellt.`);
      sshConnection = conn;
      sshConnection.setKeepAliveInterval(60000);
      if (callback) callback();
    }, (err) => {
      sshPassphrase = null;
      requestPassphrase(ws, callback);
    }, { debug: true, keepaliveInterval: 60000 });
  } else {
    // Wenn keine Passphrase gespeichert ist, direkt nach einer fragen
    requestPassphrase(ws, callback);
  }
}

/**
 * Führt einen SSH-Befehl auf dem Remote-Server aus
 */
function executeSSHCommand(ws, command, customCommand, options = {}) {
  if (!sshConfig || !sshConfig.user || !sshConfig.host) {
    ws.send("SSH-Konfiguration fehlt. Bitte zuerst einen Export durchführen.");
    return;
  }

  if (!command) {
    ws.send("Kein Befehl angegeben.");
    return;
  }
  
  // Bestimme den auszuführenden Befehl
  let sshCommand = '';
  const remoteDir = sshConfig.remoteDir;
  
  switch(command) {
    case 'sync':
      // Korrigiere die Pfad-Konstruktion für den rootFolder
      const rootDir = sshConfig.rootFolder || 'offshorewindpark_VentusFlow';
      const localDir = path.resolve(__dirname, '../../', rootDir);
      
      // Überprüfe, ob der lokale Ordner existiert
      if (!fs.existsSync(localDir)) {
        ws.send(`Fehler: Lokaler Ordner '${localDir}' nicht gefunden!`);
        return;
      }
      
      ws.send(`Verwende lokalen Ordner: ${localDir}`);
      
      // Anstatt rsync als Subprocess zu verwenden, nutzen wir die eingebaute SSH SCP-Funktionalität
      transferFilesToRemote(ws, localDir, remoteDir);
      return;

    case 'clean':
      sshCommand = `cd ${remoteDir} && ./Allclean`;
      break;
    
    case 'pre':
      sshCommand = `cd ${remoteDir} && ./Allpre`;
      break;
      
    case 'run':
      sshCommand = `cd ${remoteDir} && sbatch Allrun.slurm`;
      break;
      
    case 'status':
      sshCommand = `squeue && cd ${remoteDir} && ./utilCalcProgress`;
      break;
      
    case 'post':
      sshCommand = `cd ${remoteDir} && ./Allpost`;
      break;
      
    case 'VTK':
      const timestamp = new Date().toISOString().replace(/[:.]/g, '');
      const resultDir = path.join(__dirname, `../../result/${timestamp}`);
      
      fs.mkdirSync(resultDir, { recursive: true });
      ws.send(`Neuer lokaler Ordner erstellt: ${resultDir}`);
      
      // Anstatt rsync zu verwenden, nutzen wir die eingebaute SSH SCP-Funktionalität
      transferFilesFromRemote(ws, remoteDir, resultDir, ['VTK/**', 'log.*']);
      return;
      
    case 'all':
      sshCommand = `cd ${remoteDir} && ./Allclean && ./Allpre && sbatch Allrun.slurm`;
      break;
      
    case 'custom':
      if (customCommand) {
        sshCommand = `cd ${remoteDir} && ${customCommand}`;
      } else {
        ws.send("Kein benutzerdefinierter Befehl angegeben.");
        return;
      }
      break;
      
    case 'progress':
      sshCommand = `cd ${remoteDir} && ./utilCalcProgress`;
      break;

    default:
      ws.send(`Unbekannter Befehl: ${command}`);
      return;
  }
  
  // Neue SSH-Verbindung für den Befehl erstellen
  executeCommandWithNewConnection(ws, sshCommand, command, options);
}

/**
 * Überträgt Dateien vom lokalen System zum Remote-Server mittels SSH SFTP
 */
function transferFilesToRemote(ws, localDir, remoteDir) {
  ws.send(`Starte Übertragung von ${localDir} zu ${remoteDir}...`);
  
  // Erstelle eine neue SSH-Verbindung für die Dateiübertragung
  createSSHConnection(ws, (conn) => {
    // Erzeuge einen SFTP-Stream aus der SSH-Verbindung
    conn.sftp((err, sftp) => {
      if (err) {
        ws.send(`SFTP-Fehler: ${err.message}`);
        conn.end();
        return;
      }

      // Erstelle das Remote-Verzeichnis, falls es nicht existiert
      conn.exec(`mkdir -p ${remoteDir}`, (err) => {
        if (err) {
          ws.send(`Fehler beim Erstellen des Remote-Verzeichnisses: ${err.message}`);
          conn.end();
          return;
        }
        
        // Nun übertragen wir die Dateien rekursiv
        uploadDirectory(ws, sftp, localDir, remoteDir, () => {
          ws.send("Local->Remote Synchronisation abgeschlossen.");
          conn.end();
        });
      });
    });
  });
}

/**
 * Überträgt Dateien vom Remote-Server zum lokalen System mittels SSH SFTP
 */
function transferFilesFromRemote(ws, remoteDir, localDir, patterns = []) {
  ws.send(`Starte Übertragung von ${remoteDir} zu ${localDir}...`);
  
  // Erstelle eine neue SSH-Verbindung für die Dateiübertragung
  createSSHConnection(ws, (conn) => {
    // Erzeuge einen SFTP-Stream aus der SSH-Verbindung
    conn.sftp((err, sftp) => {
      if (err) {
        ws.send(`SFTP-Fehler: ${err.message}`);
        conn.end();
        return;
      }
      
      // Liste der zu übertragenden Dateien erstellen
      ws.send(`Suche nach VTK-Dateien und Logs in ${remoteDir}...`);
      
      // Zuerst überprüfen, ob der VTK-Ordner existiert
      conn.exec(`ls -la ${remoteDir}/VTK`, (err, stream) => {
        let dataReceived = false;
        
        if (err) {
          ws.send(`Fehler bei der Ausführung von ls: ${err.message}`);
          conn.end();
          return;
        }
        
        stream.on('data', (data) => {
          dataReceived = true;
          ws.send(`VTK-Ordner gefunden: ${data.toString()}`);
        });
        
        stream.stderr.on('data', (data) => {
          // Wenn stderr, möglicherweise existiert der Ordner nicht
          ws.send(`Warnung: ${data.toString()}`);
        });
        
        stream.on('close', (code) => {
          if (code !== 0 || !dataReceived) {
            ws.send(`VTK-Ordner scheint nicht zu existieren oder ist leer. Exit-Code: ${code}`);
            // Trotzdem nach Log-Dateien suchen
            downloadLogFiles(conn, sftp, ws, remoteDir, localDir);
          } else {
            // VTK-Ordner existiert, herunterladen
            downloadVTKDirectory(conn, sftp, ws, remoteDir, localDir, () => {
              downloadLogFiles(conn, sftp, ws, remoteDir, localDir);
            });
          }
        });
      });
    });
  });
}

/**
 * Lädt den VTK-Ordner vom Remote-Server herunter
 */
function downloadVTKDirectory(conn, sftp, ws, remoteDir, localDir, callback) {
  const remoteVTKDir = `${remoteDir}/VTK`;
  const localVTKDir = `${localDir}/VTK`;
  
  // Lokales VTK-Verzeichnis erstellen
  fs.mkdirSync(localVTKDir, { recursive: true });
  ws.send(`Lokales VTK-Verzeichnis erstellt: ${localVTKDir}`);
  
  // Funktion zum rekursiven Herunterladen eines Verzeichnisses
  function downloadDirectory(remotePath, localPath, done) {
    sftp.readdir(remotePath, (err, list) => {
      if (err) {
        ws.send(`Fehler beim Lesen des Verzeichnisses ${remotePath}: ${err.message}`);
        done();
        return;
      }
      
      if (list.length === 0) {
        ws.send(`Verzeichnis ${remotePath} ist leer.`);
        done();
        return;
      }
      
      let pending = list.length;
      
      if (pending === 0) {
        done();
        return;
      }
      
      list.forEach((item) => {
        const remoteItemPath = `${remotePath}/${item.filename}`;
        const localItemPath = `${localPath}/${item.filename}`;
        
        if (item.attrs.isDirectory()) {
          // Erstelle das lokale Verzeichnis und lade es rekursiv herunter
          fs.mkdirSync(localItemPath, { recursive: true });
          downloadDirectory(remoteItemPath, localItemPath, () => {
            if (--pending === 0) done();
          });
        } else {
          // Lade die Datei herunter
          sftp.fastGet(remoteItemPath, localItemPath, (err) => {
            if (err) {
              ws.send(`Fehler beim Herunterladen von ${remoteItemPath}: ${err.message}`);
            } else {
              ws.send(`Heruntergeladen: ${item.filename}`);
            }
            if (--pending === 0) done();
          });
        }
      });
    });
  }
  
  // Starte den Download
  downloadDirectory(remoteVTKDir, localVTKDir, () => {
    ws.send(`VTK-Verzeichnis vollständig heruntergeladen nach ${localVTKDir}`);
    if (callback) callback();
  });
}

/**
 * Lädt Log-Dateien vom Remote-Server herunter
 */
function downloadLogFiles(conn, sftp, ws, remoteDir, localDir) {
  ws.send(`Suche nach Log-Dateien in ${remoteDir}...`);
  
  conn.exec(`find ${remoteDir} -maxdepth 1 -name "log.*"`, (err, stream) => {
    if (err) {
      ws.send(`Fehler bei der Suche nach Log-Dateien: ${err.message}`);
      conn.end();
      return;
    }
    
    let logFiles = '';
    
    stream.on('data', (data) => {
      logFiles += data.toString();
    });
    
    stream.stderr.on('data', (data) => {
      ws.send(`Warnung bei der Suche nach Log-Dateien: ${data.toString()}`);
    });
    
    stream.on('close', (code) => {
      if (code !== 0) {
        ws.send(`Fehler bei der Suche nach Log-Dateien. Exit-Code: ${code}`);
        conn.end();
        return;
      }
      
      const files = logFiles.trim().split('\n').filter(f => f.length > 0);
      
      if (files.length === 0) {
        ws.send('Keine Log-Dateien gefunden.');
        conn.end();
        return;
      }
      
      ws.send(`${files.length} Log-Dateien gefunden, lade herunter...`);
      
      let pending = files.length;
      
      files.forEach((filePath) => {
        const fileName = path.basename(filePath);
        const localFilePath = path.join(localDir, fileName);
        
        sftp.fastGet(filePath, localFilePath, (err) => {
          if (err) {
            ws.send(`Fehler beim Herunterladen von ${fileName}: ${err.message}`);
          } else {
            ws.send(`Log-Datei heruntergeladen: ${fileName}`);
          }
          
          if (--pending === 0) {
            ws.send('Alle Log-Dateien wurden heruntergeladen.');
            conn.end();
          }
        });
      });
    });
  });
}

/**
 * Lädt ein Verzeichnis rekursiv über SFTP hoch
 */
function uploadDirectory(ws, sftp, localDir, remoteDir, callback) {
  // Dateien und Verzeichnisse im lokalen Ordner lesen
  fs.readdir(localDir, { withFileTypes: true }, (err, entries) => {
    if (err) {
      ws.send(`Fehler beim Lesen des Verzeichnisses ${localDir}: ${err.message}`);
      callback();
      return;
    }
    
    // Filter für OpenFOAM-relevante Dateien (.C, .H, etc.) anwenden
    // Wir könnten hier noch weitere Filter hinzufügen
    const relevantEntries = entries;
    
    if (relevantEntries.length === 0) {
      callback();
      return;
    }
    
    let completed = 0;
    
    relevantEntries.forEach(entry => {
      const localPath = path.join(localDir, entry.name);
      const remotePath = path.join(remoteDir, entry.name).replace(/\\/g, '/');
      
      if (entry.isDirectory()) {
        // Verzeichnis rekursiv hochladen
        sftp.mkdir(remotePath, (err) => {
          // Ignorieren, wenn das Verzeichnis bereits existiert
          uploadDirectory(ws, sftp, localPath, remotePath, () => {
            completed++;
            if (completed === relevantEntries.length) {
              callback();
            }
          });
        });
      } else {
        // Datei hochladen
        sftp.fastPut(localPath, remotePath, (err) => {
          if (err) {
            ws.send(`Fehler beim Hochladen von ${localPath}: ${err.message}`);
          } else {
            ws.send(`Hochgeladen: ${entry.name}`);
          }
          
          completed++;
          if (completed === relevantEntries.length) {
            callback();
          }
        });
      }
    });
  });
}

/**
 * Erstellt eine neue SSH-Verbindung mit der gespeicherten Passphrase
 */
function createSSHConnection(ws, callback) {
  if (!sshConfig) {
    ws.send("SSH-Konfiguration fehlt. Bitte zuerst einen Export durchführen.");
    return;
  }
  
  // Pfad zum SSH-Schlüssel
  const homeDir = os.homedir();
  const keyPath = path.join(homeDir, '.ssh', 'id_ed25519');
  let keyFile = null;
  
  try {
    keyFile = fs.readFileSync(keyPath);
  } catch (error) {
    ws.send(`Konnte SSH-Key nicht laden: ${error.message}`);
    return;
  }
  
  connectSSH(ws, sshPassphrase, keyFile, (conn) => {
    ws.send(`SSH-Verbindung zu ${sshConfig.host} hergestellt.`);
    callback(conn);
  }, (err) => {
    if (err.message.includes('authentication') || 
        err.level === 'client-authentication') {
      sshPassphrase = null;
      ws.send("Authentifizierungsfehler. Bitte führen Sie den Export erneut durch.");
    }
  });
}

/**
 * Erstellt eine neue SSH-Verbindung und führt einen Befehl aus
 */
function executeCommandWithNewConnection(ws, sshCommand, originalCommand, options = {}) {
  if (!options.suppressConnectionMessages && originalCommand !== 'progress') {
    ws.send(`Führe Befehl aus: ${sshCommand}`);
  }
  
  // Pfad zum SSH-Schlüssel
  const homeDir = os.homedir();
  const keyPath = path.join(homeDir, '.ssh', 'id_ed25519');
  let keyFile = null;
  
  try {
    keyFile = fs.readFileSync(keyPath);
  } catch (error) {
    ws.send(`Konnte SSH-Key nicht laden: ${error.message}`);
    return;
  }
  
  connectSSH(ws, sshPassphrase, keyFile, (conn) => {
    if (!options.suppressConnectionMessages && originalCommand !== 'progress') {
      ws.send("SSH-Verbindung für Befehl hergestellt. Führe Befehl aus...");
    }
    conn.exec(sshCommand, (err, stream) => {
      if (err) {
        if (!options.suppressConnectionMessages && originalCommand !== 'progress') {
          ws.send(`Fehler beim Ausführen des Befehls: ${err.message}`);
        }
        conn.end();
        return;
      }
      let outputData = "";
      stream.on('data', (data) => {
        const text = data.toString();
        outputData += text;
        if (originalCommand === 'progress') {
          const match = text.match(/Fortschritt der Simulation:\s*([\d.]+)\s*%/);
          if (match) {
            // Send only the filtered progress percentage in a JSON object.
            ws.send(JSON.stringify({ type: "progress", progress: match[1] }));
          }
        } else {
          ws.send(text);
        }
      });
      stream.stderr.on('data', (data) => {
        if (!options.suppressConnectionMessages && originalCommand !== 'progress') {
          ws.send(`Fehler: ${data.toString()}`);
        }
      });
      stream.on('close', (code) => {
        if (!options.suppressConnectionMessages && originalCommand !== 'progress') {
          if (code === 0) {
            ws.send(`Befehl '${originalCommand}' erfolgreich ausgeführt.`);
          } else {
            ws.send(`Befehl '${originalCommand}' mit Fehler beendet (Exit-Code: ${code}).`);
          }
        }
        conn.end();
      });
    });
  }, (err) => {
    if (err.message.includes('authentication') || 
        err.level === 'client-authentication') {
      sshPassphrase = null;
      ws.send("Authentifizierungsfehler. Bitte führen Sie den Export erneut durch.");
    }
  });
}

/**
 * Speichert die Simulationsparameter und startet das Python-Skript zur Verarbeitung.
 */
function handleExport(ws, data, callback) {
  // Speichere rootFolder in der sshConfig
  if (data.rootFolder) {
    sshConfig.rootFolder = data.rootFolder;
  }
  
  const jsonFilePath = path.join(__dirname, 'simulation_parameters.json');
  const pythonScriptPath = path.join(__dirname, 'process_input.py');

  const pythonPath = path.resolve(__dirname, '../../.venv/bin/python3');
  
  fs.writeFile(jsonFilePath, JSON.stringify(data, null, 2), (err) => {
    if (err) {
      console.error("Fehler beim Speichern der Simulationsdaten:", err);
      ws.send(`Fehler beim Speichern: ${err.message}`);
      if (callback) callback(); // auch bei Fehler Callback ausführen
    } else {
      console.log("Simulationsdaten erfolgreich gespeichert.");
      ws.send("Simulationsdaten erfolgreich gespeichert.");
      
      // Starte das Python-Skript zur Verarbeitung
      const pythonProcess = spawn(pythonPath, [pythonScriptPath, jsonFilePath]);

      pythonProcess.stdout.on("data", (data) => {
        console.log(`Python: ${data}`);
        ws.send(data.toString());
      });
      
      pythonProcess.stderr.on("data", (data) => {
        console.error(`Python-Fehler: ${data}`);
        ws.send(`Fehler: ${data.toString()}`);
      });
      
      pythonProcess.on("close", (code) => {
        if (code === 0) {
          console.log("Python-Skript erfolgreich abgeschlossen.");
          ws.send("Python-Skript erfolgreich abgeschlossen.");
        } else {
          console.error(`Python-Skript mit Fehler beendet (Exit-Code: ${code})`);
          ws.send(`Fehler: Python-Skript mit Exit-Code ${code} beendet.`);
        }
        if (callback) callback(); // Callback nach Abschluss des Python-Skripts ausführen
      });
    }
  });
}

// Cleanup beim Beenden des Servers
function cleanup() {
  if (sshConnection && sshConnection.connected) {
    console.log("Schließe SSH-Verbindung...");
    sshConnection.end();
  }
}

process.on('SIGINT', () => {
  console.log('Server wird beendet...');
  cleanup();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Server wird beendet...');
  cleanup();
  process.exit(0);
});

// Server starten
server.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
});

// New helper to connect and configure an SSH connection
function connectSSH(ws, passphrase, keyFile, readyHandler, errorHandler, extraOptions) {
  // Base configuration
  const config = {
    host: sshConfig.host,
    username: sshConfig.user,
    port: sshPort,
    readyTimeout: 30000
  };

  // SSH-Agent verwenden, wenn verfügbar
  if (checkSSHAgent()) {
    config.agent = process.env.SSH_AUTH_SOCK;
    config.agentForward = true;
    //ws.send("SSH-Agent wird für Authentifizierung verwendet.");
  } else {
    // Fallback auf privaten Schlüssel und Passphrase
    config.privateKey = keyFile;
    if (passphrase) {
      config.passphrase = passphrase;
    }
  }

  if (extraOptions) Object.assign(config, extraOptions);

  const conn = new Client();

  conn.on('banner', (msg) => {
    ws.send(`SSH Banner: ${msg}`);
  });

  conn.on('keyboard-interactive', (name, instructions, instructionsLang, prompts, finish) => {
    ws.send(`SSH erfordert Tastatureingabe: ${prompts.map(p => p.prompt).join(', ')}`);
    // Reset passphrase if it appears invalid, and request a new one
    sshPassphrase = null;
    requestPassphrase(ws, (newPassphrase) => {
      finish([newPassphrase]);
    });
  });

  conn.on('error', (err) => {
    console.error('SSH-Verbindungsfehler:', err);
    ws.send(`SSH-Verbindungsfehler: ${err.message}`);
    if (errorHandler) errorHandler(err);
  });

  conn.on('ready', () => {
    readyHandler(conn);
  });

  try {
    conn.connect(config);
  } catch (e) {
    console.error('SSH-Connection Fehler:', e);
    ws.send(`SSH-Verbindungsfehler: ${e.message}`);
    if (errorHandler) errorHandler(e);
  }
  return conn;
}