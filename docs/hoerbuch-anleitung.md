# Hörbuch mit KR Cloud Voice erstellen

Diese Anleitung führt durch die lokale Erstellung eines Hörbuchs mit der
Qwen-CPU-Spracherzeugung. Alle Daten, Audiodateien und Modell-Downloads bleiben
unter `H:\KR_Cloud_Voice`.

## 1. Anwendung starten

Öffne zwei PowerShell-Fenster und starte jeweils eines der folgenden Skripte:

```powershell
H:\KR_Cloud_Voice\scripts\start-api.ps1
```

```powershell
H:\KR_Cloud_Voice\scripts\start-web.ps1
```

Öffne danach im Browser `http://127.0.0.1:5173`.

Beim ersten Qwen-Auftrag werden die Modellgewichte einmalig nach
`H:\KR_Cloud_Voice\runtime\cache\huggingface` geladen. Dieser Schritt kann je
nach Internetverbindung und Rechner einige Minuten dauern. Danach arbeitet die
Spracherzeugung lokal auf der CPU.

## 2. Benutzerkonto anlegen

1. Öffne die Weboberfläche.
2. Wähle **Registrieren**.
3. Gib eine E-Mail-Adresse und ein sicheres Passwort mit mindestens zwölf Zeichen ein.
4. Melde dich mit dem neuen Konto an.

Jedes Konto ist ein eigener Mandant. Projekte, Texte und Audiodateien sind von
anderen Konten getrennt.

## 3. Hörbuchprojekt erstellen

1. Klicke auf **Neues Projekt**.
2. Vergib einen eindeutigen Titel, zum Beispiel `Der kleine Leuchtturm`.
3. Wähle das Projekt aus der Projektliste aus.

## 4. Manuskript vorbereiten und hochladen

Die V1 akzeptiert UTF-8-kodierte Dateien im Format `.txt` und `.md`.

Für saubere Kapitel empfiehlt sich Markdown:

```markdown
# Kapitel 1 – Die Ankunft

Am frühen Morgen erreichte Mira das Dorf am Meer.

# Kapitel 2 – Das Licht

In der folgenden Nacht sah sie den alten Leuchtturm zum ersten Mal leuchten.
```

1. Wähle **Datei hochladen**.
2. Wähle dein Manuskript aus.
3. Warte, bis die Segmente in der Liste erscheinen.

Überschriften mit `#` bilden Kapitelgrenzen. Die Anwendung teilt lange Texte
automatisch in kleinere Segmente auf, damit einzelne Stellen bei Bedarf neu
erzeugt werden können.

## 5. Sprache erzeugen

1. Prüfe die Segmentliste.
2. Klicke beim ersten Segment auf **Generieren**.
3. Warte, bis sein Status **Fertig** lautet.
4. Spiele die Audiodatei über den eingeblendeten Player ab.
5. Wiederhole den Vorgang für die übrigen Segmente.

Die Standardstimme ist Qwen CustomVoice `Vivian` in deutscher Sprache. Sie kann
vor dem API-Start angepasst werden:

```powershell
$env:KRCV_QWEN_SPEAKER = 'Vivian'
$env:KRCV_QWEN_LANGUAGE = 'German'
$env:KRCV_QWEN_INSTRUCT = ''
H:\KR_Cloud_Voice\scripts\start-api.ps1
```

Für einen schnellen technischen Test ohne KI-Inferenz:

```powershell
$env:KRCV_TTS_ENGINE = 'mock'
H:\KR_Cloud_Voice\scripts\start-api.ps1
```

Danach das PowerShell-Fenster schließen oder die Variable wieder entfernen, um
zur echten Qwen-Spracherzeugung zurückzukehren.

## 6. Korrekturen vornehmen

Wenn ein Satz nicht gefällt:

1. Passe den Text im Manuskript an.
2. Lade die überarbeitete Datei in das Projekt hoch oder erstelle ein neues Projekt für die neue Fassung.
3. Erzeuge nur die betroffenen Segmente erneut.
4. Höre sie vor dem Export an.

## 7. Hörbuch exportieren

Sobald alle gewünschten Segmente den Status **Fertig** haben:

1. Klicke auf **ZIP exportieren**.
2. Lade die erzeugte ZIP-Datei herunter.
3. Entpacke sie; die Dateien heißen fortlaufend `segment-0001.wav`,
   `segment-0002.wav` usw.

Die ZIP-Datei eignet sich als Zwischenstand für Nachbearbeitung, Kapitelmarker
oder das spätere Zusammenfügen mit einem Audioprogramm.

## Häufige Probleme

| Problem | Lösung |
| --- | --- |
| Die Weboberfläche ist nicht erreichbar | Prüfe, ob beide Startskripte laufen und öffne `http://127.0.0.1:5173`. |
| Die erste Generierung dauert lange | Beim ersten Durchlauf wird das Qwen-Modell nach `runtime\cache\huggingface` geladen. Folgeaufträge sind lokal und schneller. |
| Ein Segment schlägt fehl | Prüfe, ob die API im Qwen-Modus läuft und ob genügend freier Speicher auf `H:` vorhanden ist. Danach das Segment erneut anfordern. |
| Es wird nur ein Testton erzeugt | Die API wurde mit `KRCV_TTS_ENGINE=mock` gestartet. Starte sie ohne diese Variable neu. |
| Umlaute sind fehlerhaft | Speichere das Manuskript als UTF-8. |

## Ergebnis prüfen

Eine erfolgreiche echte Referenzgeneration liegt unter
`H:\KR_Cloud_Voice\benchmarks\qwen-first-test-generation.wav`. Sie wurde als
gültige Mono-WAV-Datei mit 24 kHz geprüft.
