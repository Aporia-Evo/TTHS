# Farbversuch: Abschlussvermerk (10.10.2026)

**Status: abgeschlossen auf Entscheidung des Nutzers vom 10.10.2026.**
- Das vorregistrierte Ergebnis ist das von v2.
- v3 ist vollständig spezifiziert (alle Entscheidungen E1–E10), aber nicht umgesetzt und nicht gelaufen. v3 ist zurückgestellt, nicht verworfen.

**Grund:** Das Fernziel des Nutzers ist ein generalisierendes System ähnlich einem Sprachmodell. Der Mechanismus des Farbversuchs überträgt sich darauf nicht direkt:
- Er braucht von Hand vorgegebene Kandidaten-Merkmale.
- „Wiederöffnen“ erweitert nur ein Erklärmodell. Die Routine selbst lernt nicht um.

Die Frage soll deshalb in einem kleinen Transformer weitergeführt werden (v4, eigenes Design).

## 1. Vorregistriertes Ergebnis (v2, Hauptlauf 400–409)

Quelle: `BERICHT.md`, `results/main_report.md`. Eingefroren mit `b9589ce`, `freeze verify` OK.

| Vorhersage | Ergebnis |
|---|---|
| P1 Prämissen | erfüllt, 10/10 |
| P2 M3-B schreibt `red` richtig zu | erfüllt, 10/10 |
| P3 M3-B öffnet bei `global` nichts | **nicht erfüllt**, 6/10 |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen | erfüllt (Latenz 182 gegen 49) |
| P5 M3-B mindestens so treffsicher wie S1-B | erfüllt (10 gegen 9) |
| **Abbruchkriterium** | **ausgelöst** (4/10 Öffnungen unter `global`) |

Nach der vorab festgelegten Regel gilt: Das Wiederöffnen per Modellvergleich funktioniert in diesem Aufbau nicht. Das bleibt das Ergebnis.

## 2. Nachträglich beobachtet

Alle Beobachtungen stammen von verbrauchten Seeds und sind keine Evidenz.

- **Diagnose** (`results/nachtrag_diagnose/`):
  - Die Fehlöffnungen unter `global` haben keinen echten Merkmalseffekt dahinter. Im Großtest gewinnt kein Kandidat.
  - Sie passen zu unkorrigierter Mehrfachprüfung: δ war je Erklärung kalibriert, erklärt wurde aber in 20–40 Runden.
- **Entwicklungsprüfungen für v3** (`results/entwicklung_v3/`), auf 400–409 und 510–514:
  - δ ist über die ganze Erklärserie kalibriert und wird nur bei vollem Puffer angewendet (E10(b)).
  - Ergebnis für M3-B: `red` 15/15 richtig, `global` 1/15 (Seed 510, im Rahmen der Fehlergrenze), `walls` und `none` 0.
  - S1-B mit serienkalibrierter z-Statistik: `red` 14/15, `global` 0/15.
  - S1 auf Holm-p erwies sich als unbrauchbar.

## 3. Deutung (Annahme)

- **Bemerken und Zuschreiben über Überraschung funktionieren in dieser Welt robust.** Das Scheitern von v2 liegt nach allem, was nachträglich sichtbar ist, an der Kalibrierung des Erklärens über wiederholte Runden, nicht am Prinzip.
- **Ungeprüft:** Ob die Serienkalibrierung das auf frischen Seeds behebt, wäre erst mit v3 belegt.
- **Viel Treffsicherheit kommt aus der Strukturvorgabe der 6 Zielzellen-Merkmale.** Mit rohen Merkmalen (M3-A) traf das System in v2 nur 5/10.

## 4. Was für die Fortsetzung (v4) übernommen wird

- **Methodik:**
  - vorab festgelegte Vorhersagen und Auswahlregeln;
  - getrennte Entwicklungs-, Bestätigungs- und Hauptlauf-Seeds mit Nachweis der Nichtnutzung;
  - Einfrieren mit Prüfsummen;
  - nachträgliche Erkundungen getrennt berichtet.
- **Statistik:**
  - Kalibrierung über die ganze Serie, erzwungen und unabhängig vom Alarm;
  - Reichweite der Fehlergrenze nur unter Austauschbarkeit (Spec v3 §4);
  - keine Größen mit Untergrenze für Serienschwellen (Lehre aus Holm-p);
  - gleiche Teilung für Gewinn und Schwelle.
- **Offene Schwäche als Leitfrage:** Wie findet ein System die wieder relevante Dimension ohne vorgegebene Kandidaten, also in seinen eigenen gelernten Merkmalen?

## 5. Falls v3 doch noch laufen soll

- **Spezifikation:** `docs/superpowers/specs/2026-10-06-farb-wiederoeffnung-v3-design.md`. Alle Entscheidungen stehen in §12.
- **Aufwand:**
  - Umsetzungsplan und Umsetzung mit Tests, etwa ein Arbeitstag;
  - Bestätigung 520–524 ohne M3-A, etwa 40 min;
  - Hauptlauf 600–609 mit M3-A, etwa 30 h auf 4 Kernen, ohne M3-A etwa 1 h.
- **Seeds:** 520–524 und 600–609 waren am 06.10.2026 nachweislich unbenutzt. Die Entwicklungsprüfungen danach nutzten nur 400–409 und 510–514. Vor jeder Nutzung ist der Nachweis neu zu führen (Spec v3 §9.1).
