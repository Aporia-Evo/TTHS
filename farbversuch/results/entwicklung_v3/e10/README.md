# E10: kleine Puffer, Nachrechnung auf verbrauchten Seeds (08.10.2026)

**Entwicklungsdaten auf den verbrauchten Seeds 400–409 und 510–514, keine Evidenz.**
- Auftrag des Nutzers vom 08.10.2026.
- Die Varianten und die Auswahlregel standen vor dem Rechnen fest: PROTOKOLL, Abschnitt „E10: Auswahlregel“, Commit `1c02884`.
- Es kamen keine weiteren Varianten dazu, und es wurden keine frischen Seeds benutzt.
- Code und Freeze von v2 sind unverändert.

## Inhalt

- `e10.py.txt`: das Skript, SHA-256 `f8a7cf0f972a…`. Aufruf: `python e10.py SEED`.
- `summarize_e10.py.txt`: Auswertung und mechanische Anwendung der Auswahlregel.
- `e10_SEED.json`: Rohdaten je Seed:
  - Schwellen;
  - Pufferfüllzeiten;
  - für jede Bedingung und Kombination aus Variante und Teilung die Erklärrunden mit n, Schwelle, bestem Gewinn und Abstand, sowie die Öffnungen;
  - Verlauf aller Kandidaten mit Basis = Übungs-Ontologie bei jedem Prüfpunkt mit n ≥ 500.
- `summary_e10.json` und `summary_e10.txt`: die Auswertung.
- `logs/`: Fortschrittsprotokolle.
- **Lauf:** 08.10.2026, 07:41–08:01, 4 Prozesse gleichzeitig, je Seed etwa 5 min.

## Varianten

Sie gelten in Kalibrierung und Einsatz gleich. n ist die Zahl der Pufferschritte im Prüfpunkt, das Bemerken ist unverändert.

| Variante | Erklären bei | Schwelle | Öffnen, wenn alle Teilungen > 0 und |
|---|---|---|---|
| (a) Referenz | n ≥ 500 | δ₁ = Maximum von G | Mittel > δ₁ |
| (b) | n = 2000 (voller Puffer) | δ₁ = Maximum von G über diese Runden | Mittel > δ₁ |
| (c) | n ≥ 500 | κ₁ = Maximum von n · G | Mittel > κ₁ / n |

**Woher die Daten stammen:**
- Die Null-Serien kommen aus D1 (`../d1_SEED.json`), die Einsatzströme wurden neu nachgespielt.
- Nachbau geprüft: Auf allen 15 Seeds und in allen vier Bedingungen baut v2 exakt nach, und (a) liefert exakt die D1-Öffnungen.

## Ergebnis

Bewertet nach Spec v3 §8: Die erste Öffnung entscheidet.

| Kombination | `red` richtig | Latenz `red` (Mittel) | kleinster Abstand `red` (Seed) | `global` | `walls` | `none` | Zusatz | größter Abstand `global` |
|---|---|---|---|---|---|---|---|---|
| v2 (Referenz) | 15/15 | 44,0 | – (δ = 0 bei 6 Seeds) | 5 | 2 | 0 | 9 | 2,14 |
| (a) Zeilen | 15/15 | 45,3 | 1,09 (408) | 1 (510) | 0 | 0 | 0 | 1,09 |
| (a) Episoden | 15/15 | 54,0 | 1,06 (513) | 0 | 0 | 0 | 0 | 0,58 |
| **(b) Zeilen** | **15/15** | **46,0** | **1,93 (513)** | **1 (510)** | **0** | **0** | **0** | **1,70** |
| (b) Episoden | 15/15 | 48,0 | 1,19 (513) | 0 | 0 | 0 | 0 | 0,88 |
| (c) Zeilen | 15/15 | 44,0 | 1,45 (402) | 1 (510) | 0 | 0 | 0 | 1,70 |
| (c) Episoden | 15/15 | 48,0 | 1,19 (513) | 0 | 0 | 0 | 0 | 0,72 |

Abstand heißt: Gewinn geteilt durch die Schwelle in der Runde. Die Bemerklatenz unter `red` liegt bei 10–100, im Mittel 42,7.

**Pufferfüllzeit**, gemessen als Episode des ersten Prüfpunkts:

| Strom | ab n ≥ 500 | voller Puffer |
|---|---|---|
| Null-Ströme | E = 20–50 | E = 100–150 (Median 130) |
| Einsatz, alle Bedingungen | E = 30–40 | E = 110–140 (Median 120) |

**Zulässige Null-Runden je Strom:** (a) 36–39, im Mittel 37,4; (b) 26–31, im Mittel 28,3.

**Erste Öffnung unter `red` gegenüber dem Bemerken:**
- Wie viele Seeds öffnen später als sie bemerken: (a) Zeilen 4, (b) Zeilen 5, (c) Zeilen 2; bei Episoden 6–8. Die Verzögerung beträgt jeweils 10 Episoden, bei Episoden bis 50.
- Die Latenz wird also überwiegend vom Bemerken bestimmt, nicht von der Erklärschwelle.

**Verlauf des richtigen Kandidaten** („Farbe 0“ unter `red`, Basis = Übungs-Ontologie, Teilung nach Zeilen):
- Vor dem Wechsel (E ≤ 100) liegt sein Gewinn bei −0,010 bis 0,0033.
- Nach dem Wechsel ist er erstmals in allen Teilungen positiv bei E = 110–150. Bei E = 150 liegt er bei 0,006–0,023, bei E = 200 bei 0,027–0,062, die Spitzen bei 0,057–0,090.
- Unter (b) Zeilen liegt er erstmals über der Schwelle bei E = 120–150, ohne Rücksicht auf das Bemerken. Bei 9 von 15 Seeds ist das vor dem tatsächlichen Bemerken.
- In `none`, `global` und `walls` bleibt er bei höchstens 0,0033.
- Einzelwerte je Prüfpunkt: `e10_SEED.json`, Schlüssel `deploy.<Bedingung>.trajectory`.

**Seed 510 unter `global`, in allen Zeilen-Varianten:**
- Der falsche Gewinn von „Farbe 0“ (0,0033) steckt schon in den Daten vor dem Wechsel. Bis Episode 100 sind alle Bedingungen gleich.
- Die Öffnung bei E = 110 ist damit ein null-artiger Ausreißer des Einsatzstroms. Genau dieses Ereignis begrenzt §4 mit höchstens 1/21 je Strom; über 15 Seeds sind etwa 0,7 solcher Fälle zu erwarten.
- Bei Teilung nach Episoden tritt er nicht auf.

## Auswahl nach der vorab festgelegten Regel

1. **Zulässig sind alle 6 Kombinationen:** `red` jeweils 15/15, `global` ≤ 1, `walls` 0, `none` 0.
2. **Größter kleinster Abstand unter `red`:** (b) Zeilen mit 1,93. Die 10-%-Grenze liegt bei 1,73, keine andere Kombination liegt innerhalb davon. Die nächstbesten sind (c) Zeilen mit 1,45, dann (b) und (c) Episoden mit je 1,19.
3. **Gleichstandsregeln:** nicht nötig.

**Gewählt: E10(b) mit Teilung nach Zeilen.** Damit bleibt E2 unverändert.

**Was (b) kostet bzw. nicht leistet**, festgehalten zur Transparenz:
- Die Fehlöffnung bei Seed 510 unter `global` bleibt, mit einem Abstand von 1,70.
- Die mittlere Latenz unter `red` steigt um 0,7 gegenüber (a) Zeilen und um 2,0 gegenüber (c) Zeilen.
- **Nebenwirkung bei den Kosten:** Weniger Runden senken die Serienkalibrierung von M3-A von etwa 13 auf etwa 10 CPU-Stunden je Seed (D3: Strom 0 mit 28 vollen Runden in 29,7 min).
