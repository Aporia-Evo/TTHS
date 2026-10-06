# Nachträgliche Erkundung: Diagnose der M3-B-Fehlöffnungen (06.10.2026)

**Nachträgliche Erkundung im Sinn von Spec v2 §8.6, auf den verbrauchten Hauptlauf-Seeds 400–409.** Sie ändert am v2-Ergebnis nichts (`../../BERICHT.md`). Sie ist keine Evidenz für eine v3. Was sie zeigt und was nicht, steht im v3-Entwurf `docs/superpowers/specs/2026-10-06-farb-wiederoeffnung-v3-design.md`, Abschnitt 1.

## Inhalt

- `diag.py.txt`: das Skript, unverändert, SHA-256 `e35c0a53…`.
  - Abgelegt als `.txt`: Jede `*.py` im Repo gehört zum v2-Freeze, eine neue würde `freeze verify` scheitern lassen.
  - Es ändert nichts am Repo. Es importiert den eingefrorenen Code (Stand `cbae948`, seit `b9589ce` unverändert) und liest `frozen_config.json`.
  - Aufruf: `python diag.py SEED` in einem Arbeitsordner, mit einem BLAS-Thread. Es schreibt `out_SEED.json` in diesen Ordner.
- `out_400.json` … `out_409.json`: die Ausgaben, je etwa 16 Minuten Rechenzeit.

## Was das Skript rechnet (nur M3-B)

1. **Nachbau:** Phase 1 von M3-B allein (`systems=("M3-B",)`).
   - Geprüft wird die Gleichheit von Übungs-Ontologie, δ und `p_global` mit `results/main/seed_N.json`, Schlüssel `check`.
2. **Null-Serie:** auf den 20 Null-Strömen von Phase 1, erzwungenes Erklären bei jedem Prüfpunkt E = 110, 120, …, 400 (30 Runden). Schlüssel `null_row` und `null_ep`.
   - Basis ist die Übungs-Ontologie. Die Teilung ist nach Zeilen (wie v2) oder nach Episoden.
   - Je Strom wird der größte zulässige Gewinn gespeichert: alle 5 Teilungen > 0, sonst 0.
   - `d_series_row` und `d_series_ep` sind jeweils das Maximum über die 20 Ströme.
   - **Einschränkung:** Die Prüfpunkte vor E = 110 fehlen. Zulässig wären ab E = 30 bzw. 40.
3. **Adaptive Nachspielung** der Einsatzströme `global` und `red`, ab dem in v2 bemerkten Prüfpunkt. Basis ist Übungs-Ontologie + bisher geöffnete Merkmale. Regeln (Schlüssel `deploy`):
   - R0: Zeilen, δ aus v2;
   - R1: Episoden, δ aus v2. Das ist gemischt, weil δ aus Zeilenteilung stammt;
   - R2: Zeilen, `d_series_row`;
   - R3: Episoden, `d_series_ep`.
4. **H3:** je 3000 Episoden `global` und `red` mit eigenem Zufallsschlüssel (Tag 99), Basis Übungs-Ontologie, beide Teilungen. Schlüssel `h3`.

`walls` und `none`, die anderen drei Systeme und zusätzliche Erklärbasen wurden nicht gerechnet.
