# Style-Guide Lernscripte (aus Referenz-PDFs gemessen)

Quelle: NEINT1_02_OSI_Schicht_pdf.pdf, NEINT1_04_01_IPv4_1.pdf
Alle Werte programmatisch via PyMuPDF ausgelesen (Bestätigt), keine Schätzungen.

## Farben (Hex, exakt gemessen)

| Zweck | Hex | Anmerkung |
|---|---|---|
| Primärblau (Titel, Bullets, Banner) | `#0071B2` | WBS-Blau |
| Hellblau (Flächen, Fußzeile) | `#D2E8F4` | Hintergrund Kapiteltrenner/Fußzeile |
| Fußzeilentext | `#89A5C9` | 12 pt |
| Fließtext dunkel | `#161616` | |
| Akzent Orange | `#FE5000` | "VIELEN DANK!", Nummern-Badges |
| Signalrot | `#FF0000` | z. B. Schicht 1, Hervorhebungen |
| OSI-Schichtfarben | `#0071B2`, `#868686`, `#FFC000`, `#92D050`, `#FFB999`, `#7ACFFF`, `#FF0000` | Schicht 7→1 |

## Typografie

- Schriftfamilie: **Source Sans Pro** (Regular/Bold/Italic); Quelle 2 nutzt Calibri → Source Sans Pro ist der Zielstandard. Fallback in ReportLab: Helvetica, oder Source Sans Pro als TTF einbetten.
- Folientitel: 44 pt Bold, `#0071B2`
- Deckblatt-Haupttitel: 48 pt, Untertitel 24 pt, `#0071B2`
- Untertitel/Kicker (kursiv): 18 pt Italic, `#0071B2`
- Fließtext/Bullets: 18 pt, `#161616` bzw. `#0071B2` je nach Quelle
- Fußzeile: 12 pt, `#89A5C9`
- Bullet-Zeichen: 22 pt, `#0071B2`

## Layout

- Seitenformat Quelle: 960×540 pt (16:9 Folien). **Für Lernscripte gilt weiterhin A4 hoch** (etablierter Lernscriptmodus-Stil) — die Folienmaße dienen nur als Farb-/Typo-Referenz.
- Fußzeilen-Balken: hellblaue Fläche `#D2E8F4` unten (~60 pt hoch), darüber Linie `#0071B2` mit charakteristischer Pfeil-Kerbe (V-Notch) bei ~x=455/960.
- Kapiteltrenner: ganzflächig `#D2E8F4`, Titel 44 pt Bold Blau.

## Lernscript-Elemente (etablierter Stil, zusätzlich zur Quelle)

- Farbcodierte Kapitelbanner pro Thema
- Boxen: Merke (blau), Beispiel (grün), Achtung (rot/orange), Info (grau)
- Vergleichstabellen, beginnerfreundliche Sprache
