# Hinweise für Claude

## Arbeitsweise (von Luis festgelegt)
- Kleinere Änderungen testen und direkt auf `main` einspielen bzw. Pull Requests selbst mergen, ohne vorher zu fragen.
- Bei größeren Sachen vorher Bescheid geben: wenn etwas gelöscht wird, sich an der Datenbank etwas Grundlegendes ändert, etwas Geld kostet oder etwas an Kunden rausgeht.
- Luis ist kein Vollzeit-Entwickler: Dinge einfach und auf Deutsch erklären, Schritte für ihn klickgenau beschreiben, nicht zu viel auf einmal.

## Projekt
- Bieterblick (Studio LDK). Dieses Repo ist die Website auf GitHub Pages: `index.html` ist die Startseite, `app/` die eigentliche App. Backend und Datenabruf liegen in `StudioLDK/Ausschreibungsfinder`.
- Alles, was auf `main` landet, ist nach ein bis zwei Minuten live.
- Startseite: Effekte nur mit der Klasse `fx` (JavaScript an, keine "Weniger Bewegung"), ohne sie muss alles sichtbar bleiben. Vor dem Einspielen im Browser auf Computer- und Handybreite (390 und 320 Pixel) prüfen.
- Zahlen auf der Startseite nur so, wie sie in der Datenbank stimmen.
- `<meta name="robots" content="noindex, nofollow">` erst zum offiziellen Start entfernen. Nach dem Umzug auf eine eigene Domain `og:image` in `index.html` anpassen.
