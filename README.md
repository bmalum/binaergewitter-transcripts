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

`corrections/` enthält Korrekturen für Folgen, die schon ein Auphonic-Transkript haben. Bisher ist das
Talk #227: Auphonic hat dort 79 Minuten mit dem gemeinsamen Sprecher „IngoundFelix“ markiert. In der korrigierten
Datei sind sie auf Ingo (38,8 min) und Felix (40,2 min) verteilt, nach derselben Stimmgruppierung wie unten. Text und
Zeiten sind die von Auphonic. Weil die Datei keine Wortzeiten hat, bekommt jedes Auphonic-Segment einen Sprecher;
bei Segmenten, in denen beide sprechen, ist das nur einer der beiden (85 von 396 Segmenten sind gemischt oder ohne
Stimmbeleg). Auf den Segmenten, die Auphonic selbst l33tname zuordnet, erkennt das Verfahren 96,9 % der Sekunden
richtig. Zum Austausch der Datei auf `download.binaergewitter.de` müssen die Maintainer die Dateien ersetzen.

## Qualität

Die Transkripte sind vollautomatisch erstellt und nicht von Hand korrigiert.

- **Text:** Im Vergleich mit den vorhandenen Auphonic-Transkripten weichen etwa 12–13 % der Wörter ab. Auphonic ist
  ebenfalls maschinell, die Zahl ist also eine Abweichung zwischen zwei Erkennern, keine echte Fehlerrate.
  Typische Fehler sind Eigennamen und Fachbegriffe. Die häufigsten davon sind nachträglich korrigiert (siehe
  „Textkorrekturen“), zum Beispiel „ButterFS“ → btrfs, „System D“ → systemd, „Lesefu“ → Lesefoo. Es bleiben
  Fehler, die niemand gefunden hat, vor allem Verhörer, die wie ein echtes deutsches Wort aussehen.
- **Sprecher:** Jede Stimme ist namentlich zugeordnet (siehe unten). Getestet an Folgen mit Auphonic-Sprecherzuordnung
  waren im Schnitt etwa 92–93 % der Wörter dem richtigen Sprecher zugeordnet, in der schlechtesten Folge 88,8 %.
  Für die frühen Folgen mit Pfleidi, Marc und Mat gibt es keine solche Referenz. Dort stützen sich die Namen auf
  Shownotes und auf das, was die Leute in den Folgen selbst sagen („Ich bin der Pfleidi“, „Hallo, Jan“), und es
  gibt keinen Widerspruch zu den Shownotes der Folgen, die ihre Besetzung nennen.
- **Kurze Einwürfe** unter 0,8 Sekunden („Hallo.“, „Ja.“) bekommen den Sprecher des vorherigen Satzes und
  sind deshalb öfter falsch zugeordnet.
- **Stimmen mit wenig Redeanteil** (unter einer Minute pro Folge) bekommen keinen eigenen Sprecher und werden dem
  ähnlichsten Sprecher der Folge zugeschlagen.

Korrekturen sind willkommen, gern als Issue oder Pull Request.

## Wer spricht

Die Namen stehen so im `speaker`-Feld der JSON-Dateien und in den `<v …>`-Tags der VTT-Dateien.

| Sprecher | Wer | Folgen |
|---|---|---|
| Felix, Ingo | Felix Richter, Ingo Ebel | 2011–2023 |
| l33tname, Markus | der zweite Felix, Markus Schlichting | 2017–2023 bzw. ab Ende 2015 (und einmal 2012 in Talk #18) |
| Pfleidi | Sven Pfleiderer | 108 Folgen, 2011–2020 |
| Marc | Marc Seeger (rb2k) | 74 Folgen, 2011–2020 |
| Mat | Matthias Wenz (ranterle) | 65 Folgen, 2013–2017 |
| Jan | Gast in Talk #11, #14, #44, #46 | 2012–2013 |
| Jan (Hackerspace) | Gast im Hackerspace-Spezial (RadioTux #3), eine andere Stimme als „Jan“ | 2011 |
| Schmittlauch | Talk #181 und #208 (FrOSCon) | 2017–2018 |
| Torbjörn, Andreas | Spezial #4 (Distributed Computing) | 2012 |
| Walter Kriha | RadioTux #2 (Sichere Systeme) | 2011 |
| Dirk | RadioTux #1 (NoSQL) | 2011 |
| Frank, Marcel, Thomas, Taki, Lukas, Tobi, Toby, Jörg | je eine Folge: Talk #86, #111, #149, #164, Westcoast #2, #183 (Tobi und Toby), Spezial #7 (NixOS) | 2014–2017 |

So wurden die Namen gefunden:

- **Pfleidi und Marc** sind die Stimmen, die vorher als „Gast 1“ und „Gast 2“ liefen, vor allem in den Westcoast-
  Folgen. In Westcoast #1 sagt Marc „Okay, Pfeili, ich glaube, wir sind durch“, und die Shownotes nennen Pfleidi
  und Marc. In Talk #5 sagt Pfleidi „Ich bin der Pfleidi“, in Westcoast #6 sagt Marc „Ich bin Marc“, und in
  Talk #75 stellt sich die Runde mit „mir, Marc und mit Matt“ vor.
- **Mat** ist die dritte Stimme der Jahre 2013 bis 2017 („Oh hi, ich bin Matthias oder Matt“ in Talk #74, Besetzung
  von Spezial #5 laut Shownotes: Felix, Marc, Mat, Pfleidi und Ingo).
- **Gäste** stehen in den Shownotes der jeweiligen Folge („Heute mit dabei: Lukas“) oder werden zu Beginn der Folge
  vorgestellt. Dieselbe Stimme in mehreren Folgen gehört zum selben Namen: Schmittlauch in Talk #181 und #208, Jan in
  vier Talks von 2012 und 2013.
- Unsicher ist die Zuordnung von **Tobi und Toby** in Talk #183: Beide heißen im Transkript „Tobi“, die Shownotes
  schreiben „Tobi und Toby“. Wer von beiden wer ist, steht nicht eindeutig fest. Ebenso ist offen, ob die beiden
  „Jan“ dieselbe Person sind. Die Stimmen sind verschieden, deshalb heißt der eine „Jan (Hackerspace)“.
- Auch in den Folgen, in denen vorher nur Ingo, Felix oder Markus erkannt wurden, hat sich einiges geändert: In
  frühen Folgen steckte oft Pfleidi unter „Ingo“, und in einigen Folgen von 2017 lief Ingo als „Gast 1“.

## Textkorrekturen

Die Spracherkennung hört Eigennamen und Fachbegriffe oft falsch („ButterFS“ statt btrfs, „System D“ statt systemd,
„Lesefu“ statt Lesefoo, „Pürzen“ statt Fürzen). Nachträglich sind rund 12.400 Stellen in allen 327 Folgen korrigiert:

- **Regeln** (`tools/fix_terms.py`, rund 7.400 Stellen): Verhörer, die überall gleich falsch sind, etwa Produkt- und
  Personennamen (McAfee, Tizen, ownCloud, Torvalds, Stallman), die Rubrik „Lesefoo“, „Heise“ (oft als „heiße“ erkannt)
  und das Zeichen „⁇“, das die Erkennung für `+` und `&` ausgibt („C ⁇“ → C++, „AT ⁇ T“ → AT&T). Wörter, die es auch
  als normales Deutsch gibt („Nass“ für NAS, „Skala“ für Scala, „Wim“ für Vim), werden nur ersetzt, wenn der Kontext
  passt. Die Wortzeiten bleiben dabei passend zum Text.
- **Durchsicht pro Folge** (`tools/term_fixes/episode_review.json` und `second_check.json`, rund 5.000 Stellen): Pro
  Folge wurden die Sätze mit Wörtern, die kein Wörterbuch und keine Shownotes kennen, zusammen mit den Shownotes
  durchgesehen; Begriffe aus den Shownotes, die im Transkript nie vorkommen, wurden gesucht. Vorschläge, bei denen sich
  die erste Durchsicht nicht ganz sicher war, hat ein zweiter Durchgang unabhängig geprüft (671 von 719 bestätigt, 13
  mit geänderter Schreibweise, 35 verworfen). Jede Korrektur steht mit Folge, Satznummer, altem und neuem Text in den
  Dateien.
- **Nicht korrigiert** sind Verhörer in Sätzen, die niemand beanstandet hat, Wörter, bei denen unklar bleibt, was
  gemeint war („Nupsi“, „Blafu“), und Scherze der Hosts („Wolgograd“, „Premiärquelle“, „Dingsi“).

Es ist keine Vollkorrektur. Wer in einer Folge etwas findet, kann es gern als Issue oder Pull Request melden.

## Wie sie entstanden sind

- **Spracherkennung:** [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) über
  NVIDIA NeMo, in 20-Minuten-Stücken, die an leisen Stellen geschnitten werden.
- **Sprecher, erste Runde:** Je Satz ein Stimmabdruck mit
  [speechbrain/spkrec-ecapa-voxceleb](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb), verglichen mit
  Stimmprofilen aus 17 Folgen mit Auphonic-Sprecherzuordnung. Das erkannte Ingo, Felix, l33tname und Markus, aber
  keine Stimmen ohne Profil (damals „Gast 1“, „Gast 2“ …) und nicht zuverlässig die Hosts der frühen Jahre.
- **Sprecher, zweite Runde (aktueller Stand):** Die Stimmabdrücke jeder Folge werden ohne Vorlage gruppiert, also eine
  Gruppe je Stimme. Diese Gruppen werden über alle Folgen hinweg zu Personen zusammengefasst, zum Beispiel Pfleidi in
  108 Folgen von 2011 bis 2020. Die Personen bekommen ihre Namen aus Shownotes und Aussagen in den Folgen (siehe oben).
  Auf den 10 Auphonic-Folgen, deren Sprecher alle bekannt sind, liegt das bei 92,1 % richtigen Wörtern, die erste Runde
  bei 92,0 %. Der Gewinn liegt bei den frühen Folgen, wo die erste Runde Stimmen vertauschte oder nicht benennen konnte.
- **Hardware:** 4× AWS EC2 `g6.12xlarge` (16× NVIDIA L4), rund 40 Minuten für alle Folgen.

Die Skripte liegen in `tools/`:

| Skript | Aufgabe |
|---|---|
| `boot.sh` | EC2-Startskript: Installation, danach `supervise.sh` |
| `supervise.sh` | Ein `worker.py` je GPU, Neustart nach CUDA-Fehlern, Abschalten am Ende |
| `worker.py` | Holt Folgen aus einer gemeinsamen Warteschlange in S3 (bedingte Schreibzugriffe als Sperre), transkribiert sie und berechnet die Stimmabdrücke |
| `name_speakers.py` | Sprecherzuordnung der ersten Runde und Export der `-speech.json`; läuft ohne GPU |
| `relabel.py` | Sprecherzuordnung der zweiten Runde: Stimmen je Folge gruppieren, zu Personen zusammenfassen, benennen. Die Namen und ihre Belege stehen im Skript |
| `fix_terms.py` | Textkorrekturen: Regeln für falsch erkannte Begriffe und Einspielen der Einzelkorrekturen aus `term_fixes/` (`--manual`) |
| `make_vtt.py` | Erzeugt die `.vtt` aus den `-speech.json` |

`name_speakers.py` und `relabel.py` brauchen die Stimmabdrücke der Sätze. Sie sind nicht veröffentlicht, weil es
biometrische Daten sind.

## Lizenz

Die Transkripte sind eine Bearbeitung des Podcasts Binärgewitter vom Binärgewitter-Team und stehen wie das
Original unter [Creative Commons BY-SA 3.0 DE](https://creativecommons.org/licenses/by-sa/3.0/de/).
Siehe `LICENSE`.

Die Skripte in `tools/` stehen unter der Apache-Lizenz 2.0 (`tools/LICENSE`).
