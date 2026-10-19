# Hinweise für Claude

## Arbeitsweise (von Luis festgelegt)
- Kleine Korrekturen (Tippfehler, abgeschnittene Knöpfe, Fehler, über die Kunden stolpern) testen und direkt auf `main` einspielen.
- Größere Änderungen (neue Funktionen, sichtbare Änderungen an Aussehen oder Abläufen) erst in die Vorschau: `./vorschau.sh` ausführen, nur `vorschau/` einspielen, Luis den Link https://bieterblick.studioldk.de/vorschau/ geben. Live erst nach seinem „passt, freigeben“.
- Alles mit Geld, Mails an Kunden oder Löschen von Daten: immer erst Luis fragen, Mails vorher als Testmail an ihn.
- Die Vorschau nutzt dieselbe Datenbank wie die echte Seite. Datenbank-Änderungen deshalb so bauen, dass alte und neue App-Version beide funktionieren.
- Jede Änderung lässt sich mit `git revert` zurücknehmen, dann ist in 1 bis 2 Minuten wieder der alte Stand live.
- Bei größeren Sachen vorher Bescheid geben: wenn etwas gelöscht wird, sich an der Datenbank etwas Grundlegendes ändert, etwas Geld kostet oder etwas an Kunden rausgeht.
- Luis ist kein Vollzeit-Entwickler: Dinge einfach und auf Deutsch erklären, Schritte für ihn klickgenau beschreiben, nicht zu viel auf einmal.

## Projekt
- Bieterblick (Studio LDK). Dieses Repo ist die Website auf GitHub Pages: `index.html` ist die Startseite, `app/` die eigentliche App. Backend und Datenabruf liegen in `StudioLDK/Ausschreibungsfinder`.
- Alles, was auf `main` landet, ist nach ein bis zwei Minuten live.
- Startseite: Effekte nur mit der Klasse `fx` (JavaScript an, keine "Weniger Bewegung"), ohne sie muss alles sichtbar bleiben. Vor dem Einspielen im Browser auf Computer- und Handybreite (390 und 320 Pixel) prüfen.
- Zahlen auf der Startseite nur so, wie sie in der Datenbank stimmen.
- Startseite ist seit 17.10.2026 für Suchmaschinen offen (kein `noindex` mehr, `robots.txt` und `sitemap.xml` im Hauptordner). App, Rechtstexte unter `app/` und die Vorschau bleiben auf `noindex`. Zum offiziellen Start die Beschreibung (`meta description`) wieder um „7 Tage kostenlos testen“ ergänzen.
- Adresse seit 17.10.2026: https://bieterblick.studioldk.de (Datei `CNAME`, INWX-Eintrag CNAME `bieterblick` → `studioldk.github.io`). Die alte Adresse studioldk.github.io/App leitet automatisch weiter.
- Bezahlen über Stripe ist eingebaut, aber mit `ZAHLUNG_AKTIV = false` in `app/index.html` ausgeschaltet. Einschalten erst nach `STRIPE_ANLEITUNG.md` im Repo Ausschreibungsfinder.
- Microsoft Store: App ist als PWA vorbereitet (Manifest mit id, Screenshots, Schnellzugriffen). Paket mit PWABuilder erst nach dem Umzug auf die eigene Adresse bauen, weil das Paket an die Adresse gebunden ist.
- Gewerk-Seiten für Google seit 19.10.2026 live (von Luis freigegeben): `auftraege/` (201 Seiten) und `sitemap.xml` baut jeden Morgen `.github/workflows/seo.yml` mit `seo/bauen.py` aus `seo/daten.json` (kommt aus `seo_daten.py` im Repo Ausschreibungsfinder). Gestaltung nur in `seo/bauen.py` ändern, nie die erzeugten Dateien. Für Vorschau-Tests: `python3 seo/bauen.py seo/daten.json vorschau --vorschau`. Die Startseite verlinkt unten auf `auftraege/`.
