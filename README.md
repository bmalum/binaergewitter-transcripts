# Binärgewitter-Transkripte

Maschinell erstellte Transkripte mit Sprecherzuordnung für **327 Folgen** des Podcasts
[Binärgewitter](https://blog.binaergewitter.de/), die bisher kein Transkript hatten. Das sind alle Talk-Folgen
von #0 bis #323 ohne Auphonic-Transkript plus 14 Spezial-, Westcoast- und RadioTux-Folgen
(Januar 2011 bis Oktober 2023, zusammen rund 758 Stunden Audio).

Zusammen mit den Auphonic-Transkripten, die schon auf `download.binaergewitter.de` liegen, hat damit jede Folge
mit Audio ein Transkript.

## Dateien

`transcripts/` enthält je Folge zwei Dateien, benannt wie die Audiodateien auf `download.binaergewitter.de`:

| Datei | Inhalt |
|---|---|
| `<datum>.Binaergewitter.Talk.<nr>-speech.json` | Segmente mit Sprecher, Text und Zeitstempeln je Wort, im selben Aufbau wie die Auphonic-`-speech.json` |
| `<datum>.Binaergewitter.Talk.<nr>.vtt` | Dasselbe als WebVTT-Untertitel mit Sprecher-Tags (`<v Ingo>…`), Cues höchstens etwa 7 Sekunden lang |

Weil Namen und Aufbau den vorhandenen Dateien entsprechen, können sie direkt neben die MP3s gelegt und über
`transcript:` im Front Matter der Blogposts verlinkt werden. `manifest.json` listet jede Folge mit Dauer,
Wortzahl und Redezeit je Sprecher.

## Qualität

Die Transkripte sind vollautomatisch erstellt und nicht von Hand korrigiert.

- **Text:** Im Vergleich mit den vorhandenen Auphonic-Transkripten weichen etwa 12–13 % der Wörter ab. Auphonic ist
  ebenfalls maschinell, die Zahl ist also eine Abweichung zwischen zwei Erkennern, keine echte Fehlerrate.
  Typische Fehler sind Eigennamen und Fachbegriffe, zum Beispiel „Binary Gewitter“.
- **Sprecher:** Getestet an 17 Folgen mit Auphonic-Sprecherzuordnung (jeweils ohne diese Folge in den
  Stimmprofilen) waren im Schnitt 92,9 % der Wörter dem richtigen Sprecher zugeordnet, in der schlechtesten
  Folge 88,8 %.
- **Erkannte Namen:** Ingo, Felix, l33tname und Markus. Für sie gab es Stimmprofile aus den Auphonic-Transkripten.
- **„Gast 1“, „Gast 2“ …:** Stimmen ohne Stimmprofil, vor allem frühere Mitstreiter und Gäste. Die Nummer gilt
  **nur innerhalb einer Folge**: „Gast 1“ in zwei Folgen ist nicht unbedingt dieselbe Person. Das betrifft vor
  allem 2011–2016.
- **„Unbekannt“:** Sätze, die keiner Stimme sicher zugeordnet werden konnten (etwa 9 von 758 Stunden).
- **Kurze Einwürfe** unter 0,8 Sekunden („Hallo.“, „Ja.“) bekommen den Sprecher des vorherigen Satzes und
  sind deshalb öfter falsch zugeordnet.

Korrekturen sind willkommen, gern als Issue oder Pull Request. Besonders hilfreich: wer die „Gast“-Stimmen der
frühen Folgen ist. Mit ein, zwei Folgen, in denen eine Person sicher spricht, lassen sich die Sprecher für alle
Folgen neu zuordnen, ohne die Spracherkennung zu wiederholen.

## Wie sie entstanden sind

- **Spracherkennung:** [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) über
  NVIDIA NeMo, in 20-Minuten-Stücken, die an leisen Stellen geschnitten werden.
- **Sprecher:** Je Satz ein Stimmabdruck mit
  [speechbrain/spkrec-ecapa-voxceleb](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb), verglichen mit
  Stimmprofilen aus 17 Folgen mit Auphonic-Sprecherzuordnung. Dazu kommen eine Anpassung je Folge, eine Prüfung,
  ob ein Name in der ganzen Folge wirklich passt, und das Gruppieren unbekannter Stimmen.
- **Hardware:** 4× AWS EC2 `g6.12xlarge` (16× NVIDIA L4), rund 40 Minuten für alle Folgen.

Die Skripte liegen in `tools/`:

| Skript | Aufgabe |
|---|---|
| `boot.sh` | EC2-Startskript: Installation, danach `supervise.sh` |
| `supervise.sh` | Ein `worker.py` je GPU, Neustart nach CUDA-Fehlern, Abschalten am Ende |
| `worker.py` | Holt Folgen aus einer gemeinsamen Warteschlange in S3 (bedingte Schreibzugriffe als Sperre), transkribiert sie und berechnet die Stimmabdrücke |
| `name_speakers.py` | Sprecherzuordnung und Export der `-speech.json`; läuft ohne GPU |
| `make_vtt.py` | Erzeugt die `.vtt` aus den `-speech.json` |

Die Stimmabdrücke selbst sind nicht veröffentlicht, weil es biometrische Daten sind.

## Lizenz

Die Transkripte sind eine Bearbeitung des Podcasts Binärgewitter vom Binärgewitter-Team und stehen wie das
Original unter [Creative Commons BY-SA 3.0 DE](https://creativecommons.org/licenses/by-sa/3.0/de/).
Siehe `LICENSE`.

Die Skripte in `tools/` stehen unter der Apache-Lizenz 2.0 (`tools/LICENSE`).
