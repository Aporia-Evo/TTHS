# Kontextversuch (v4): Nutzt ein kleiner Transformer eine ignorierte Dimension aus dem Kontext?

**Status: Design vom 11.10.2026, vom Nutzer abschnittsweise freigegeben, Spec zur Durchsicht.** Noch nichts umgesetzt, nichts gelaufen.

**Grundlagen:**
- Abschluss des Farbversuchs: `farbversuch/ABSCHLUSS.md`.
- Wegwerf-Testläufe vom 11.10.2026: Machbarkeit und Format, siehe §10. Sie gehören nicht zu v4, und ihre Seeds sind keine v4-Seeds.

---

## 1. Frage und Einordnung

**Fernziel des Nutzers:** ein generalisierendes System ähnlich einem Sprachmodell.

**Frage von v4:** Ein kleiner Transformer lernt, Regeln allein aus Beispielen im Kontext zu erschließen. Eine Dimension, die Farbe, ist im Training dabei (fast) nie Regelträger. Nutzt das Modell die Farbe trotzdem, wenn eine Regel im Kontext an ihr hängt, ohne jedes Nachtrainieren?

**Zwei Mechanismen sind denkbar,** beide plausibel:
- **Allgemeiner Mechanismus:** Das Modell sucht im Kontext nach Übereinstimmungen bei allen Eigenschaften. Dann überträgt es sich auf die Farbe; die Farbe ist **offen**.
- **Gelernt zu ignorieren:** Im Training waren Farb-Übereinstimmungen reines Rauschen, und das Modell blendet sie aus. Dann ist die Farbe **geschlossen**.

**Bezug zum Farbversuch:**
- Gleiche Grundfrage (ignorierte Dimension wird relevant) und gleiche Methodik: vorab festgelegte Vorhersagen, getrennte Seeds, Einfrieren, nachträgliche Erkundungen getrennt.
- Neu: keine vorgegebenen Kandidaten, kein Erklärmodell. Gemessen wird, was das Modell selbst aus dem Kontext macht.

**Nicht Teil von v4:**
- Nachtrainieren;
- das Finden der Dimension in gelernten internen Merkmalen;
- zusammengesetzte Regeln;
- andere Aufgabenwelten.

---

## 2. Aufgabenwelt

**Objekte:**
- 4 Eigenschaften: Form, Größe, Position, Farbe (Index 3);
- je 4 Werte, jede Eigenschaft mit eigenen Tokens (16 Tokens);
- alle Werte werden unabhängig und gleichverteilt gezogen. Die Farbe ist immer vorhanden und schwankt.

**Regel je Sequenz:**
- eine Regel-Eigenschaft a und eine zufällige eineindeutige Zuordnung π ihrer 4 Werte auf 4 Antwort-Tokens;
- die Antwort eines Objekts ist π(Wert von a).

**Wahl der Regel-Eigenschaft im Training:**
- Je Sequenz wird u gleichverteilt auf [0, 1) gezogen.
- Ist u < p, ist die Farbe die Regel-Eigenschaft. Sonst entscheidet eine zweite, eigene Ziehung gleichverteilt unter Form, Größe und Position.
- **Stufen:** p ∈ {0, 0,01, 0,10, 0,25}. Bei 0,25 sind alle vier Eigenschaften gleich häufig.

**Sequenzformat:**
- K = 8 Beispiele der Form [4 Eigenschafts-Tokens, „?“, Antwort-Token], also 48 Tokens. Der Wortschatz hat 21 Tokens: 16 für Eigenschaften, 4 Antworten, „?“.
- **Reihenfolge der vier Eigenschafts-Tokens:** je Beispiel unabhängig zufällig gemischt. Welche Eigenschaft ein Token ist, steckt im Token selbst.
  - Keine Eigenschaft hat damit eine bevorzugte Stelle.
  - Das war im ersten Testlauf ein Störfaktor: Die Farbe stand dort immer direkt vor der Antwort (§10).
- **Vorhersage:** am „?“-Token jedes Beispiels. Das erste Beispiel ist reines Raten.

**Starthilfe, nur im Training:**
- Jedes Beispiel k ≥ 2 ist mit Wahrscheinlichkeit 0,3 eine Kopie eines gleichverteilt gewählten früheren Objekts. Die Kopie hat die gleichen Werte, aber eine neu gemischte Reihenfolge.
- Sie gilt in allen Stufen gleich und betrifft alle Eigenschaften gleich.
- **Grund:** Ohne Starthilfe lernte in den Testläufen kein Modell in 15.000 Schritten etwas (§10).

**Prüfsätze:**
- feste Sätze, für alle Modelle dieselben, ohne Wiederholungen, Reihenfolge wie im Training gemischt;
- 2000 Sequenzen mit Farbregel (Prüf-Seed 9001) und 2000 mit gleichverteilter bekannter Eigenschaft (Prüf-Seed 9002).

---

## 3. Modell und Training

**Modell:**
- Decoder im GPT-Stil: 3 Schichten, Breite 64, 4 Köpfe, MLP mit 4-facher Breite;
- Normierung vor jedem Block, kein Dropout, gelernte Positions-Einbettung, kausale Maske;
- Ausgabekopf über den ganzen Wortschatz. Etwa 156.000 Parameter.

**Fehlerfunktion:** Kreuzentropie an allen 8 „?“-Positionen, nur über die 4 Antwort-Logits.

**Optimierung:**
- AdamW mit Lernrate 0,001, Weight Decay 0,01, Standard-Betas;
- 500 Schritte lineares Aufwärmen, danach konstant;
- Batch 128, 30.000 Schritte;
- die Daten werden laufend aus dem Seed erzeugt.

**Seeds und Paarung:**
- Ein Modell ist (Stufe p, Seed s).
- Aus s werden getrennte Zufallsströme abgeleitet: Startgewichte, Objekte, Reihenfolgen, Wiederholungen, Zuordnungen, u-Ziehungen, Ersatz-Eigenschaft.
- Derselbe Seed in verschiedenen Stufen ergibt identische Startgewichte und identische Ziehungen. Die Modelle unterscheiden sich nur darin, welche Sequenzen eine Farbregel tragen (u < p).

**Determinismus:**
- nur CPU, ein Thread, `torch.use_deterministic_algorithms(True)`;
- PyTorch in fester Version (`kontextversuch/requirements.txt`);
- jedes Ergebnis trägt einen Fingerabdruck von Code und Umgebung wie in v2. Bitgleichheit gilt nur auf derselben Maschine.

**Zwischenstände:** bei 5.000, 10.000, …, 30.000 Schritten werden U und die Trefferquoten nur beschreibend berichtet. Für die Vorhersagen zählt allein der Stand bei 30.000 Schritten.

**Rechenaufwand:** etwa 0,18 s je Schritt auf einem Kern, also etwa 92 min je Modell. Vier Modelle laufen parallel auf 4 Kernen.

---

## 4. Messungen

Untersuchungseinheit ist das einzelne Modell.

### 4.1 Trefferquote je Position
a_M(k) ist die Trefferquote des Modells am „?“-Token von Beispiel k = 1…8, gemittelt über einen Prüfsatz. Vorhergesagt wird die Antwort mit dem größten Logit unter den 4 Antworten.

### 4.2 Ideale Vergleichsmodelle (exakt)
- **Hypothesen:** (Eigenschaft a, Zuordnung π) mit gleichverteilter Vorabwahrscheinlichkeit, 24 Zuordnungen je Eigenschaft.
  - **Ideal mit Farbe:** a ∈ {Form, Größe, Position, Farbe}, also 96 Hypothesen.
  - **Ideal ohne Farbe:** a ∈ {Form, Größe, Position}, also 72 Hypothesen.
- **Vorhersage für Beispiel k:** Unter den Hypothesen, die zu Beispiel 1…k−1 passen, wird jede Antwort nach ihrem Anteil gewichtet. Vorhergesagt wird die häufigste.
- **Trefferquote eines Beispiels:** 1/|M|, wenn die richtige Antwort in der Menge M der häufigsten liegt, sonst 0. Das entspricht zufälligem Losen bei Gleichstand.
- **Passt keine Hypothese mehr:** Das kann nur dem Ideal ohne Farbe bei Farbregeln passieren. Dann gilt 1/4, also Raten.
- Je Prüfsatz ergeben sich daraus die Kurven a_mit(k) und a_ohne(k).

### 4.3 Hauptgröße „Farbnutzung“ U
- U = Σ_{k=2..8} (a_M(k) − a_ohne(k)) / Σ_{k=2..8} (a_mit(k) − a_ohne(k)), auf dem Prüfsatz mit Farbregeln.
- Ist der Nenner ≤ 0, ist U nicht definiert und wird als Fehler gemeldet.
- **U = 0:** Das Modell verhält sich, als gäbe es die Farbe nicht.
- **U = 1:** Es nutzt die Farbe so gut wie das Ideal.
- Zur Information wird U_bekannt auf dem Prüfsatz mit bekannten Eigenschaften berichtet, mit denselben Kurven für diesen Satz.

### 4.4 Prämisse je Modell
Die Prämisse ist erfüllt, wenn a_M(8) ≥ 0,80 auf dem Prüfsatz mit bekannten Eigenschaften. Sonst hat das Modell das Erschließen aus dem Kontext nicht gelernt, und die Farbfrage ist an ihm nicht sinnvoll.

### 4.5 Nebenmessungen (beschreibend)
- **Erhaltung (Probe):**
  - Merkmale: der Zustand vor dem Ausgabekopf am „?“-Token jedes Beispiels, auf dem Prüfsatz mit bekannten Eigenschaften. Das sind 16.000 Zeilen.
  - Ziel: der Farbwert des aktuellen Objekts, vier Klassen. Ebenso für Form, Größe und Position.
  - Verfahren: multinomiale logistische Regression mit L2-Strafe 1e-3, 5-fache Kreuzvalidierung, Teilung nach Sequenzen.
  - Berichtet wird die Trefferquote gegen 0,25.
- **Bemerken:**
  - Statistik je Sequenz: der mittlere Vorhersagefehler (Kreuzentropie) an den Antworten k = 3…8.
  - Schwelle: das 95-%-Quantil dieser Statistik auf dem Prüfsatz mit bekannten Eigenschaften, je Modell.
  - Berichtet wird der Anteil der Farbregel-Sequenzen über der Schwelle.

---

## 5. Vorhersagen und Bewertung (Hauptlauf 4200–4209)

Bewertet wird bei 30.000 Schritten. Modelle mit nicht erfüllter Prämisse werden berichtet, nicht ersetzt, und fehlen in den U-Auswertungen.

| | Aussage | Bewertung |
|---|---|---|
| **P1 Prämisse** | In jeder Stufe erfüllen mindestens 9/10 Modelle die Prämisse. | Nicht erfüllt: **Abbruch**, die Methode ist in dieser Form nicht tragfähig. P2–P5 werden dann nur beschreibend berichtet. |
| **P2 Positivkontrolle** | Bei p = 0,25 ist der Mittelwert von U ≥ 0,8. | Nicht erfüllt: U ist nicht als Maß bestätigt. P3–P5 werden berichtet, aber als nicht deutbar gekennzeichnet. |
| **P3 Dosis-Wirkung** | U steigt mit p. | Siehe unten. |
| **P4 Kernfrage, p = 0** | Kategorie aus dem 95-%-t-Intervall des mittleren U: | |
| | – **geschlossen:** obere Grenze < 0,2 | |
| | – **offen:** untere Grenze > 0,5 | |
| | – **teilweise:** sonst | |
| **P5, p = 0,01** | Dieselben drei Kategorien wie P4. | |

**Trendtest für P3:**
- Weil die Seeds über die Stufen gepaart sind, wird der Page-Test verwendet und nicht Jonckheere wie im Gespräch zunächst genannt.
- Je Seed werden die U-Werte der vier Stufen in Ränge gebracht, L = Σ_j j · R_j.
- Der p-Wert kommt aus 100.000 zufälligen Rangvertauschungen innerhalb der Seeds, mit festem Zufalls-Seed 4999. Der Test ist einseitig, α = 0,05.
- Es zählen nur Seeds, deren vier Modelle alle die Prämisse erfüllen.

**Keine Richtungswette für p = 0.** Die drei Kategorien stehen vorab fest, und jedes Ergebnis wird berichtet.

**Zusätzlich berichtet:**
- U je Stufe mit Intervall und Bootstrap über die Modelle;
- die Kurven a_M(k) gegen a_mit(k) und a_ohne(k);
- U_bekannt, Probe, Bemerken und die Zwischenstände;
- Laufzeiten.

---

## 6. Ablauf

1. **Entwicklung, Seeds 4000–4001** (8 Modelle):
   - **Erlaubte Änderungen:** Lernrate, Aufwärmen, Schrittzahl, Rate der Starthilfe, Batch, Breite, Schichten, Köpfe.
   - **Entschieden wird nur nach Prämisse und Positivkontrolle.** U bei p = 0 und p = 0,01 wird protokolliert, darf aber keine Wahl beeinflussen.
   - Jede Änderung kommt mit Grund ins Protokoll.
2. **Bestätigung, Seeds 4100–4102** (12 Modelle):
   - **Regel:** Alle 12 Modelle erfüllen die Prämisse, und bei p = 0,25 ist der Mittelwert von U ≥ 0,8.
   - **Nicht bestätigt:** zurück zu 1, danach neue Bestätigungs-Seeds (4110–4112 usw.).
3. **Einfrieren** nach Entscheidung des Nutzers: Konfiguration, Prüfsummen der Quelldateien von `kontextversuch/`, Umgebung, Fingerabdruck.
4. **Hauptlauf, Seeds 4200–4209** (40 Modelle):
   - P1–P5 nach §5. Urteile gibt es nur für genau diese Seeds.
   - Alles danach ist nachträgliche Erkundung.
5. **Nichtnutzung der Seeds:** Vor jeder Stufe neu nachgewiesen, wie im Farbversuch. Die Testläufe vom 11.10.2026 nutzten nur den Torch-Seed 0 und den Prüf-Seed 123.
6. **Maschine:** Bestätigung und Hauptlauf laufen je auf einer Maschine.

**Rechenzeit auf 4 Kernen:** Entwicklung etwa 3 h je Runde, Bestätigung etwa 4,5 h, Hauptlauf etwa 15 h.

---

## 7. Aufbau

Neues Paket `kontextversuch/` neben `farbversuch/`. Jede Einheit hat eine Aufgabe:

| Modul | Aufgabe |
|---|---|
| `config.py` | Konfiguration als Dataclass, JSON lesen und schreiben, unbekannte Schlüssel sind ein Fehler |
| `tasks.py` | Sequenzen erzeugen (Training mit Starthilfe, Prüfsätze), abgeleitete Zufallsströme je Seed |
| `ideal.py` | exakte Vergleichskurven a_mit(k), a_ohne(k) |
| `model.py` | Decoder |
| `train.py` | Trainingsschleife, Determinismus, Zwischenstände |
| `evaluate.py` | Trefferquoten, U, Prämisse, Probe, Bemerken |
| `run.py` | Treiber über Stufen und Seeds: parallel, Wiederaufnahme, Sperre, Fingerabdruck (Vorbild v2) |
| `analyze.py` | P1–P5, Page-Test, Bericht |
| `freeze.py` | Einfrieren und Prüfen für `kontextversuch/` |

**Abhängigkeiten:**
- `kontextversuch/requirements.txt` mit fester PyTorch-Version, dazu numpy.
- Der Farbversuch bleibt ohne PyTorch lauffähig.

**Freeze des Farbversuchs:**
- `farbversuch.freeze verify` prüft jede `*.py` im Repo und würde mit dem neuen Paket scheitern.
- Deshalb wird vor dem ersten neuen Code das Git-Tag `farbversuch-v2-final` gesetzt. Der Farbversuch ist dann über dieses Tag prüfbar, sein eingefrorener Code bleibt unverändert.

---

## 8. Tests (testgetrieben)

**`tasks`:**
- Jede Antwort ist π(Wert der Regel-Eigenschaft), und π ist eineindeutig.
- Bei p = 0 ist die Farbe nie Regel-Eigenschaft, bei p = 1 immer.
- Die Reihenfolge der Eigenschaften ist je Beispiel gleichverteilt (Häufigkeitstest).
- Wiederholungen gibt es nur im Training und in etwa 30 %.
- Gleicher Seed in zwei Stufen ergibt identische Sequenzen außer bei Farbregel-Sequenzen.
- Die Prüfsätze sind reproduzierbar.

**`ideal`:**
- Kleinfälle sind von Hand nachgerechnet.
- a_mit(1) = a_ohne(1) = 0,25.
- a_mit(k) ≥ a_ohne(k) auf Farbregeln.
- Auf bekannten Regeln gilt a_ohne(k) ≥ a_mit(k), weil weniger Hypothesen im Spiel sind.
- Gibt es keine passende Hypothese, ergibt sich 0,25.

**`model`:** Spätere Tokens ändern frühere Vorhersagen nicht. Ausgabeformen und Parameterzahl stimmen.

**`train`:**
- Gleicher Seed auf einem Thread ergibt bitgleiche Gewichte nach N Schritten.
- Eine Mini-Konfiguration lernt eine leichte Variante (`slow`).

**`evaluate`:**
- U auf konstruierten Trefferkurven: 0, 1 und Zwischenwerte; ein Nenner ≤ 0 ist ein Fehler.
- Die Prämissenschwelle wird geprüft.
- Die Probe trifft auf konstruierten, trennbaren Daten fast immer und auf Zufallsdaten etwa 0,25.
- Die Schwelle für das Bemerken liegt auf Nulldaten bei etwa 5 %.

**`analyze`:**
- Der Page-Test stimmt bei kleinem n mit vollständiger Aufzählung überein.
- Die Kategorien von P4 und P5 an ihren Grenzen sind richtig.
- P1–P5 und der Abbruch werden mit Kunstergebnissen geprüft.

**`run` und `freeze`:** Wiederaufnahme, Sperre und Fingerabdruck wie in v2. Ein fremder Fingerabdruck führt zum Abbruch.

---

## 9. Grenzen (vorab benannt)

- **Spielaufgabe:** eine kleine Aufgabenwelt und eine Modellgröße. Die Übertragung auf große Sprachmodelle ist eine Annahme.
- **Starthilfe:** Die Wiederholungen begünstigen Mechanismen nach dem Muster „Gleiches finden, Antwort kopieren“. Das könnte das Ergebnis Richtung „offen“ schieben. Die Starthilfe ist in allen Stufen gleich, und dieser Einfluss wird als Grenze berichtet.
- **Eigene Tokens je Eigenschaft:** Die Farb-Tokens sind eigene Wörter, die das Modell immer sieht. Ob ein Ergebnis auch bei gemeinsamem Wortschatz gilt, prüft v4 nicht.
- **„Offen“ heißt nur:** nutzbar aus dem Kontext. Ein Nachweis eines bestimmten internen Mechanismus ist das nicht.

---

## 10. Wegwerf-Testläufe vom 11.10.2026 (Grundlage der Festlegungen, keine Evidenz)

Testskripte nur im Arbeitsordner, nicht im Repo. Torch-Seed 0, Prüf-Seed 123. Die Stufe p = 0 wurde nur in den ersten beiden Läufen gerechnet, mit fehlerhaftem bzw. nicht gelerntem Format; mit dem endgültigen Format nicht.

| Lauf | Aufbau | Ergebnis |
|---|---|---|
| 1 | Eigenschaften in fester Reihenfolge, Farbe direkt vor der Antwort; 2 Schichten, Breite 64, 6000 Schritte | p = 0: alles Raten. p = 0,25: nur Farbregeln gelernt (k = 8: 0,98), bekannte Eigenschaften Raten. **Störfaktor durch die Stelle der Farbe.** |
| 2 | Reihenfolge je Beispiel gemischt, Frage-Token; zwei Größen, 12.000–15.000 Schritte | Alle Modelle Raten, Fehler bei ln 4. |
| 3 | wie 2 mit Starthilfe 0,3, p = 0,25, 30.000 Schritte | 3 Schichten, Reihenfolge je Beispiel: bekannte Eigenschaften 0,94, Farbe 0,92 bei k = 8. |
| | | 2 Schichten: 0,69 und 0,80. |
| | | Reihenfolge je Sequenz: Farbe benachteiligt (0,76 gegen 0,57). |
| | | Ohne Starthilfe: erst ab etwa 20.000 Schritten Ansätze (0,48). |

**Festlegungen daraus:** gemischte Reihenfolge je Beispiel, Frage-Token, Starthilfe 0,3, 3 Schichten, 30.000 Schritte.
