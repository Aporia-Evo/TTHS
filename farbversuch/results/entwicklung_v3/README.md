# Entwicklungsprüfungen D1–D3 für v3 (07.10.2026)

**Entwicklungsdaten auf verbrauchten Seeds (400–409, 510–514), keine Evidenz.** Freigegeben durch Entscheidung E6 des Nutzers (Spec v3, §9.0 und §12). Code, Konfiguration und `freeze.sha256` von v2 sind unverändert; `freeze verify`: OK.

## Inhalt

- `dev3.py.txt`: das Skript, SHA-256 `bea52cdd7f92…`.
  - Als `.txt` abgelegt, weil jede `*.py` zum v2-Freeze gehört.
  - Es importiert den eingefrorenen Code und ändert nichts am Repo.
  - Aufruf: `python dev3.py d1 SEED` bzw. `python dev3.py d3 SEED`, mit einem BLAS-Thread.
- `summarize.py.txt`: die Auswertung. Sie schreibt `summary.json`.
- `d1_SEED.json`: D1 (M3-B) und D2 (S1-B) je Seed.
- `d3_400.json`: D3, die Kosten von M3-A an Null-Strom 0 von Seed 400.
- `logs/`: Fortschrittsprotokolle.
- **Lauf:** 07.10.2026, 12:49–14:26, 4 Prozesse gleichzeitig, je Seed etwa 19–20 min. Vorher gab es einen Kurzlauf zum Testen (2 Null-Ströme, nur `global`).

## Was gerechnet wurde

**Prüfgerüst:**
- Es arbeitet Schritt für Schritt wie der Monitor: echter `RingBuffer`, Überraschung je Schritt, CUSUM je Schritt, gleiche Zufallsschlüssel je Prüfpunkt.
- Phase 1 wird für M3-B und S1-B deterministisch neu gerechnet. Geprüft wird die Gleichheit mit dem v2-Ergebnis (Schlüssel `check`).

**Null-Serien (Spec v3 §3, §7.1)** auf allen 20 Null-Strömen, erzwungen und unabhängig von Alarm und Wechsel:
- M3-B bei jedem Prüfpunkt mit ≥ 500 Pufferschritten, Teilung nach Zeilen und nach Episoden. Daraus ergeben sich `delta1_row` und `delta1_ep`.
- S1-B bei jedem Prüfpunkt mit 10.000 Permutationen, zwei Statistiken:
  - kleinster Holm-adjustierter p-Wert (`alpha1`);
  - stetige Variante: größter standardisierter Unterschied z über die Kandidaten (`z1`).

**Nachspielung aller vier Bedingungen.** Bemerkt wird selbst gerechnet und nicht aus v2 übernommen. Regeln:

| Regel | Bedeutung |
|---|---|
| `M3_v2` | v2-Regel (δ aus v2); muss v2 exakt nachbauen |
| `M3_v3_row` | δ₁ nach Zeilen, Z3 |
| `M3_v3_ep` | δ₁ nach Episoden, Z3 |
| `S1_v2` | v2-Regel; muss v2 exakt nachbauen |
| `S1_v3` | Holm-p < α₁, höchstens eine Öffnung je Runde |
| `S1_v3z` | z > z₁, höchstens eine Öffnung je Runde |

**D3:** M3-A an einem Null-Strom, alle 38 zulässigen Runden, mit Zeitmessung.

## Ergebnis

**Nachbau:** Auf allen 15 Seeds und in allen vier Bedingungen exakt gleich wie v2: Bemerkzeitpunkte und Öffnungen von M3-B und S1-B, bei M3-B mit Gewinn. Die Rundengewinne ab E = 110 stimmen exakt mit `../nachtrag_diagnose/` überein.

**Bewertung nach Spec v3 §8** (Z3: die erste Öffnung entscheidet):

| Regel | `red` richtig, 400–409 / 510–514 | Latenz | `global` | `walls` | `none` | Zusatzöffnungen |
|---|---|---|---|---|---|---|
| M3_v2 | 10/10, 5/5 | 49 / 34 | 4 + 1 | 1 + 1 | 0 | 9 |
| M3_v3_row | 10/10, 5/5 | 51 / 34 | 0 + 1 (Seed 510) | 0 | 0 | 0 |
| M3_v3_ep | 10/10, 5/5 | 63 / 36 | 0 | 0 | 0 | 0 |
| S1_v2 | 9/10, 5/5 | 47 / 54 | 7 + 3 | 0 + 1 | 0 | 14 |
| S1_v3 (Holm-p) | 0/10, 0/5 | – | 0 | 0 | 0 | 0 |
| S1_v3z | 9/10, 5/5 | 48 / 56 | 0 | 0 | 0 | 2 |

**Befunde:**
- **Frühe, kleine Puffer bestimmen δ₁.**
  - δ₁ (Zeilen) liegt bei 0,0027–0,0138, im Spike waren es 0,0023–0,0037 ab E = 110.
  - Bei 11 von 15 Seeds stammt es aus einer Runde bei E = 30–90 mit 500–1500 Pufferschritten.
  - Die knappste richtige `red`-Öffnung liegt beim 1,09-Fachen von δ₁ (Zeilen, Seed 408) bzw. beim 1,06-Fachen (Episoden, Seed 513).
- **Seed 510:** Nach Zeilen geteilt öffnet M3-B unter `global` bei E = 110 „Farbe 0“, mit dem 1,09-Fachen von δ₁. Nach Episoden geteilt geschieht das nicht.
- **S1 auf Holm-p ist unbrauchbar.**
  - In 11–20 von 20 Null-Strömen liegt der kleinste adjustierte p-Wert auf der Untergrenze der Permutationen (m/10.001).
  - α₁ ist damit unerreichbar, S1 öffnet nie.
  - Die stetige z-Variante hat dieses Problem nicht.
  - Die Null-Werte von z erreichen 6,2–9,7. Die zeilenweisen Permutationstests von S1 sind unter der Nullhypothese also stark zu optimistisch.
- **D3:** 38 Runden in 39 min, 37–74 s je Runde. Für 20 Ströme sind das etwa 13 CPU-Stunden je Seed.
