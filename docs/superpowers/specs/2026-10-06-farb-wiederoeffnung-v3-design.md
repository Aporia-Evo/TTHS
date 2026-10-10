# Farbversuch v3: Erklären über die ganze Serie kalibrieren (ENTWURF)

**Status: zurückgestellt (10.10.2026).** Der Farbversuch ist auf Entscheidung des Nutzers abgeschlossen (`farbversuch/ABSCHLUSS.md`). Dieser Entwurf ist vollständig entschieden, aber nicht umgesetzt; er bleibt als Option liegen.

**Entwurf vom 06.10.2026.** Nicht eingefroren.
- Eingetragen sind die Entscheidungen E1–E8 des Nutzers vom 07.10.2026 und E10 vom 08.10.2026 (nach vorab festgelegter Regel). Alle stehen in §12.
- Die Entwicklungsprüfungen D1–D3 und E10 sind erledigt: `farbversuch/results/entwicklung_v3/`.
- E9 hat der Nutzer am 10.10.2026 entschieden: z-Statistik für S1. Damit sind alle Entscheidungen getroffen; als Nächstes folgen der Umsetzungsplan und die Umsetzung.
- Kein Lauf auf frischen Seeds ohne ausdrückliche Freigabe.

**Grundlagen:**
- Spec v2 (`2026-10-03-farb-wiederoeffnung-v2-design.md`), eingefroren mit `b9589ce`;
- Hauptlauf 400–409 (`ab439a2`) und Bericht `farbversuch/BERICHT.md` (`cbae948`);
- nachträgliche Diagnose `farbversuch/results/nachtrag_diagnose/`.

---

## 0. Stellung zu v2

- **v2 ist abgeschlossen.** Alle 10 Hauptlauf-Seeds liefen nach den eingefrorenen Regeln.
  - P1, P2, P4 und P5 sind erfüllt. **P3 ist nicht erfüllt** (6/10), das **Abbruchkriterium ist ausgelöst**.
  - Das bleibt das Ergebnis von v2. v3 ändert daran nichts.
- **Alles in diesem Entwurf ist nachträglich abgeleitet**, aus Daten verbrauchter Seeds (0, 400–409, 500–504, 510–514).
  - Aus diesen Seeds wird kein Erfolg einer v3 behauptet.
  - Einzelne Seeds (etwa 405) entscheiden nichts. Die Diagnose lief auf allen 10 Hauptlauf-Seeds.
- **Eine v3 gilt erst als geprüft** nach einer Bestätigung und einem Hauptlauf auf frischen Seeds (§9).

---

## 1. Diagnose: Befund

Die Diagnose lief nur für M3-B auf den Seeds 400–409. Methode und Rohdaten: `farbversuch/results/nachtrag_diagnose/`. In diesem Abschnitt steht zuerst, was beobachtet wurde, dann, was offen ist.

### 1.1 Belegt (beobachtet, auf verbrauchten Seeds)

**B1 Nachbau.**
- M3-B allein, neu gerechnet, reproduziert auf allen 10 Seeds den v2-Hauptlauf exakt: Übungs-Ontologie, δ, `p_global` und jede Öffnung unter `global` und `red` nach Merkmal, Episode und Gewinn (bis 1e-10).
- Die Nachspielung ist **adaptiv** wie der Einsatz: Basis = Übungs-Ontologie + bisher geöffnete Merkmale, Start beim in v2 bemerkten Prüfpunkt. So wurden alle Regeln R0–R3 nachgespielt, auf allen 10 Seeds mit derselben Skriptfassung, auch auf Seed 405.

**B2 Kein echter Effekt unter `global` (H3 widerlegt).**
- Daten: je Seed 3000 Episoden `global` (49.739–52.477 Schritte), Basis = Übungs-Ontologie.
- Ergebnis: Kein Kandidat ist in allen 5 Teilungen positiv, weder bei Teilung nach Zeilen noch nach Episoden. Der größte mittlere Gewinn ist 0,00011.
- Zum Vergleich: Die vier v2-Fehlöffnungen hatten Gewinne von 0,0014–0,0017, die richtige Öffnung unter `red` im selben Großtest 0,058–0,066.

**B3 Mehrfachprüfung.**
- Aufbau: Auf den 20 Null-Strömen wird bei jedem Prüfpunkt von E = 110 bis 400 erzwungen erklärt (30 Runden), mit dem v2-δ und der Übungs-Ontologie als Basis.
- Ergebnis: Mindestens eine Öffnung in 5–17 von 20 Strömen bei Teilung nach Zeilen, in 11–18 von 20 bei Teilung nach Episoden.
- Auf den Endpuffern, aus denen δ in v2 kalibriert ist, überschreitet per Konstruktion kein Strom δ.
- Folgerung: δ je Erklärung kontrolliert die Serie nicht.

**B4 Serien-δ, adaptiv nachgespielt** (δ aus den 30 Runden von B3, Teilung jeweils gleich in Gewinn und Schwelle):

| Regel | Teilung | δ (Spanne über Seeds) | `global`: Seeds mit Öffnung | `red`: erste Öffnung „Farbe 0“ | `red`: Zusatzöffnungen | Latenz `red` (Mittel) |
|---|---|---|---|---|---|---|
| R0 (v2) | Zeilen | 0–0,0018 | 4/10 | 10/10 | 7 | 49 |
| R2 | Zeilen | 0,0023–0,0037 | 0/10 | 10/10 | 0 | 49 |
| R3 | Episoden | 0,0037–0,0068 | 0/10 | 10/10 | 0 | 54 |

Abstände zur Schwelle, je Teilung mit eigener Schwelle:

| Abstand | R2 (Zeilen) | R3 (Episoden) |
|---|---|---|
| Kleinster Gewinn der richtigen Öffnung unter `red`, als Vielfaches von δ | 1,6 (Seed 402) | 1,8 (Seed 402) |
| Größter bester Gewinn einer `global`-Runde, Anteil an δ | 0,74 (Seed 400) | 0,88 (Seed 403) |
| Größter bester Gewinn unter `red` nach dem Treffer, Anteil an δ | 0,94 (Seed 401) | 0,48 |

**B5 Gemischte Regel.** R1 (Gewinne nach Episoden, δ aus Zeilenteilung) öffnet unter `global` in 6/10 Seeds. Weil Gewinn und Schwelle aus verschiedenen Teilungen stammen, sagt das nichts über die Teilung nach Episoden.

### 1.2 Nicht belegt oder offen

- **U1 Nicht alle zulässigen Zeitpunkte.**
  - Die Null-Serie begann bei E = 110, also am Wechselzeitpunkt ausgerichtet.
  - Zulässig sind 37–38 Prüfpunkte je Strom, ab E = 30 oder 40 (§3.3). Gezählt wurden die Prüfpunkte mit ≥ 500 Pufferschritten unter `none` in v2.
  - Die fehlenden 7–8 frühen Runden haben kleinere, noch nicht volle Puffer (ab 500 Schritten) und können das Serienmaximum erhöhen. Das δ nach §3 kann also größer sein als in B4, die Abstände unter `red` kleiner.
- **U2 `walls` nicht nachgespielt.**
  - Die v2-Fehlöffnung „Farbe 3“ bei Seed 407 (Episode 350) ist ungeprüft.
  - `none` wurde ebenfalls nicht nachgespielt. In v2 hat dort kein System etwas bemerkt.
- **U3 Zusatzöffnungen ohne eigene Kalibrierung.** Das Serien-δ ist mit Basis = Übungs-Ontologie bestimmt. Dass R2/R3 unter `red` nichts zusätzlich öffnen, ist eine Beobachtung. Für die Basis „Übungs-Ontologie + geöffnetes Merkmal“ ist nichts kalibriert.
- **U4 Höheres Rauschen.** Die Null-Ströme haben das Grundrutschen 0,1, `global` liegt bei 0,21–0,28. „0/10 unter `global`“ ist eine Beobachtung, keine Folge der Kalibrierung (§4).
- **U5 Nicht unabhängig.**
  - Die Regel wurde auf 400–409 abgeleitet und dort angesehen.
  - Seed 510 ist nicht nachgespielt. Seine `global`-Fehlöffnung lag beim ersten Erklären mit Gewinn 0,0033, also innerhalb der Spanne der Serien-δ von 400–409 (Spec v2, B.2).
- **U6 Andere Systeme nicht gerechnet.** Für S1-B, S1-A und M3-A gibt es keine Serienkalibrierung. P4 und P5 unter v3 sind unbekannt.
- **U7 Kein eigener Beleg aus den Kalibrierströmen.** Dass die 20 Kalibrierströme unter dem Serien-δ nichts öffnen, ist per Konstruktion so.
- **U8 Zeilen gegen Episoden** (Korrektur einer früheren Aussage).
  - Die Daten unterscheiden die beiden Teilungen nicht. Die Zählungen sind gleich, die Latenz bei Episoden ist etwas höher (54 statt 49).
  - Mein früheres Argument, die Teilung nach Episoden mache δ „doppelt so groß“ und verfehle damit den kleinsten echten Gewinn (0,0041), verglich einen Gewinn aus Zeilenteilung mit einem δ aus Episodenteilung. Es ist ungültig und zurückgezogen.
- **U9 Seed 405 im Einzelnen.** Die Aussage zu Seed 405 ist durch die vollständige adaptive Nachspielung gedeckt: Unter `global` öffnet R2 nichts, unter `red` nur „Farbe 0“, bei δ von 0 auf 0,0028. Das gilt aber nur für das δ aus B3 (ab E = 110, Basis Übungs-Ontologie), nicht für das δ nach §3.

### 1.3 Deutung (Annahme)

- Die v2-Fehlöffnungen unter `global` und die Zusatzöffnungen unter `red` passen zu einer unkorrigierten Mehrfachprüfung über die Erklärrunden. Zu einem echten Merkmalseffekt passen sie nicht.
- Ob eine Serienkalibrierung das allgemein behebt, ohne die richtige Zuschreibung zu verlieren, ist offen. Das prüft erst §9.

---

## 2. Was v3 ändert und was nicht

**Ändert sich (Kern):**
- **K1:** Die Mindestverbesserung δ von M3 wird über die ganze Erklärserie kalibriert (§3), für die erste Öffnung.
- **K2:** Die Schwelle von S1 wird ebenso über die Serie kalibriert, auf dem standardisierten Unterschied z (E9, §7.1).
- **K3:** Zusatzöffnungen werden ausdrücklich behandelt (§5, Entscheidung E3).
- **K4** (entfällt mit E9): Geplant war, die Permutationszahl von S1-B auf 10.000 zu erhöhen. Mit der z-Statistik braucht das Erklären von S1 keine Permutationen mehr; das Vor-Öffnen bleibt bei 1000.
- **K5:** S1 öffnet höchstens ein Merkmal je Runde, das mit dem größten z (E8, E9, §7.1, §8). Damit gilt für M3 und S1 dieselbe Trefferdefinition.

**Bleibt wie in v2 (eingefroren `b9589ce`):**
- Welt, Bedingungen, Wechsel bei Episode 100, 400 Episoden;
- Routine, Vorwärtsmodell, Trainings-Hyperparameter (`frozen_config.json`);
- Prämissen P1/P1b und ihre Grenzen;
- Bemerken: M3-Fenster und CUSUM mit denselben Schwellen;
- Kandidaten, Übungs-Ontologie, Residualisieren;
- Teilung der Kreuzvalidierung nach Zeilen, falls E2 nicht anders entscheidet;
- Prüfintervall 10, höchstens 3 Öffnungen je System (außer bei Z1, §5.2).

Eine Änderung zur Zeit: v3 ändert die Kalibrierung des Erklärens und sonst nichts, was ein Ergebnis beeinflusst. Ein Unterschied zu v2 lässt sich dann ihr zuschreiben.

---

## 3. Serienkalibrierung für M3 (erste Öffnung)

### 3.1 Kalibrierströme
- Es sind die 20 Null-Ströme aus v2: Tag `NULL`, Strom j = 0…19, Grundrutschen, Grundwanddichte, kein Rot. Die Routine handelt.
- Sie dienen weiter auch dem Bemerken. Die Fehlergrenze in §4 nutzt das Bemerken nicht, deshalb dürfen es dieselben Ströme sein.
- **Pflicht:** `n_null_episodes == n_deploy_episodes` (beide 400). Sonst bricht der Lauf mit Fehler ab: Der Zeitraster der Kalibrierung muss dem des Einsatzes gleichen.

### 3.2 Puffer
- B_j(E) ist für Strom j nach E abgeschlossenen Episoden: die letzten min(s_j(E), `buffer_size`) Schritte, wobei s_j(E) die Zahl aller Schritte bis dahin ist.
- Das ist genau der Inhalt des Ringpuffers eines frischen Monitors, der Strom j sieht. Kalibrierung und Einsatz nutzen dieselbe Pufferfunktion.

### 3.3 Zulässige Zeitpunkte (E10(b), gilt gleich für M3-A und M3-B)
- 𝓔_j = { E : E mod 10 = 0, 10 ≤ E ≤ 400, n_j(E) = `buffer_size` }. Erklärt wird also **nur bei vollem Puffer**, in Kalibrierung und Einsatz gleich. Dabei ist n_j(E) die Zahl der Pufferschritte im Prüfpunkt E.
- **Einheitlich für M3-A und M3-B:**
  - Die Regel hängt nur von der Pufferfüllung ab, nicht von der Kandidatenmenge.
  - Beide Systeme nutzen sie identisch, jedes mit seiner eigenen Schwelle aus der eigenen Null-Serie (eigene Kandidaten, eigene Übungs-Ontologie).
  - Auch die Teilung ist für beide gleich: nach Zeilen (E2). Die Nebenauswertung nach Episoden läuft nur für M3-B, aus Kostengründen.
- **Bemerken unverändert:** Fenster 500, ab n ≥ 500.
  - Bemerkt ein System, bevor der Puffer voll ist, erklärt es erstmals beim ersten Prüfpunkt mit vollem Puffer.
  - Danach erklärt es bei jedem Prüfpunkt, denn der Puffer bleibt voll.
- **Unabhängig von Alarm und Wechsel:** 𝓔_j hängt nicht von der Meldeschwelle ab, nicht davon, ob Strom j alarmiert, und nicht von `switch_episode`.
- **Begründung:** Im Einsatz erklärt M3 nur bei vollem Puffer, nach dem Bemerken aber bei jedem solchen Prüfpunkt. 𝓔_j enthält also jeden möglichen Erklärzeitpunkt.
- **Warum erzwungen:** Die Meldeschwelle ist das Maximum derselben 20 Null-Ströme. Unter der strikten Regel „>“ überschreitet deshalb kein Kalibrierstrom seine eigene Schwelle. Eine Kalibrierung nur nach einem Alarm hätte keine einzige Runde.
- **Umfang** (Entwicklungsdaten 400–409, 510–514):
  - Null-Ströme: voll ab E = 100–150, also 26–31 Zeitpunkte je Strom, im Mittel 28,3.
  - Einsatzströme: voll ab E = 110–140, Median 120.
- **Warum (b):** Das wurde nach vorab festgelegter Regel aus (a) „ab n ≥ 500“, (b) und (c) „Normierung n · G“ gewählt, jeweils mit beiden Teilungen (§12, E10).
  - Unter (a) bestimmten frühe Runden mit kleinem Puffer δ₁ und machten die Abstände der richtigen Öffnungen knapp.

### 3.4 Zulässiger Gewinn je Runde
- Berechnung: `imp, cand = m3_improvements(Z, A, D, F, K₀, make_rng(seed, CV, E), …)` auf B_j(E), mit den Fit-Parametern des Einsatzes.
  - K₀ ist die Übungs-Ontologie des Systems. Die Kandidaten sind alle Spalten außerhalb von K₀.
  - Der Zufallsschlüssel der Teilung ist derselbe wie im Einsatz beim selben E.
- G_j(E) = größter Mittelwert über die Kandidaten, die in allen 5 Teilungen > 0 sind. Gibt es keinen solchen Kandidaten, ist G_j(E) = 0. Das ist `m3_null_gain`.
- Ein Kandidat ist also zulässig genau dann, wenn er die erste Bedingung von `select_m3` erfüllt.

### 3.5 Statistik und Schwelle
- T_j = max über E ∈ 𝓔_j von G_j(E).
- δ₁ = max_j T_j. Das ist `null_threshold(T, max_alarms = 0)`.

### 3.6 Einsatzregel
- Unverändert `select_m3(imp, cand, δ₁)`: Geöffnet wird nur, wenn alle Teilungen > 0 sind und das Mittel strikt > δ₁ ist.
- **Folge:** Macht M3 im Einsatz eine erste Öffnung, dann gibt es ein E ∈ 𝓔 mit G(E) > δ₁, also T_Einsatz > δ₁. Das ist die Brücke zu §4 und wird getestet (§10, T3).

### 3.7 Teilung
- Für Gewinne und δ₁ gilt immer dieselbe Teilung.
- Wird nach Episoden geteilt (E2), dann entsteht δ₁ aus derselben Episodenteilung auf denselben Null-Strömen.

---

## 4. Reichweite der Fehlergrenze

**Aussage.** Für jeden Seed und jedes M3-System gilt unter einer Voraussetzung: Einsatzstrom und die 20 Kalibrierströme sind austauschbar. Dann ist

> P(T_Einsatz > δ₁) ≤ 1/21, also P(M3 öffnet in diesem Einsatzstrom irgendetwas) ≤ 1/21.

**Begründung:** Bei 21 austauschbaren Werten ist die Wahrscheinlichkeit, dass ein bestimmter strikt größer als alle anderen ist, höchstens 1/21. Bindungen ändern daran nichts, auch δ₁ = 0 nicht.

**Prüfschema.** Aussage, Voraussetzungen, Begründung und Umsetzung werden getrennt festgehalten und getrennt geprüft:

| Teil | Inhalt | Wie geprüft |
|---|---|---|
| Aussage | P(T_neu > max(T₁, …, T₂₀)) ≤ 1/21; T ist das Maximum der vollständigen Erklärserie nach §3 | – |
| V1 Austauschbarkeit | Einsatzstrom und Kalibrierströme sind austauschbar | Nur durch den Versuchsaufbau: Sie gilt für `none` und vor dem Wechsel, sonst nicht (unten). |
| V2 Gleiche Statistik | T ist in Kalibrierung und Einsatz dieselbe Funktion des Stroms: Puffer, Zeitpunkte, Basis, Kandidaten, Teilungsschlüssel | Tests T1, T2, T7 (§10) |
| V3 Öffnung setzt Überschreitung voraus | Jede erste Öffnung im Einsatz setzt T_Einsatz > δ₁ voraus | Tests T3, T4 |
| Begründung | Rangargument wie oben | Elementar. T6 prüft es zusätzlich an synthetischen Strömen. |

Ein formaler Beweis, etwa in Lean mit unabhängiger Prüfung wie bei [Comparator](https://github.com/leanprover/comparator), würde nur die Begründung absichern, also den einfachsten Teil. Er sagt nichts darüber, ob V1 unter `global` oder für Zusatzöffnungen gilt, und nichts über V2 im Python-Code. Er ist deshalb nicht vorgesehen.

**Was die Aussage bedeutet:**
- Sie betrifft das Überschreiten einer vorab festgelegten Serienstatistik.
- Sie ist **gemittelt** über die Zufälligkeit von Kalibrier- und Einsatzströmen. Bedingt auf die 20 Kalibrierströme eines Seeds kann die Rate höher sein.
  - Bei stetigem T ist die bedingte Überschreitungsrate Beta(1, 20)-verteilt: im Mittel 4,8 %.
  - In etwa 12 % der Seeds liegt sie über 10 %, in etwa 3,9 % über 15 %.
- **Konservativ:** Das Bemerken bleibt unberücksichtigt, und es wird bei allen Zeitpunkten in 𝓔 erklärt.
- **Über 10 Seeds:** Unter `none` sind im Erwartungswert höchstens 10/21 ≈ 0,48 Seeds mit einer Öffnung.

**Austauschbar ist nur `none`.** Dort gelten dieselben Weltparameter, und die Zufallsströme sind unabhängig (Tag `DEPLOY` statt `NULL`).

**Auch abgedeckt: Öffnungen vor dem Wechsel, in jeder Bedingung.** Bis Episode 100 sind alle Bedingungen gleich verteilt wie die Null-Ströme. Eine Öffnung bei E ≤ 100 verlangt G(E) > δ₁ ≥ max_j max_{E ≤ 100} G_j(E). Dafür gilt dieselbe Grenze 1/21.

**Nicht abgedeckt:**
- `global`: höheres Rauschen, die Verteilung von G ändert sich;
- `walls`;
- jede Öffnung unter `red`, auch eine falsche erste Öffnung;
- Zusatzöffnungen (§5);
- der Vergleich zwischen Systemen.

P3 bleibt deshalb eine empirische Vorhersage.

**Kein Beleg:** Dass die eigenen 20 Kalibrierströme nichts öffnen, folgt aus der Konstruktion und belegt nichts (U7).

---

## 5. Erste und zusätzliche Öffnungen

### 5.1 Erste Öffnung
- Basis K₀ = Eingaben des Vorwärtsmodells + Übungs-Ontologie.
- δ₁ nach §3. Nur für die erste Öffnung gilt die Grenze aus §4.

### 5.2 Zusatzöffnungen
Nach einer ersten Öffnung, insbesondere nach einem echten Treffer unter `red`, ist die Basis K = K₀ ∪ geöffnete Merkmale. Varianten (Entscheidung E3):

- **Z1, nur eine Öffnung:** `max_open = 1` für alle Systeme.
  - Es gibt keine Zusatzöffnungen.
  - Ein System, dessen erste Öffnung falsch war, kann sich nicht mehr korrigieren.
- **Z2, Schwellentabelle je Basis:**
  - Für jede erreichbare Basis K (höchstens `max_open` − 1 geöffnete Merkmale) wird δ_K wie in §3 bestimmt, mit Basis K, auf denselben 20 Null-Strömen. Das geschieht in Phase 1, vor jedem Einsatz.
  - Im Einsatz gilt δ_K der aktuellen Basis.
  - **Umfang für M3-B** (Übungs-Ontologie bisher immer {Wand}, 5 weitere Kandidaten): 1 + 5 + 10 = 16 Basen.
  - **Für M3-A nicht machbar:** 1192 + C(1192, 2) Basen.
  - **Abgedeckt** ist die Mehrfachprüfung bei geänderter Basis unter der vollständigen Nullhypothese.
  - **Nicht abgedeckt** ist die teilweise Nullhypothese nach einem echten Treffer. Der Einsatzstrom enthält dann einen echten Effekt und ist mit Null-Strömen nicht austauschbar; auch Fehlspezifikation bleibt außen vor.
- **Z3, die erste Öffnung entscheidet (gewählt, E3):**
  - Vorhersagen, Abbruchkriterium und Bestätigung zählen **nur die erste Öffnung** je Strom.
  - Zusatzöffnungen laufen mit δ₁ weiter. Sie werden getrennt beschrieben: Merkmal, Episode, Gewinn, Gewinn/δ₁.
  - Sie tragen keine Fehlergarantie und gehen in kein Urteil ein.
  - **Vorteile:** gleich für alle vier Systeme, keine Zusatzkosten. Die bewertete Größe hängt nur von δ₁ ab.
  - **Nachteil:** Zusatzöffnungen bleiben unkontrolliert. In B4 lag der größte Gewinn nach dem Treffer bei 0,94 δ, also knapp unter der Schwelle.

### 5.3 Regeln gegen zirkuläre Statistik
- **N1:** Jede Schwelle wird in Phase 1 nur aus Null-Strömen bestimmt. Keine Einsatzdaten einer Bedingung gehen in eine Schwelle ein.
- **N2:** Keine Basis und keine Schwelle wird mit Kenntnis des richtigen Merkmals gewählt.
  - Verboten ist etwa, mit der Basis „Übungs-Ontologie + Farbe 0“ zu kalibrieren, weil das die richtige ist.
  - Z2 rechnet alle erreichbaren Basen gleich.
- **N3:** Keine Regel, Schwelle oder Variante wird auf Seeds gewählt, auf denen sie bewertet wird. 0, 400–409, 500–504 und 510–514 sind nur Entwicklungsdaten.
- **N4:** Die Kalibrierströme dienen nie als Beleg für eine Fehlerrate (§4, „Kein Beleg“).

---

## 6. Teilung der Kreuzvalidierung

- **Vergleichsregel:** Teilung nach Zeilen und nach Episoden werden nur mit Gewinnen und Schwellen aus derselben Teilung verglichen (R2 gegen R3). Gemischte Vergleiche sind ungültig, etwa ein Zeilengewinn gegen ein Episoden-δ oder ein Episodengewinn gegen ein Zeilen-δ (R1).
- **Die v2-Begründung trägt nicht:** Spec v2, Anhang A, stützt „Zeilen“ auf Seed 0 (2/5 gegen 0/5 Fehlöffnungen unter `global`). Das war ein einzelner Seed und ein δ je Erklärung. Für eine Serienkalibrierung sagt das nichts.
- **Gültigkeit:** Die Grenze in §4 braucht keine Unabhängigkeit der Zeilen, nur austauschbare Ströme. Beide Teilungen sind dafür gültig.
- **Worin sie sich unterscheiden:**
  - in der Trennschärfe;
  - in der Bedeutung des Gewinns: Bei Episodenteilung heißt er Vorhersage auf ungesehenen Episoden und Karten.
- **Befund:** Die Daten in B4 unterscheiden die Teilungen nicht.
- **Gewählt (E2):**
  - Bestätigend wird nach Zeilen geteilt, nach dem Grundsatz „eine Änderung zur Zeit“.
  - Die Teilung nach Episoden läuft als vorab festgelegte Nebenauswertung auf denselben Strömen mit eigenem δ₁ nach §3.7. Sie wird nur beschrieben.
  - Alternative: Episoden bestätigend. Die Wahl fällt vor der Bestätigung.
- **Blockpermutationen sind nicht Teil von v3.** Sie wären eine eigene Variante und bräuchten:
  - eine eigene Nullhypothese: Die Verschiebung ist bei gegebenem z, gegebener Aktion und gegebenen übrigen Merkmalen unabhängig vom Kandidaten;
  - eine Permutationseinheit (Episode oder Karte);
  - einen Umgang mit z, das bei Invarianz < 1 noch etwas Farbe enthält;
  - einen Umgang mit Aktion und übrigen Merkmalen: Farben schließen einander je Zelle aus;
  - einen Umgang mit verschieden langen Episoden.

---

## 7. Vergleichssysteme

### 7.1 S1: Serienstatistik auf dem standardisierten Unterschied z (E9)

**Je Runde E**, auf dem Puffer B(E) mit n Schritten und der Überraschung S je Schritt:
- Für jeden Kandidaten c außerhalb der bekannten Merkmale K gilt k₁ = Zahl der Schritte mit F_c = 1 und k₀ = n − k₁.
- Der standardisierte Unterschied ist

  z_c = (Mittel von S bei F_c = 1 − Mittel von S bei F_c = 0) / sd_c,  mit sd_c² = n² σ² / (k₁ k₀ (n − 1)).

  - σ² ist die Varianz von S im Puffer (ddof = 0).
  - sd_c ist genau die Standardabweichung dieses Unterschieds unter zufälliger Vertauschung der Zeilen. Permutationen braucht es nicht.
- Kandidaten mit k₁ = 0 oder k₀ = 0 bekommen kein z. Bei σ = 0 ist z_c = 0.
- Rundenstatistik: Z_j(E) = max_c z_c. Bei Gleichstand gilt der kleinste Kandidatenindex.

**Zeitpunkte:**
- Erklärt wird wie in v2 nach dem CUSUM-Alarm bei jedem Prüfpunkt, ohne Mindestfüllung des Puffers. Für S1 ist 𝓔 deshalb {10, 20, …, 400}.
- E10 betrifft nur M3.
- Die CUSUM-Schwelle ist ebenfalls das Maximum derselben 20 Ströme. Deshalb wird auch hier erzwungen erklärt.

**Schwelle:** T_j = max_E Z_j(E) mit Basis K₀ = Übungs-Ontologie von S1. Daraus z₁ = max_j T_j.

**Einsatz:**
- Geöffnet wird der Kandidat mit dem größten z, genau dann, wenn z > z₁ (strikt).
- Höchstens ein Merkmal je Runde (E8), insgesamt höchstens 3 wie in v2.
- Kalibriert und entschieden wird auf derselben Größe.
- Die Kandidatenkorrektur steckt im Maximum über die Kandidaten. Die Serienkalibrierung deckt damit Kandidaten und Runden zugleich ab.

**Warum nicht der Holm-adjustierte p-Wert** (ursprünglicher Entwurf, verworfen mit E9):
- In D2 lag der kleinste adjustierte Permutations-p-Wert in 11–20 von 20 Null-Strömen auf der Untergrenze m/(n_perm + 1).
- Die Schwelle α₁ war damit unerreichbar, und S1 öffnete nie, auch unter `red` nicht (0/15).
- Die z-Werte auf den Null-Strömen erreichen 6,2–9,7. Die zeilenweisen Permutationstests von S1 sind unter der Nullhypothese also stark zu optimistisch. Nur eine Größe ohne Untergrenze lässt sich über die Serie sinnvoll kalibrieren.
- **Entwicklungsbefund D2** auf 15 verbrauchten Seeds: `red` 14/15 richtig, `global`, `walls` und `none` je 0 (`farbversuch/results/entwicklung_v3/`).

**Unverändert:**
- Das Vor-Öffnen von S1, also seine Übungs-Ontologie, bleibt beim v2-Permutationstest mit Holm (`n_perm` 1000).
- **S1-A** (E5) läuft mit der unkalibrierten v2-Regel mit und wird nur beschreibend berichtet, ausdrücklich als unkalibriert gekennzeichnet. Keine Vorhersage hängt an S1-A.

**Grenze:** Für die erste Öffnung von S1 gilt dieselbe Grenze und dieselbe Reichweite wie in §4. T ist eine feste Funktion des Stroms, und Kalibrierung und Einsatz nutzen dieselbe Größe.

### 7.2 M3-A: Kosten der vollen Serienkalibrierung

**Gleiches Verfahren wie §3,** mit 1192 Kandidaten.

**Gemessen in v2:**
- eine Erklärrunde: Median 72,6 s, über 418 Runden im Hauptlauf;
- δ aus 20 Endpuffern: ≈ 21 min je Seed (Seed 400).

**Serie:** Mit E10(b) sind es 20 Ströme × 26–31 Runden bei vollem Puffer. D3 hat 58–74 s je Runde gemessen; Strom 0 von Seed 400 mit 28 Runden brauchte 29,7 min. Das ergibt etwa 10 CPU-h je Seed. Unter (a) wären es etwa 13 CPU-h.
- Bestätigung (5 Seeds): ≈ 50 CPU-h, ≈ 12–13 h auf 4 Kernen. Nach E4 läuft M3-A dort nicht mit.
- Hauptlauf (10 Seeds): ≈ 100 CPU-h, ≈ 25–26 h auf 4 Kernen.
- Dazu kommt der Einsatz von M3-A wie in v2, ≈ 1 CPU-h je Seed.

**Keine Abkürzung über ein gröberes Raster:** Kalibrierung alle 50 Episoden bei Erklären alle 10 im Einsatz hätte weniger Runden, ein kleineres Maximum und damit ein zu kleines δ.

**Gültig, aber mit Nachteilen:**
- gleiches Intervall in Kalibrierung und Einsatz: ändert die Latenzauflösung von M3-A und verzerrt die Latenz in P4;
- weniger Kalibrierströme: anderes Fehlerniveau als bei M3-B, unfairer Vergleich;
- schnelleres Anpassen, etwa durch Warmstart: Technik mit eigenem Prüfaufwand, Numerik ändert sich.

**Zusatzöffnungen:** Für M3-A ist Z2 nicht machbar (§5.2). Mit Z3 werden M3-A und M3-B gleich behandelt.

**Gewählt (E4): M3-A nur im Hauptlauf.**
- Die Bestätigung 520–524 läuft ohne M3-A, denn ihre Regel betrifft nur M3-B.
- Der Hauptlauf 600–609 läuft mit M3-A und voller Serienkalibrierung; P4 bleibt.
- D3 (§9.0) misst die Kosten vorher an einem verbrauchten Seed.

**Verworfene Alternative:** M3-A weglassen hätte die **Forschungsfrage eingeengt**.
- v3 fragt dann nicht mehr, ob die Kandidatenmenge (6 Zielzellen-Merkmale gegen 1192 Rohbit×Aktion) für das Wiederöffnen zählt.
- **P4 entfällt ausdrücklich.** P1–P3 und P5 bleiben.
- Das geschieht nur auf Entscheidung des Nutzers.

---

## 8. Vorhersagen v3 (Entwurf, vor dem Hauptlauf einzufrieren)

Hauptlauf: Seeds 600–609. Die Schwellen sind wie in v2, damit beide vergleichbar sind.

**Bewertung bei Z3 (erste Öffnung je Strom):**
- **Treffer unter `red`:** Die erste Öffnung des Stroms ist das richtige Merkmal (wie v2 §6) und liegt bei E > 100.
  - Eine erste Öffnung vor dem Wechsel ist kein Treffer.
  - **M3 und S1 werden mit derselben Definition bewertet** (E8). S1 kann in v2 bis zu 3 Merkmale in einer Runde öffnen. „Treffer, wenn das richtige Merkmal unter den Öffnungen der ersten Runde ist“ wäre für S1 nachsichtiger als für M3 und würde P5 verzerren. Gewählt ist die erste der beiden Varianten:
    - **S1 öffnet höchstens ein Merkmal je Runde (gewählt, E8):** mit E9 das Merkmal mit dem größten z (§7.1). „Erste Öffnung“ ist dann für beide Verfahren ein einzelnes Merkmal. §4 bleibt gültig.
    - *Verworfen:* **S1 wie v2.** Treffer nur, wenn das richtige Merkmal in der ersten Runde in Holm-Reihenfolge vorn liegt. Die übrigen Merkmale dieser Runde zählen als falsche erste Öffnungen.
  - Treffer, erste Öffnung und Latenz bestimmt für alle Systeme **eine einzige Auswertungsfunktion** (Test T8).
- **Falsche erste Öffnung:**
  - in `none`, `global` und `walls` jede erste Öffnung eines Farbmerkmals;
  - in `red` jede erste Öffnung, die kein Treffer ist.
- **Latenz:** E der ersten Öffnung − 100 bei Treffer, sonst zensiert bei 300.

**Vorhersagen:**
- **P1:** wie v2. Seeds mit gescheiterter Prämisse werden berichtet, nicht ersetzt, und zählen gegen M3-B.
- **P2:** M3-B trifft unter `red` in ≥ 9/10 Seeds.
- **P3:** M3-B öffnet unter `global` in ≥ 9/10 Seeds nichts. Das ist empirisch und nicht durch §4 gedeckt.
- **P4** (nur mit M3-A): M3-A ist unter `red` langsamer oder hat über alle Bedingungen mehr falsche erste Öffnungen als M3-B. Der Abstand wird beziffert.
- **P5:** M3-B trifft unter `red` mindestens so oft wie S1-B, mit S1-B nach §7.1.
- **Abbruchkriterium:** M3-B trifft unter `red` in < 5/10 Seeds, oder es öffnet unter `global` in > 3/10 Seeds.

**Pflichtangaben, nur beschreibend:**
- Öffnungen unter `none` (Erwartung nach §4: höchstens 1/21 je Seed) und unter `walls`;
- Zusatzöffnungen;
- δ₁, z₁, Gewinn/δ₁ jeder M3-Öffnung und z/z₁ jeder S1-Öffnung;
- die Nebenauswertung mit Teilung nach Episoden;
- Latenzen und Kosten.

---

## 9. Plan der frischen Prüfungen

### 9.0 Entwicklung (keine Evidenz)
- Umsetzung testgetrieben (§10). Läufe mit voller Konfiguration nur auf verbrauchten Seeds.
- Entwicklungsprüfungen, vom Nutzer freigegeben (E6). Ihr Ergebnis darf die Varianten noch ändern, weil es Entwicklungsdaten sind:
  - **D1:** δ₁ nach §3 mit allen zulässigen Zeitpunkten auf 400–409 und 510–514. Nachspielung aller vier Bedingungen, auch `walls` und `none`, für M3-B mit beiden Teilungen. Schließt U1, U2 und U5 als Entwicklungsbefund.
  - **D2:** S1-B nach §7.1 auf denselben Seeds.
  - **D3:** Kosten von M3-A an einem Strom messen, ≈ 45 min (nötig für E4).

### 9.1 Nachweis der Nichtnutzung, vor jeder Stufe neu
**Geprüft wird:**
- Ergebnisordner und Git-Historie auf Ergebnisdateien und Laufargumente mit diesen Seeds;
- alle Befehlsprotokolle dieser Sitzung und ihrer Teilagenten;
- der Arbeitsordner.

Das Ergebnis kommt ins Protokoll.

**Stand 06.10.2026:**
- 520–524 und 600–609 kommen nur als vorgeschlagene Nummern in Texten vor;
- kein Lauf, keine Ergebnisdatei, kein Commit.

**Nicht prüfbar** sind Rechnungen außerhalb dieser Sitzung.

### 9.2 Bestätigung auf 520–524

**Systeme:** M3-B, S1-B und S1-A, ohne M3-A (E4).

**Vorher festgelegt und als Commit abgelegt:**
- Konfiguration und Varianten E2–E5 und E8;
- Code-Stand;
- diese Regel.

Nach dem Lauf wird nichts mehr gewählt.

**Regel wie v2 D1:** Je Seed müssen alle drei Bedingungen gleichzeitig gelten:
1. Prämisse erfüllt;
2. M3-B öffnet unter `none` und unter `global` nichts;
3. die erste Öffnung von M3-B unter `red` ist „Farbe 0“ nach dem Wechsel.

**Bestätigt** heißt: mindestens 4 von 5 Seeds.

**Nicht bestätigt:**
- Abbruch und Bericht.
- Ein neuer Versuch braucht einen neuen Entwicklungsschritt und frische Seeds (530–534 usw.) mit eigenem Nichtnutzungsnachweis.

**Bestätigt:** Der Nutzer entscheidet über Einfrieren und Hauptlauf.

### 9.3 Einfrieren
- Wie v2: `frozen_config.json`, `freeze.sha256`, Umgebung, Fingerabdruck.
- Der v2-Stand bleibt über ein Git-Tag reproduzierbar.

### 9.4 Hauptlauf auf 600–609
- P1–P5 und Abbruchkriterium nach §8. Urteile gibt es nur für genau diese Seeds.
- Alles danach ist nachträgliche Erkundung.
- Bestätigung und Hauptlauf laufen je auf einer Maschine.

---

## 10. Tests (testgetrieben)

Alle v2-Tests bleiben. Neu:

- **T1 Zeitpunkte:**
  - 𝓔 enthält genau die Prüfpunkte mit ≥ `notice_window` Schritten, auch solche vor `switch_episode`.
  - Eine Änderung der Meldeschwelle (auch +∞) oder von `switch_episode` ändert T nicht.
- **T2 Puffergleichheit:** Für dieselbe Folge von Trajektorien ist B(E) der Kalibrierung bitgleich mit dem Monitorpuffer bei Prüfpunkt E.
- **T3 Brücke zum Einsatz:**
  - Ein Monitor mit erzwungenem Bemerken öffnet auf einem Strom genau dann etwas, wenn auf demselben Strom G(E) > δ₁ für ein E ≥ Bemerkzeitpunkt gilt.
  - Kalibrierung und Einsatz nutzen denselben Teilungsschlüssel je E.
- **T4 Schwelle:**
  - δ₁ = Maximum der T_j. Die strikte Regel „>“ gilt; δ₁ = 0 ist möglich.
  - Ein Kandidat mit Mittel = δ₁ öffnet nicht.
- **T5 S1 (z-Statistik):**
  - sd_c stimmt mit der Standardabweichung des Unterschieds über viele zufällige Vertauschungen überein (Monte-Carlo-Vergleich).
  - Kandidaten mit k₁ = 0 oder k₀ = 0 bekommen kein z.
  - Bei Gleichstand öffnet der kleinste Index.
  - z = z₁ öffnet nicht (strikt).
  - Bekannte Merkmale werden nicht getestet.
  - Je Runde höchstens eine Öffnung.
- **T6 Kalibrierung austauschbarer Ströme** (synthetisch, `slow`): Mit 21 austauschbaren synthetischen Strömen liegt die Überschreitungsrate über viele Wiederholungen bei ≤ 1/21 (Binomialtoleranz).
- **T7 Pflichtprüfung:** `n_null_episodes != n_deploy_episodes` ergibt einen Fehler.
- **T8 Bewertung Z3:**
  - Treffer, falsche erste Öffnung, Latenz und Abbruch werden aus der ersten Öffnung bestimmt.
  - Zusatzöffnungen ändern kein Urteil, werden aber berichtet.
  - M3 und S1 laufen durch dieselbe Auswertungsfunktion. Ein S1-Ergebnis mit mehreren Öffnungen in der ersten Runde wird nach E8 bewertet, nicht nachsichtiger als M3.
- **T9 Seeds:**
  - Urteile gibt es nur für 600–609.
  - Die Bestätigung nimmt nur nicht verbrauchte Seeds ab 520.
  - Verbrauchte Seeds werden abgewiesen.
- **T10 Rückwärtsgleichheit:** Mit ausgeschalteter Serienkalibrierung sind die Ergebnisse auf einem Mini-Seed bitgleich zu v2.
- **T11 (nur Z2):**
  - Die δ_K-Tabelle deckt alle erreichbaren Basen ab und entsteht vor dem Einsatz.
  - Die Rechenfunktion bekommt keine Einsatzdaten.

---

## 11. Kosten

| Teil | je Seed | Grundlage |
|---|---|---|
| M3-B, Serie, eine Teilung | ≈ 20 × 38 × 0,42 s ≈ 5 min | v2: Median 0,41 s je Runde |
| M3-B, Nebenauswertung nach Episoden | ≈ 5 min | wie oben |
| M3-B, Z2-Tabelle (15 weitere Basen) | ≈ 80 min | wie oben |
| S1-B, Serie mit der z-Statistik | wenige Sekunden | geschlossene Formel, keine Permutationen |
| S1-A, Serie | nicht sinnvoll (§7.1) | |
| M3-A, Serie | ≈ 10 CPU-h (E10(b)) | §7.2, D3 |
| Rest wie v2 ohne M3-A (Phase 1, Einsatz) | ≈ 3 min | v2, Seed 400: Phase 1 ohne M3-A ≈ 110 s, Einsatz ohne M3-A ≈ 30 s |
| Rest wie v2 mit M3-A | ≈ 1,5 CPU-h | v2: Seed 400 insgesamt 5265 s |

**Gesamt auf 4 Kernen, nach E4 und E10(b):** Bestätigung ohne M3-A etwa 40 min, Hauptlauf mit M3-A etwa 30 h.

**Zum Vergleich:**
- **ohne M3-A** (≈ 20 min je Seed): Bestätigung etwa 40 min, Hauptlauf etwa 1 h.
- **mit M3-A** (≈ 11,5 CPU-h je Seed unter E10(b), ≈ 14,5 unter (a)): Bestätigung etwa 15 h, Hauptlauf etwa 30 h.
  - Das setzt voraus, dass der Treiber über Kalibrierströme parallelisiert. Wird wie in v2 nur über Seeds und Bedingungen parallelisiert, dauert ein Lauf mit 5 Seeds auf 4 Kernen etwa doppelt so lang.

Dazu kommen Umsetzung mit Tests, Entwicklungsprüfungen (D1 ≈ 1–1,5 h auf 4 Kernen für 15 Seeds), Einfrieren und Bericht.

---

## 12. Entscheidungen (Nutzer, 07.10.2026)

| | Frage | Entscheidung |
|---|---|---|
| E1 | Serienkalibrierung als Kern (§3, §7.1) | angenommen |
| E2 | Teilung | bestätigend nach Zeilen; Episoden als beschreibende Nebenauswertung mit eigener Schwelle |
| E3 | Zusatzöffnungen | Z3: Nur die erste Öffnung zählt, weitere werden beschrieben |
| E4 | M3-A | nur im Hauptlauf 600–609, volle Serienkalibrierung, P4 bleibt; Bestätigung ohne M3-A |
| E5 | S1-A | unkalibrierte v2-Regel, nur beschreibend |
| E6 | Entwicklungsprüfungen D1–D3 | freigegeben |
| E7 | Seeds | Bestätigung 520–524, Hauptlauf 600–609 |
| E8 | Trefferdefinition S1 | S1 öffnet höchstens ein Merkmal je Runde |
| E9 | Statistik für S1 | z-Statistik, über die Serie kalibriert, statt Holm-p (Nutzer, 10.10.2026; Entwicklungsbefund D2) |
| E10 | Kleine Puffer | **(b) erst bei vollem Puffer erklären, Teilung nach Zeilen**. Gewählt am 08.10.2026 nach der vorab festgelegten Auswahlregel (PROTOKOLL, Commit `1c02884`), auf Auftrag des Nutzers. Gilt gleich für M3-A und M3-B (§3.3). Begründung und Daten: `farbversuch/results/entwicklung_v3/e10/` |

---

## 13. Nicht Teil von v3

- Blockpermutationen (§6);
- ein δ relativ zur Stärke der bemerkten Änderung;
- Umlernen von Routine oder Encoder;
- andere Welten;
- Kalibrierung unter höherem Rauschen, also eigene `global`-ähnliche Null-Ströme. Das wäre eine eigene Variante mit eigener Nullhypothese.
- **Jederzeit gültige Tests über Martingale (Doob- bzw. Ville-Maximalungleichung, e-Prozesse).**
  - Vorteil: Sie könnten eine Überschreitung irgendwann in der Serie auch unter `global` begrenzen. Dann hinge die Grenze nicht an der Austauschbarkeit mit den Null-Strömen.
  - Voraussetzung: ein Prozess, der unter jeder Verteilung der Nullhypothese ein Supermartingal ist. Die überlappenden Kreuzvalidierungs-Gewinne von M3 sind das nicht.
  - Ein fortlaufender Likelihood-Quotient gegen das Vorwärtsmodell wäre es nur, wenn das Vorwärtsmodell die wahre bedingte Verteilung träfe. Das tut es hier nicht.
  - Das wäre eine eigene Version mit eigener Nullhypothese. Die Ungleichung selbst ist Standard (Mathlib `MeasureTheory.maximal_ineq`). Die Fundstelle in `openai/math` (`martingale_exponential_maximal`) ist eine Anwendung davon.
