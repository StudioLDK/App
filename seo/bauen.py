#!/usr/bin/env python3
"""Baut die öffentlichen Gewerk-Seiten (auftraege/*.html) aus einer Zahlen-Datei.

Aufruf: python3 seo/bauen.py daten.json ZIELORDNER [--vorschau]
Die Zahlen kommen aus den Tabellen zuschlaege und tenders (Abfrage siehe seo/LIESMICH.md).
Mit --vorschau bekommen die Seiten noindex und den roten Balken.
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

BASIS = "https://bieterblick.studioldk.de"
TESTEN = BASIS + "/?testen=bb-handwerk"
MIN_VERGABEN = 30  # darunter keine Seite, zu wenig Daten
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

REGION = {"kurz": "bayern", "name": "Bayern", "berater": "das Auftragsberatungszentrum Bayern"}

# Reihenfolge = Reihenfolge auf der Übersicht. pf: CPV-Anfänge, nur zur Dokumentation (die Abfrage nutzt dieselben).
GEWERKE = {
    "malerarbeiten": dict(pf=["45442"], name="Malerarbeiten", wer="Maler- und Lackierarbeiten",
        text="Häufig ausgeschrieben werden Anstriche in Schulen, Kitas und Verwaltungsgebäuden, oft als Teil einer Sanierung. Dazu kommen Jahresverträge für kleinere Arbeiten: Dort bietest du Einheitspreise für typische Positionen und wirst über die Laufzeit immer wieder abgerufen. Maler und Lackierer ist ein zulassungspflichtiges Handwerk, die Eintragung in die Handwerksrolle wird deshalb fast immer verlangt."),
    "elektroinstallation": dict(pf=["45311", "45312", "45314", "45315", "45316", "45317"], name="Elektroarbeiten", wer="Elektroinstallation, Beleuchtung, Blitzschutz und Photovoltaik",
        text="Ausgeschrieben werden komplette Elektroinstallationen bei Neubau und Sanierung, aber auch einzelne Gewerke wie Blitzschutz, Beleuchtung oder PV-Anlagen. Für Arbeiten am Stromnetz brauchst du die Eintragung ins Installateurverzeichnis des Netzbetreibers. Oft verlangt werden außerdem Prüfprotokolle und eine vollständige Dokumentation der Anlage."),
    "sanitaer-heizung": dict(pf=["4533"], name="Sanitär, Heizung, Lüftung", wer="Sanitär-, Heizungs- und Lüftungsarbeiten",
        text="Bei öffentlichen Gebäuden geht es oft um energetische Sanierungen, den Tausch von Heizungsanlagen und Lüftungstechnik für Schulen. Viele Ausschreibungen sind nach Gewerken getrennt, du kannst also nur für Heizung oder nur für Sanitär anbieten. Für Gas und Trinkwasser ist die Eintragung ins Installateurverzeichnis des Versorgers üblich, für Kälteanlagen ein Sachkundenachweis."),
    "dachdeckerarbeiten": dict(pf=["45261"], name="Dachdeckerarbeiten", wer="Dachdecker-, Abdichtungs- und Klempnerarbeiten",
        text="Neben Neubauten werden viele Dachsanierungen an Schulen, Turnhallen und Bauhöfen ausgeschrieben, oft zusammen mit Dämmung und Abdichtung. Verlangt werden meist Referenzen über vergleichbare Dachflächen. Plane bei der Kalkulation Gerüst und Absturzsicherung genau ein, oft sind sie eigene Positionen im Leistungsverzeichnis."),
    "fliesenarbeiten": dict(pf=["45431"], name="Fliesenarbeiten", wer="Fliesen-, Platten- und Mosaikarbeiten",
        text="Typisch sind Sanitärräume und Duschen in Schulen, Sporthallen und Kliniken, häufig als ein Los einer größeren Sanierung. Fliesenleger ist seit 2020 wieder ein zulassungspflichtiges Handwerk, die Eintragung in die Handwerksrolle wird deshalb in der Regel geprüft."),
    "tischlerarbeiten": dict(pf=["45421"], name="Tischler- und Fensterbau", wer="Tischler-, Schreiner-, Fenster- und Türarbeiten",
        text="Ausgeschrieben werden Innentüren, Fenster, Trennwände und Einbaumöbel, oft als eigene Lose bei Schulbauten. Bei Brandschutz- und Rauchschutztüren musst du die Zulassung der Produkte nachweisen, bei Fenstern häufig die Wärmedämmwerte. Lies die Produktvorgaben genau, oft sind gleichwertige Produkte erlaubt, wenn du das belegen kannst."),
    "gebaeudereinigung": dict(pf=["9091"], name="Gebäudereinigung", wer="Unterhalts-, Glas- und Grundreinigung",
        text="Reinigung wird meist als Rahmenvertrag über zwei bis vier Jahre vergeben und nach Fläche und Reinigungshäufigkeit kalkuliert. Nutze die Besichtigung der Objekte vor der Kalkulation, wenn sie angeboten wird. Viele Auftraggeber prüfen ungewöhnlich niedrige Preise genauer und achten auf die Einhaltung des Branchenmindestlohns."),
    "garten-landschaftsbau": dict(pf=["451127", "7731"], name="Garten- und Landschaftsbau", wer="Außenanlagen, Pflanz- und Pflegearbeiten",
        text="Neben Außenanlagen bei Neubauten schreiben Städte und Bauämter regelmäßig Pflanzungen und Grünpflege aus, oft als Jahresvertrag. Bei Pflanzarbeiten wird die Fertigstellungs- und Entwicklungspflege über ein bis zwei Jahre häufig gleich mit vergeben. Das bringt planbare Folgeaufträge."),
    "strassenbau": dict(pf=["45233"], name="Straßenbau", wer="Straßen-, Wege- und Tiefbauarbeiten",
        text="Viele Aufträge kommen von der Autobahn GmbH, den Staatlichen Bauämtern und den Landkreisen. Die Lose sind oft groß, es gibt aber auch kleinere Aufträge wie Markierungen, Gehwege oder Reparaturen, die gut zu regionalen Betrieben passen. Achte auf die Vorgaben zur Verkehrssicherung, sie sind ein großer Kostenpunkt."),
    "trockenbau": dict(pf=["45324"], name="Trockenbau", wer="Trockenbau- und Gipskartonarbeiten",
        text="Häufig geht es um Ständerwände, abgehängte Decken und Brandschutzbekleidungen in Schulen, Kliniken und Verwaltungsbauten. Für Brandschutzkonstruktionen musst du geprüfte Systeme verwenden und das nachweisen können. Große Vorhaben sind oft in Bauabschnitte geteilt, das macht auch Teilleistungen für kleinere Betriebe möglich."),
}

e = html.escape


def euro(x):
    x = float(x)
    if x >= 1_000_000:
        return f"{x / 1_000_000:.1f}".replace(".", ",") + " Mio. €"
    return f"{round(x, -3):,.0f}".replace(",", ".") + " €"


def zahl(x):
    x = float(x)
    return f"{x:,.0f}".replace(",", ".") if x == int(x) else f"{x:.1f}".replace(".", ",")


def datum(s):
    d = date.fromisoformat(s)
    return d.strftime("%d.%m.%Y")


def stelle(n):
    """Langen Behördennamen auf das Wesentliche kürzen."""
    n = re.sub(r"\s*\([^)]*\)", "", n)
    n = re.split(r" - | – ", n)[0]
    m = re.match(r"^Freistaat Bayern,? vertreten durch (?:das|den|die) (.+)$", n)
    if m:
        n = m.group(1).replace("Bayerische Landesamt", "Bayerisches Landesamt")
    n = re.split(r",? (?:hier )?vertreten durch", n)[0]
    n = re.sub(r", (?:Direktorium|Technische Geschäftsleitung|Zentrale|Sachgebiet|SG ).*$", "", n)
    n = re.sub(r"\s+Abt\..*$", "", n)
    n = n.replace("Fraunhofer-Gesellschaft zur Förderung der angewandten Forschung e.V.", "Fraunhofer-Gesellschaft")
    n = n.replace("Deutsches Museum von Meisterwerken der Naturwissenschaft und Technik", "Deutsches Museum")
    n = re.sub(r"\bMarkt Markt\b", "Markt", n)
    n = re.sub(r"\s+", " ", n).strip(" ,-")
    return n


def auftraggeber(liste, k=5):
    summe = {}
    for name, n in liste:
        kurz = stelle(name)
        summe[kurz] = summe.get(kurz, 0) + n
    return sorted(summe.items(), key=lambda x: (-x[1], x[0]))[:k]


def gewinner(liste, k=5):
    out = []
    for name, ort, n in liste:
        if any(name.startswith(o[0]) or o[0].startswith(name) for o in out):
            continue
        out.append((name, ort, n))
    return out[:k]


def offene(liste):
    seen, out = set(), []
    for titel, stelle_, frist in liste:
        titel = re.sub(r"\s+", " ", titel).strip()
        titel = re.sub(r"^\d[\d.]* - ", "", titel)
        if titel.startswith(stelle(stelle_) + ": "):
            titel = titel[len(stelle(stelle_)) + 2:]
        key = (titel.lower(), stelle(stelle_))
        if key in seen:
            continue
        seen.add(key)
        out.append((titel, stelle(stelle_), frist))
    return out[:6]


CSS = """@font-face{font-family:'Archivo';font-style:normal;font-display:swap;font-weight:100 900;font-stretch:62% 125%;src:url(/app/fonts/archivo-latin-wdth-normal.woff2) format('woff2-variations')}
:root{--bg:#fff;--flaeche:#F4F5F7;--linie:#E2E4E8;--text:#1C1F23;--leise:#5C626B;--rot:#CC0605}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Archivo',system-ui,sans-serif;font-size:18px;line-height:1.6;-webkit-font-smoothing:antialiased}
.vorschau{background:#CC0605;color:#fff;text-align:center;font-weight:700;font-size:14px;padding:6px 12px}
.w{max-width:860px;margin:0 auto;padding:0 20px}
header.k{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:20px 0}
.marke{display:flex;align-items:center;gap:10px;font-weight:800;font-stretch:115%;font-size:20px;color:inherit;text-decoration:none}
.marke i{width:14px;height:14px;background:var(--rot);border-radius:3px;display:block}
.btn{display:inline-block;background:var(--rot);color:#fff;font-weight:750;text-decoration:none;padding:12px 20px;border-radius:12px}
.btn.klein{padding:9px 14px;font-size:15px;white-space:nowrap}
.pfad{font-size:14px;color:var(--leise);margin:8px 0 0}
.pfad a{color:inherit}
h1{font-weight:850;font-stretch:115%;font-size:clamp(32px,6vw,54px);line-height:1.05;letter-spacing:-.02em;margin:10px 0 14px;text-wrap:balance;overflow-wrap:break-word}
.lead{font-size:20px;color:var(--leise);margin:0 0 30px;max-width:62ch}
h2{font-weight:850;font-stretch:112%;font-size:clamp(24px,4vw,32px);line-height:1.15;margin:52px 0 16px}
.kacheln{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.kachel{background:var(--flaeche);border-radius:16px;padding:18px;color:inherit;text-decoration:none;display:block}
.kachel b{display:block;font-weight:850;font-stretch:110%;font-size:clamp(24px,4vw,34px);line-height:1.1}
.kachel.haupt b{color:var(--rot)}
.kachel span{font-size:15px;color:var(--leise)}
.gewerke .kachel b{font-size:20px;margin-bottom:6px}
.gewerke .kachel:hover{outline:2px solid var(--rot)}
.hinweis{font-size:15px;color:var(--leise);margin-top:10px}
.liste{list-style:none;padding:0;margin:0;border-top:1px solid var(--linie)}
.liste li{padding:14px 0;border-bottom:1px solid var(--linie);display:flex;justify-content:space-between;gap:16px}
.liste li b{font-weight:700;overflow-wrap:anywhere}
.liste li span{color:var(--leise);font-size:15px;white-space:nowrap}
.liste li small{display:block;color:var(--leise);font-size:15px}
.frist{color:var(--rot)!important;font-weight:700}
.box{background:var(--flaeche);border-radius:20px;padding:28px;margin:52px 0}
.box h2{margin-top:0}
.box p{margin:0 0 18px}
.ratgeber h3{font-size:20px;margin:28px 0 6px}
.ratgeber p{margin:0;color:#33373D}
.mehr{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}
.mehr a{display:block;border:1px solid var(--linie);border-radius:999px;padding:6px 14px;color:inherit;text-decoration:none;font-size:16px}
.mehr a:hover{border-color:var(--rot)}
footer{border-top:1px solid var(--linie);margin-top:60px;padding:24px 0 40px;font-size:14px;color:var(--leise)}
footer a{color:inherit}
@media (max-width:620px){.kacheln{grid-template-columns:1fr}.liste li{flex-direction:column;gap:2px}.liste li span{white-space:normal}body{font-size:17px}.box{padding:22px}}
@media (max-width:360px){.marke{font-size:18px}.btn.klein{padding:8px 10px;font-size:14px}}"""


def kopf(titel, beschreibung, pfad, vorschau, breadcrumb):
    robots = '<meta name="robots" content="noindex, nofollow">' if vorschau else f'<link rel="canonical" href="{BASIS}/{pfad}">'
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{BASIS}/{u}"} for i, (n, u) in enumerate(breadcrumb)]}
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title>
<meta name="description" content="{e(beschreibung)}">
{robots}
<meta property="og:title" content="{e(titel)}">
<meta property="og:description" content="{e(beschreibung)}">
<meta property="og:image" content="{BASIS}/img/og.png">
<link rel="icon" href="/app/icons/icon-192.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
{CSS}
</style>
</head>
<body>
{'<div class="vorschau">VORSCHAU, nicht live</div>' if vorschau else ''}
<div class="w">
<header class="k"><a class="marke" href="/"><i></i>Bieterblick</a><a class="btn klein" href="{TESTEN}">Kostenlos testen</a></header>
"""


def fuss(stand):
    return f"""<footer>Stand {datum(stand)}. Daten: TED (Amtsblatt der EU) und Datenservice Öffentlicher Einkauf, aufbereitet von Bieterblick. Alle Angaben ohne Gewähr, maßgeblich sind die Originalbekanntmachungen. · <a href="/impressum.html">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a></footer>
</div>
</body>
</html>
"""


def zeitraum(stand):
    d = date.fromisoformat(stand)
    return f"{MONATE[d.month - 1]} {d.year - 2} bis {MONATE[d.month - 1]} {d.year}"


def seite(slug, g, z, stand, vorschau, alle):
    r = REGION
    pfad = f"auftraege/{slug}-{r['kurz']}.html"
    titel = f"Öffentliche Aufträge für {g['name']} in {r['name']}: Preise, Konkurrenz, offene Ausschreibungen"
    beschr = (f"Was zahlen Städte und Gemeinden in {r['name']} für {g['wer']}? Typischer Auftrag {euro(z['median'])}, "
              f"im Mittel {zahl(z['bieter_median'])} Angebote. Aktuelle Ausschreibungen und wer die Aufträge gewinnt, täglich aktualisiert.")
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", "auftraege/"), (f"{g['name']} in {r['name']}", pfad)])]
    t.append(f"""
<p class="pfad"><a href="./">Öffentliche Aufträge in {r['name']}</a> › {e(g['name'])}</p>
<h1>Öffentliche Aufträge für {e(g['name'])} in {r['name']}</h1>
<p class="lead">Was zahlen Städte, Gemeinden und Landesbehörden in {r['name']} für {e(g['wer'])}, wie viele Betriebe bieten mit, und welche Aufträge sind gerade offen? Alle Zahlen stammen aus echten Zuschlägen der letzten zwei Jahre.</p>
""")
    if z.get("median") and z.get("wert_n", 0) >= 20:
        t.append(f"""<h2>So viel wird gezahlt</h2>
<div class="kacheln">
  <div class="kachel haupt"><b>{euro(z['median'])}</b><span>typischer Auftrag (Median)</span></div>
  <div class="kachel"><b>{euro(z['p25'])}</b><span>kleinere Aufträge (unteres Viertel)</span></div>
  <div class="kachel"><b>{euro(z['p75'])}</b><span>größere Aufträge (oberes Viertel)</span></div>
</div>
<p class="hinweis">Aus {zahl(z['wert_n'])} Zuschlägen mit veröffentlichtem Auftragswert in {r['name']}, {zeitraum(stand)}. Ein Viertel der Aufträge liegt unter {euro(z['p25'])}, ein Viertel über {euro(z['p75'])}.</p>
""")
    eins = z.get("bieter_eins")
    if eins is None:
        satz = ""
    elif eins == 0:
        satz = "Keine Vergabe ging an ein einziges Angebot. Wer mitbietet, trifft also immer auf Wettbewerb, hat bei dieser Zahl an Mitbewerbern aber echte Chancen."
    elif eins <= 5:
        satz = f"Nur bei etwa {zahl(eins)} % der Vergaben gab es ein einziges Angebot. Wer regelmäßig mitbietet, hat also echte Chancen, muss aber mit Wettbewerb rechnen."
    else:
        satz = f"Bei etwa {zahl(eins)} % der Vergaben gab es sogar nur ein einziges Angebot. Wer dort mitgeboten hätte, wäre ohne Konkurrenz gewesen."
    t.append(f"""<h2>So viel Konkurrenz gibt es</h2>
<div class="kacheln">
  <div class="kachel"><b>{zahl(z['bieter_median'])}</b><span>Angebote pro Vergabe im Mittel</span></div>
  <div class="kachel"><b>{zahl(z['vergaben_1j'])}</b><span>vergebene Aufträge in den letzten 12 Monaten</span></div>
  <div class="kachel"><b>{zahl(z['vergaben_2j'])}</b><span>vergebene Aufträge in 2 Jahren</span></div>
</div>
<p class="hinweis">{satz}</p>
""")
    of = offene(z.get("offen", []))
    t.append(f"<h2>Gerade offen in {r['name']}</h2>\n")
    if of:
        t.append('<ul class="liste">\n' + "".join(
            f'  <li><div><b>{e(a)}</b><small>{e(b)}</small></div><span class="frist">Frist {datum(c)}</span></li>\n' for a, b, c in of) + "</ul>\n")
        t.append(f'<p class="hinweis">Eine Auswahl. Alle offenen Ausschreibungen mit Unterlagen und Link zur Vergabeplattform siehst du in Bieterblick.</p>\n')
    else:
        t.append('<p>Gerade ist keine passende Ausschreibung mit Frist offen. Neue kommen fast jeden Tag dazu.</p>\n')
    t.append(f"""
<div class="box">
  <h2>Keine Ausschreibung mehr verpassen</h2>
  <p>Bieterblick schickt dir jeden Morgen die passenden neuen Ausschreibungen für deinen Betrieb und deinen Umkreis per Mail. Dazu siehst du bei jedem Auftrag, wer ähnliche gewonnen hat und zu welchem Preis.</p>
  <a class="btn" href="{TESTEN}">30 Tage kostenlos testen</a>
  <p class="hinweis" style="margin:12px 0 0">Ohne Zahlungsdaten, endet automatisch.</p>
</div>
""")
    ag = auftraggeber(z.get("auftraggeber", []))
    if ag:
        t.append(f"<h2>Wer in {r['name']} ausschreibt</h2>\n<ul class=\"liste\">\n" + "".join(
            f"  <li><b>{e(a)}</b><span>{zahl(n)} {'Vergabe' if n == 1 else 'Vergaben'}</span></li>\n" for a, n in ag) + "</ul>\n")
    gw = gewinner(z.get("gewinner", []))
    if gw:
        t.append("<h2>Wer die Aufträge gewinnt</h2>\n<ul class=\"liste\">\n" + "".join(
            f"  <li><div><b>{e(a)}</b><small>{e(o or '')}</small></div><span>{zahl(n)} Zuschläge</span></li>\n" for a, o, n in gw) + "</ul>\n")
        t.append(f'<p class="hinweis">Zuschläge bei Auftraggebern in {r["name"]} in den letzten 2 Jahren, laut den veröffentlichten Bekanntmachungen. Gezeigt werden nur Unternehmen mit Rechtsform wie GmbH oder AG.</p>\n')
    t.append(f"""
<section class="ratgeber">
  <h2>So kommst du an öffentliche Aufträge für {e(g['name'])}</h2>
  <h3>Was ist bei {e(g['name'])} typisch?</h3>
  <p>{e(g['text'])}</p>
  <h3>Wie läuft das ab?</h3>
  <p>Der Auftraggeber veröffentlicht die Ausschreibung auf einer Vergabeplattform. Du lädst die Unterlagen herunter, meist mit einem Leistungsverzeichnis, in dem jede Position mit Menge steht. Du trägst deine Preise ein und reichst das Angebot bis zur Frist ein, heute fast immer elektronisch über die Plattform. Nach der Wertung bekommt in der Regel das wirtschaftlichste Angebot den Zuschlag.</p>
  <h3>Was brauche ich dafür?</h3>
  <p>Typisch sind ein Nachweis über die Eintragung bei der Handwerkskammer oder im Handelsregister, Referenzen über ähnliche Arbeiten, Angaben zu Mitarbeitern und Umsatz sowie aktuelle Bescheinigungen, etwa von Finanzamt, Krankenkasse und Berufsgenossenschaft. Viele Betriebe lassen sich präqualifizieren. Dann müssen sie diese Nachweise nicht für jede Ausschreibung neu einreichen.</p>
  <h3>Kleine oder große Aufträge?</h3>
  <p>Aufträge unter dem EU-Schwellenwert werden national ausgeschrieben, oft regional und mit überschaubarem Umfang. Gerade dort haben kleinere Betriebe gute Chancen. Große Vorhaben sind häufig in Lose aufgeteilt. Du kannst dann nur für das Los anbieten, das zu dir passt.</p>
  <h3>Drei Tipps</h3>
  <p>Lies die Unterlagen früh, damit du Fragen rechtzeitig an die Vergabestelle stellen kannst. Halte die Frist genau ein, verspätete Angebote werden nicht gewertet. Und fülle alle geforderten Formulare vollständig aus, fehlende Angaben sind einer der häufigsten Gründe für einen Ausschluss.</p>
  <p class="hinweis" style="margin-top:18px">Diese Hinweise sind allgemein und keine Rechtsberatung. Verbindlich sind immer die Vorgaben in der jeweiligen Ausschreibung. Beratung zu öffentlichen Aufträgen bietet zum Beispiel {r['berater']}.</p>
</section>

<div class="box">
  <h2>Passende Aufträge jeden Morgen im Postfach</h2>
  <p>Beschreib in eigenen Worten, was dein Betrieb macht, und wähl deinen Umkreis. Den Rest erledigt Bieterblick.</p>
  <a class="btn" href="{TESTEN}">30 Tage kostenlos testen</a>
</div>

<h2>Weitere Gewerke in {r['name']}</h2>
<ul class="mehr">
""")
    t.append("".join(f'  <li><a href="{s}-{r["kurz"]}.html">{e(GEWERKE[s]["name"])}</a></li>\n' for s in alle if s != slug))
    t.append(f'  <li><a href="./">Alle Gewerke</a></li>\n</ul>\n')
    t.append(fuss(stand))
    return pfad, "".join(t)


def uebersicht(daten, stand, vorschau, alle):
    r = REGION
    pfad = "auftraege/"
    titel = f"Öffentliche Aufträge in {r['name']} nach Gewerk: Preise und offene Ausschreibungen"
    beschr = f"Was Städte, Gemeinden und Behörden in {r['name']} für Handwerksleistungen zahlen, wie viel Konkurrenz es gibt und welche Ausschreibungen gerade offen sind. Aus echten Zuschlägen."
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", pfad)])]
    t.append(f"""
<p class="pfad">Öffentliche Aufträge</p>
<h1>Öffentliche Aufträge in {r['name']} nach Gewerk</h1>
<p class="lead">Wie viel zahlen öffentliche Auftraggeber in {r['name']} für typische Handwerksleistungen, wie viele Betriebe bieten mit, und was ist gerade offen? Wähl dein Gewerk.</p>
<div class="kacheln gewerke">
""")
    for s in alle:
        z = daten[s]
        t.append(f'  <a class="kachel" href="{s}-{r["kurz"]}.html"><b>{e(GEWERKE[s]["name"])}</b>'
                 f'<span>typisch {euro(z["median"])} · {zahl(z["vergaben_1j"])} Vergaben im Jahr</span></a>\n')
    t.append(f"""</div>
<p class="hinweis">Typisch heißt: der mittlere Auftragswert (Median) aus Zuschlägen der letzten zwei Jahre.</p>

<div class="box">
  <h2>Keine Ausschreibung mehr verpassen</h2>
  <p>Bieterblick durchsucht jeden Tag alle öffentlichen Ausschreibungen in Deutschland und schickt dir morgens die passenden für deinen Betrieb und deinen Umkreis.</p>
  <a class="btn" href="{TESTEN}">30 Tage kostenlos testen</a>
  <p class="hinweis" style="margin:12px 0 0">Ohne Zahlungsdaten, endet automatisch.</p>
</div>
""")
    t.append(fuss(stand))
    return pfad + "index.html", "".join(t)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vorschau = "--vorschau" in sys.argv
    daten = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    ziel = Path(args[1])
    stand, gw = daten["stand"], daten["gewerke"]
    alle = [s for s in GEWERKE if s in gw and (gw[s].get("vergaben_2j") or 0) >= MIN_VERGABEN and gw[s].get("median")]
    (ziel / "auftraege").mkdir(parents=True, exist_ok=True)
    pfade = []
    for s in alle:
        pfad, inhalt = seite(s, GEWERKE[s], gw[s], stand, vorschau, alle)
        (ziel / pfad).write_text(inhalt, encoding="utf-8")
        pfade.append(pfad)
    pfad, inhalt = uebersicht(gw, stand, vorschau, alle)
    (ziel / pfad).write_text(inhalt, encoding="utf-8")
    print(f"{len(alle)} Gewerk-Seiten und Übersicht in {ziel / 'auftraege'}")
    # für die Sitemap
    (ziel / "auftraege" / "seiten.txt").write_text("\n".join(["auftraege/"] + pfade) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
