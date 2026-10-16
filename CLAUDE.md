# Hinweise für Claude

## Arbeitsweise (von Luis festgelegt)
- Kleine Korrekturen (Tippfehler, abgeschnittene Knöpfe, Fehler, über die Kunden stolpern) testen und direkt auf `main` einspielen.
- Größere Änderungen (neue Funktionen, sichtbare Änderungen an Aussehen oder Abläufen) erst in die Vorschau: `./vorschau.sh` ausführen, nur `vorschau/` einspielen, Luis den Link https://studioldk.github.io/App/vorschau/ geben. Live erst nach seinem „passt, freigeben“.
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
- `<meta name="robots" content="noindex, nofollow">` erst zum offiziellen Start entfernen. Nach dem Umzug auf eine eigene Domain `og:image` in `index.html` anpassen.
- Bezahlen über Stripe ist eingebaut, aber mit `ZAHLUNG_AKTIV = false` in `app/index.html` ausgeschaltet. Einschalten erst nach `STRIPE_ANLEITUNG.md` im Repo Ausschreibungsfinder.
- Microsoft Store: App ist als PWA vorbereitet (Manifest mit id, Screenshots, Schnellzugriffen). Paket mit PWABuilder erst nach dem Umzug auf die eigene Adresse bauen, weil das Paket an die Adresse gebunden ist.
