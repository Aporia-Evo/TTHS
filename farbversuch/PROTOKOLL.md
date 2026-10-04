# Protokoll der Pilot-Änderungen (Spec v2 §8.1)

Jede Änderung an `farbversuch/pilot_config.json` mit Grund und den Messwerten davor. Erlaubt sind nach Spec v2 §8.1 nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße und Prüfintervall.

Maschine aller Läufe: Cloud-Container, 4 Kerne, Python 3.11.15, numpy 2.4.6, BLAS-Threads 1.

## 1. `wd` 0,001 → 0,01 (04.10.2026)

**Ausgangslauf:** Pilot Seed 0 mit den Standardwerten (`Config()`), Start 07:15:34, Ende nach 83 s. Code-Stand 352092c. Die Prämisse ist nicht erfüllt, deshalb gab es keine Kalibrierung und keine Bedingungen (Entscheidung D2).

| Messgröße | Wert | Grenze | erfüllt |
|---|---|---|---|
| Farbinvarianz (P1) | 0,9258 | ≥ 0,95 | nein |
| Vorwärtsmodell / Häufigkeitsmodell (P1) | 0,5831 / 1,5912 | kleiner | ja |
| Restanteil (P1b) | 0,1117 | ≤ 0,15 | ja |
| Verschiebung (P1b) | 0,1574 | ≤ 0,25 | ja |

**Grund:** P1 scheitert allein an der Farbinvarianz. Ein stärkerer Weight Decay der Routine drückt die Gewichte der im Training bedeutungslosen Farbbits gegen null.

**Vorprüfung:** explorativ, Seed 0, außerhalb des Ergebnisordners. Gerechnet wurden `train_phase1` und `premise_checks` mit je einer geänderten Größe; alles andere ist Standard.

| Variante | Farbinvarianz | Restanteil | Verschiebung | Vorwärts / Häufigkeit | Treffer auf Lehrerdaten | Prämisse |
|---|---|---|---|---|---|---|
| wd 0,003 | 0,9319 | 0,0817 | 0,1508 | 0,5803 / 1,5729 | 0,8991 | nein |
| wd 0,01 | 0,9797 | −0,0364 | 0,1035 | 0,6182 / 1,3688 | 0,9128 | ja |
| wd 0,03 | 0,9787 | 0,1189 | 0,0556 | 0,8221 / 1,3956 | 0,7291 | ja |
| epochs 2000 | 0,8833 | 0,2280 | 0,2461 | 0,5505 / 1,5979 | 0,9475 | nein |

**Entscheidung:** `wd` = 0,01, vom Nutzer am 04.10.2026 freigegeben.
- **Gewählt:** P1 und P1b sind deutlich erfüllt, und die Routine folgt dem Lehrer fast unverändert.
- **Verworfen:** wd 0,03 schließt die Farbe ebenfalls, verschlechtert aber die Routine stark. Mehr Epochen verschlechtern die Invarianz.
- **Kopplung:** `wd` wirkt nur auf das Training der Routine. Es fließt weder in das Erklären noch in die P1b-Messung.

**Altes Ergebnis:** aus `farbversuch/results/pilot` entfernt, damit die CLI mit der neuen Konfiguration startet. Die Werte stehen oben.

**Ergebnis des nächsten Pilots:** folgt.
