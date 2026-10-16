#!/bin/sh
# Kopiert den aktuellen Stand nach vorschau/, damit Luis größere Änderungen vor der Freigabe ansehen kann.
# Adresse: https://studioldk.github.io/App/vorschau/  (App: .../vorschau/app/)
# Achtung: Die Vorschau nutzt dieselbe Datenbank wie die echte Seite.
# Ablauf: Änderung im Arbeitsordner machen, ./vorschau.sh ausführen, NUR vorschau/ einspielen.
#         Nach Freigabe die Änderung selbst einspielen.
set -e
cd "$(dirname "$0")"
rm -rf vorschau
mkdir vorschau
cp -r index.html impressum.html datenschutz.html img app vorschau/
BALKEN='<div style="position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#CC0605;color:#fff;font:700 14px/1 Arial,sans-serif;text-align:center;padding:9px 12px;pointer-events:none">VORSCHAU, nicht live. Kunden sehen diese Version nicht.</div>'
for f in vorschau/index.html vorschau/app/*.html; do
  # nie bei Google, immer mit Balken
  grep -q 'name="robots"' "$f" || sed -i 's#<head>#<head>\n<meta name="robots" content="noindex, nofollow">#' "$f"
  sed -i "s|</body>|$BALKEN\n</body>|" "$f"
done
# Kein Offline-Speicher in der Vorschau, damit immer der neueste Stand geladen wird
sed -i "s#navigator.serviceWorker.register('sw.js')#Promise.resolve()#" vorschau/app/index.html
echo "Vorschau erstellt: https://studioldk.github.io/App/vorschau/"
