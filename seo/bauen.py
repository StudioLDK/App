#!/usr/bin/env python3
"""Baut die öffentlichen Gewerk-Seiten (auftraege/*.html) aus einer Zahlen-Datei.

Aufruf: python3 seo/bauen.py daten.json ZIELORDNER [--vorschau]
Die Zahlen kommen aus seo.json, erzeugt von seo_daten.py im Repo Ausschreibungsfinder (täglich im Abruf).
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
MIN_VERGABEN = 25  # darunter keine Seite, zu wenig Daten
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

BERATER = "die Auftragsberatungsstelle in deinem Bundesland oder deine Handwerkskammer"
LAENDER = {
    "DE1": ("Baden-Württemberg", "baden-wuerttemberg"), "DE2": ("Bayern", "bayern"), "DE3": ("Berlin", "berlin"),
    "DE4": ("Brandenburg", "brandenburg"), "DE5": ("Bremen", "bremen"), "DE6": ("Hamburg", "hamburg"),
    "DE7": ("Hessen", "hessen"), "DE8": ("Mecklenburg-Vorpommern", "mecklenburg-vorpommern"), "DE9": ("Niedersachsen", "niedersachsen"),
    "DEA": ("Nordrhein-Westfalen", "nordrhein-westfalen"), "DEB": ("Rheinland-Pfalz", "rheinland-pfalz"), "DEC": ("Saarland", "saarland"),
    "DED": ("Sachsen", "sachsen"), "DEE": ("Sachsen-Anhalt", "sachsen-anhalt"), "DEF": ("Schleswig-Holstein", "schleswig-holstein"),
    "DEG": ("Thüringen", "thueringen"),
}


def region(code):
    name, kurz = LAENDER[code]
    return {"code": code, "name": name, "kurz": kurz,
            "berater": "das Auftragsberatungszentrum Bayern" if code == "DE2" else BERATER}

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
    "winterdienst": dict(pf=["90620", "90630"], name="Winterdienst", wer="Winterdienst und Schneeräumung",
        text="Winterdienst wird meist im Sommer und Herbst für eine oder mehrere Saisons ausgeschrieben, oft getrennt nach Gebieten oder Objekten. Bezahlt wird häufig eine Pauschale für die Bereitschaft und zusätzlich jeder Einsatz. Wichtig sind kurze Reaktionszeiten und eine lückenlose Dokumentation jedes Einsatzes."),
    "sicherheitsdienst": dict(pf=["7971"], name="Sicherheitsdienst", wer="Bewachungs- und Sicherheitsdienste",
        text="Ausgeschrieben werden Objektschutz, Empfangs- und Pfortendienste sowie Sicherheitsdienste für Veranstaltungen und Unterkünfte, meist als Vertrag über mehrere Jahre. Du brauchst die Erlaubnis nach § 34a Gewerbeordnung, und die eingesetzten Mitarbeiter müssen die vorgeschriebene Unterrichtung oder Sachkundeprüfung haben."),
    "gebaeudereinigung": dict(pf=["9091"], name="Gebäudereinigung", wer="Unterhalts-, Glas- und Grundreinigung",
        text="Reinigung wird meist als Rahmenvertrag über zwei bis vier Jahre vergeben und nach Fläche und Reinigungshäufigkeit kalkuliert. Nutze die Besichtigung der Objekte vor der Kalkulation, wenn sie angeboten wird. Viele Auftraggeber prüfen ungewöhnlich niedrige Preise genauer und achten auf die Einhaltung des Branchenmindestlohns."),
    "garten-landschaftsbau": dict(pf=["451127", "7731"], name="Garten- und Landschaftsbau", wer="Außenanlagen, Pflanz- und Pflegearbeiten",
        text="Neben Außenanlagen bei Neubauten schreiben Städte und Bauämter regelmäßig Pflanzungen und Grünpflege aus, oft als Jahresvertrag. Bei Pflanzarbeiten wird die Fertigstellungs- und Entwicklungspflege über ein bis zwei Jahre häufig gleich mit vergeben. Das bringt planbare Folgeaufträge."),
    "strassenbau": dict(pf=["45233"], name="Straßenbau", wer="Straßen-, Wege- und Tiefbauarbeiten",
        text="Viele Aufträge kommen von der Autobahn GmbH, den Staatlichen Bauämtern und den Landkreisen. Die Lose sind oft groß, es gibt aber auch kleinere Aufträge wie Markierungen, Gehwege oder Reparaturen, die gut zu regionalen Betrieben passen. Achte auf die Vorgaben zur Verkehrssicherung, sie sind ein großer Kostenpunkt."),
    "zimmerer": dict(pf=["45422"], name="Zimmerer- und Holzbau", wer="Zimmerer- und Holzbauarbeiten",
        text="Öffentliche Auftraggeber bauen zunehmend mit Holz, etwa Kitas, Schulerweiterungen und Aufstockungen. Ausgeschrieben werden Dachstühle, Holzrahmenbau und Fassaden aus Holz. Verlangt werden oft Nachweise zum Brandschutz und zur Qualität der Bauteile, plane dafür genug Zeit ein."),
    "bodenbelag": dict(pf=["45432"], name="Bodenbelagsarbeiten", wer="Bodenbelags- und Parkettarbeiten",
        text="Ausgeschrieben werden Linoleum-, PVC- und Teppichbeläge, Parkett und Sportböden, oft in Schulen, Kitas und Verwaltungsgebäuden. Bei Sanierungen gehören die Vorbereitung des Untergrunds und das Entfernen alter Beläge meist dazu. Diese Positionen solltest du besonders sorgfältig kalkulieren."),
    "geruestbau": dict(pf=["452621"], name="Gerüstbau", wer="Gerüstbauarbeiten",
        text="Gerüste werden oft als eigenes Los bei Sanierungen und Neubauten ausgeschrieben, manchmal auch als Rahmenvertrag über mehrere Jahre. Kalkuliert wird meist nach Fläche und Standzeit. Achte deshalb genau auf die vorgesehene Vorhaltezeit und auf die Preise für jede weitere Woche."),
    "abbruch": dict(pf=["451111"], name="Abbrucharbeiten", wer="Abbruch-, Rückbau- und Entkernungsarbeiten",
        text="Häufig geht es um Rückbau vor einem Neubau oder um Entkernungen vor einer Sanierung. Wichtig sind die Vorgaben zur Trennung und Entsorgung der Abfälle und zu Schadstoffen wie Asbest, für die eine eigene Sachkunde nötig ist. Die Entsorgung ist oft der größte Posten in der Kalkulation."),
    "trockenbau": dict(pf=["45324"], name="Trockenbau", wer="Trockenbau- und Gipskartonarbeiten",
        text="Häufig geht es um Ständerwände, abgehängte Decken und Brandschutzbekleidungen in Schulen, Kliniken und Verwaltungsbauten. Für Brandschutzkonstruktionen musst du geprüfte Systeme verwenden und das nachweisen können. Große Vorhaben sind oft in Bauabschnitte geteilt, das macht auch Teilleistungen für kleinere Betriebe möglich."),
}
REIHENFOLGE = ["malerarbeiten", "elektroinstallation", "sanitaer-heizung", "dachdeckerarbeiten", "zimmerer", "tischlerarbeiten", "fliesenarbeiten",
               "bodenbelag", "trockenbau", "geruestbau", "abbruch", "strassenbau", "garten-landschaftsbau", "gebaeudereinigung", "winterdienst", "sicherheitsdienst"]
GEWERKE = {k: GEWERKE[k] for k in REIHENFOLGE}

e = html.escape


def euro(x):
    x = float(x)
    if x >= 1_000_000:
        return f"{x / 1_000_000:.1f}".replace(".", ",") + "\u00a0Mio.\u00a0€"
    schritt = -2 if x < 10_000 else -3
    return f"{round(x, schritt):,.0f}".replace(",", ".") + "\u00a0€"


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


CSS = """@font-face{font-family:'Archivo';font-style:normal;font-display:swap;font-weight:100 900;font-stretch:62% 125%;src:url(/app/fonts/archivo-latin-wdth-normal.woff2) format('woff2-variations');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Archivo';font-style:normal;font-display:swap;font-weight:100 900;font-stretch:62% 125%;src:url(/app/fonts/archivo-latin-ext-wdth-normal.woff2) format('woff2-variations');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+20A0-20AB,U+20AD-20C0,U+2C60-2C7F,U+A720-A7FF}
:root{--papier:#fff;--plan:#F4F5F7;--linie:#E2E4E8;--linie2:#CED2D8;--tusche:#1C1F23;--graphit:#5C626B;--rot:#CC0605;--rot-tief:#A80504;--rot-hell:#FF4A42;--nacht:#16191D;--nacht2:#22262C;--nacht3:#2E333A;--nacht-text:#C3C8CF;--weich:cubic-bezier(.2,.7,.2,1);--schatten:0 1px 2px rgba(22,25,29,.06),0 8px 24px -6px rgba(22,25,29,.14),0 40px 80px -24px rgba(22,25,29,.22)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papier);color:var(--tusche);font-family:'Archivo',system-ui,sans-serif;font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit}
:focus-visible{outline:3px solid var(--rot);outline-offset:3px;border-radius:6px}
.w{max-width:1120px;margin:0 auto;padding:0 20px}
.vorschau{background:var(--rot);color:#fff;text-align:center;font-weight:700;font-size:13px;padding:5px 12px}
header.k{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.9);-webkit-backdrop-filter:saturate(1.6) blur(14px);backdrop-filter:saturate(1.6) blur(14px);border-bottom:1px solid var(--linie)}
header.k .w{display:flex;align-items:center;justify-content:space-between;gap:12px;height:62px}
.marke{display:flex;align-items:center;gap:10px;font-weight:800;font-stretch:118%;font-size:20px;text-decoration:none;letter-spacing:-.01em}
.marke i{width:14px;height:14px;background:var(--rot);border-radius:3px;display:block}
.btn{display:inline-flex;align-items:center;gap:10px;background:var(--rot);color:#fff;font-weight:750;font-stretch:105%;text-decoration:none;padding:15px 24px;border-radius:14px;font-size:17px;line-height:1.2;box-shadow:0 10px 30px -10px rgba(204,6,5,.7);transition:transform .2s var(--weich),background .2s}
.btn:hover{background:var(--rot-tief);transform:translateY(-2px)}
.btn svg{width:18px;height:18px;flex:none}
.btn.klein{padding:9px 14px;font-size:15px;border-radius:11px;box-shadow:none;white-space:nowrap}
.btn-info{font-size:14px;color:var(--graphit);margin:12px 0 0}
.nacht .btn-info{color:var(--nacht-text)}
/* Hero */
.hero{position:relative;background:var(--nacht);color:#fff;overflow:hidden;isolation:isolate}
.hero:before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(60% 55% at 85% 0%,rgba(204,6,5,.38),transparent 70%),radial-gradient(40% 40% at 0% 100%,rgba(204,6,5,.14),transparent 70%)}
.hero:after{content:"";position:absolute;inset:0;z-index:-1;background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);background-size:44px 44px;-webkit-mask-image:linear-gradient(180deg,#000,transparent 85%);mask-image:linear-gradient(180deg,#000,transparent 85%)}
.hero .w{padding-top:26px;padding-bottom:56px}
.pfad{font-size:14px;color:var(--nacht-text);margin:0 0 18px;display:flex;flex-wrap:wrap;gap:4px 8px}
.pfad a{color:var(--nacht-text);text-decoration:none;border-bottom:1px solid rgba(195,200,207,.35)}
.pfad a:hover{color:#fff}
h1{font-weight:850;font-stretch:118%;font-size:clamp(34px,7.6vw,72px);line-height:1;letter-spacing:-.025em;margin:0 0 18px;text-wrap:balance;overflow-wrap:break-word;hyphens:auto}
h1 em{font-style:normal;color:var(--rot-hell)}
.lead{font-size:clamp(17px,2.2vw,20px);color:var(--nacht-text);margin:0;max-width:60ch}
.kern{margin:34px 0 0;display:grid;grid-template-columns:minmax(0,1fr);gap:26px}
.kern-zahl small{display:block;font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--nacht-text);margin-bottom:4px}
.kern-zahl b{display:block;font-weight:850;font-stretch:125%;font-size:min(138px,calc((100vw - 44px) / (var(--n,8) * .7)));line-height:.92;letter-spacing:-.035em;color:var(--rot-hell);font-variant-numeric:tabular-nums;white-space:nowrap}
.kern-zahl p{margin:12px 0 0;color:var(--nacht-text);max-width:44ch}
.kern-zahl p strong{color:#fff;font-weight:700}
.hero-zahlen{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.12);border-radius:18px;overflow:hidden}
.hero-zahlen div{background:rgba(22,25,29,.82);padding:16px 14px}
.hero-zahlen b{display:block;font-weight:850;font-stretch:115%;font-size:clamp(26px,6vw,40px);line-height:1;font-variant-numeric:tabular-nums}
.hero-zahlen span{display:block;font-size:13px;line-height:1.35;color:var(--nacht-text);margin-top:6px}
.hero-cta{margin-top:30px}
@media (min-width:900px){.hero .w{padding-top:40px;padding-bottom:84px}.kern-zahl b{font-size:min(138px,calc(580px / (var(--n,8) * .7)))}.kern{grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);align-items:end;gap:48px}.hero-zahlen{grid-template-columns:1fr}.hero-zahlen div{display:flex;align-items:baseline;gap:14px;padding:18px 22px}.hero-zahlen span{margin:0}}
/* Abschnitte */
.abschnitt{padding-top:64px}
.marke-zeile{display:flex;align-items:center;gap:12px;font-size:13px;font-weight:750;letter-spacing:.12em;text-transform:uppercase;color:var(--rot);margin:0 0 10px}
.marke-zeile:before{content:"";width:22px;height:2px;background:var(--rot)}
h2{font-weight:850;font-stretch:115%;font-size:clamp(27px,4.6vw,44px);line-height:1.05;letter-spacing:-.02em;margin:0 0 14px;text-wrap:balance;overflow-wrap:break-word;hyphens:auto}
.unter{color:var(--graphit);margin:0 0 26px;max-width:62ch;font-size:18px}
.hinweis{font-size:14px;color:var(--graphit);margin:14px 0 0;max-width:72ch}
/* Preisband */
.band-karte{background:var(--plan);border-radius:22px;padding:26px 20px 22px}
.band{position:relative;height:74px;margin:6px 4px 0}
.band .spur{position:absolute;left:0;right:0;top:46px;height:10px;border-radius:99px;background:repeating-linear-gradient(90deg,var(--linie2) 0 2px,transparent 2px 12px)}
.band .spanne{position:absolute;top:40px;height:22px;border-radius:99px;background:linear-gradient(90deg,#F2B8B6,var(--rot) 50%,#F2B8B6);box-shadow:0 8px 22px -8px rgba(204,6,5,.6);transform-origin:left center}
.band .mitte{position:absolute;top:0;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center}
.band .mitte span{background:var(--tusche);color:#fff;font-size:13px;font-weight:750;padding:4px 9px;border-radius:8px;white-space:nowrap}
.band .mitte:after{content:"";width:3px;height:30px;background:var(--tusche);border-radius:2px;margin-top:4px}
.skala{display:flex;justify-content:space-between;font-size:13px;color:var(--graphit);margin:6px 4px 0}
.drei{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:20px}
.drei div{background:#fff;border-radius:14px;padding:14px 12px}
.drei b{display:block;font-weight:850;font-stretch:112%;font-size:clamp(19px,4.4vw,30px);line-height:1.1;font-variant-numeric:tabular-nums}
.drei .rot b{color:var(--rot)}
.drei span{display:block;font-size:13px;line-height:1.35;color:var(--graphit);margin-top:4px}
/* Konkurrenz */
.konkurrenz{display:grid;grid-template-columns:minmax(0,1fr);gap:22px}
.figuren{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end}
.figuren svg{width:34px;height:52px;color:var(--linie2)}
.figuren .du{color:var(--rot)}
.figuren .du-text{font-size:13px;font-weight:750;color:var(--rot);align-self:center;margin-left:4px}
.konk-zahlen{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.konk-zahlen div{border:1px solid var(--linie);border-radius:14px;padding:14px 12px}
.konk-zahlen b{display:block;font-weight:850;font-stretch:112%;font-size:clamp(22px,4.6vw,32px);line-height:1.1;font-variant-numeric:tabular-nums}
.konk-zahlen span{display:block;font-size:13px;line-height:1.35;color:var(--graphit);margin-top:4px}
.fazit{border-left:3px solid var(--rot);padding:2px 0 2px 16px;margin:0;font-size:18px;max-width:62ch}
@media (min-width:900px){.konkurrenz{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:center;gap:48px}}
/* Offene */
.offen{list-style:none;margin:0;padding:0;display:grid;gap:12px}
.offen li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 16px;align-items:start;background:#fff;border:1px solid var(--linie);border-radius:16px;padding:16px 18px;box-shadow:0 1px 2px rgba(22,25,29,.04)}
.offen b{font-weight:700;line-height:1.35;overflow-wrap:anywhere}
.offen small{grid-column:1;display:block;color:var(--graphit);font-size:14px;overflow-wrap:anywhere}
.frist{grid-column:2;grid-row:1 / span 2;text-align:right;white-space:nowrap}
.frist em{display:inline-block;font-style:normal;font-size:13px;font-weight:750;padding:4px 10px;border-radius:99px;background:var(--plan);color:var(--tusche)}
.frist em.knapp{background:var(--rot);color:#fff}
.frist span{display:block;font-size:13px;color:var(--graphit);margin-top:6px}
.offen-mehr{margin:14px 0 0;font-size:15px;color:var(--graphit)}
.offen-mehr a{color:var(--rot);font-weight:700}
@media (max-width:520px){.offen li{grid-template-columns:1fr}.frist{grid-column:1;grid-row:auto;text-align:left;display:flex;gap:10px;align-items:center}.frist span{margin:0}}
/* Ranglisten */
.zwei{display:grid;grid-template-columns:minmax(0,1fr);gap:40px}
@media (min-width:900px){.zwei{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:56px}}
.rang{list-style:none;margin:0;padding:0;counter-reset:r}
.rang li{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:4px 12px;align-items:center;padding:12px 0;border-bottom:1px solid var(--linie);counter-increment:r}
.rang li:before{content:counter(r);width:30px;height:30px;border-radius:9px;background:var(--plan);display:grid;place-items:center;font-weight:800;font-size:14px;grid-row:1 / span 2}
.rang li:first-child:before{background:var(--tusche);color:#fff}
.rang b{font-weight:700;line-height:1.3;overflow-wrap:anywhere}
.rang small{color:var(--graphit);font-size:14px;grid-column:2}
.rang .n{font-size:14px;color:var(--graphit);white-space:nowrap;grid-column:3;grid-row:1}
.rang .strich{grid-column:2 / span 2;height:4px;border-radius:9px;background:var(--plan);overflow:hidden}
.rang .strich i{display:block;height:100%;background:var(--tusche);border-radius:9px;transform-origin:left center}
.rang li:first-child .strich i{background:var(--rot)}
/* Vergleich */
.vergleich{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.vergleich a{display:grid;grid-template-columns:minmax(0,9.5em) minmax(0,1fr) auto;gap:12px;align-items:center;text-decoration:none;padding:7px 10px;border-radius:12px}
.vergleich a:hover{background:var(--plan)}
.vergleich .land{font-weight:650;font-size:15px;overflow-wrap:anywhere;line-height:1.25}
.vergleich .bal{height:14px;border-radius:99px;background:var(--plan);overflow:hidden}
.vergleich .bal i{display:block;height:100%;border-radius:99px;background:var(--linie2);transform-origin:left center}
.vergleich .wert{font-size:14px;color:var(--graphit);white-space:nowrap;text-align:right;font-variant-numeric:tabular-nums}
.vergleich .hier{background:#FFF1F0}
.vergleich .hier .land{color:var(--rot)}
.vergleich .hier .bal i{background:var(--rot)}
@media (max-width:520px){.vergleich a{grid-template-columns:minmax(0,1fr) auto;gap:4px 10px}.vergleich .bal{grid-column:1 / span 2;grid-row:2}}
/* CTA */
.nacht{background:var(--nacht);color:#fff}
.cta{position:relative;overflow:hidden;border-radius:28px;margin:72px 0 0;padding:40px 24px;background:var(--nacht);color:#fff;isolation:isolate}
.cta:before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(70% 90% at 100% 0%,rgba(204,6,5,.45),transparent 65%)}
.cta h2{color:#fff;max-width:18ch}
.cta p{color:var(--nacht-text);max-width:56ch;margin:0 0 22px}
.haken{list-style:none;padding:0;margin:0 0 28px;display:grid;gap:10px}
.haken li{display:flex;gap:12px;align-items:flex-start;color:#fff}
.haken li:before{content:"";flex:none;width:22px;height:22px;margin-top:2px;border-radius:50%;background:var(--rot) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 12.5l4 4 8-9'/%3E%3C/svg%3E") center/14px no-repeat}
@media (min-width:900px){.cta{padding:56px 56px}}
/* Ratgeber */
.ratgeber{display:grid;grid-template-columns:minmax(0,1fr);gap:26px}
@media (min-width:900px){.ratgeber{grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:56px}.ratgeber .kopf{position:sticky;top:96px;align-self:start}}
.typisch{background:var(--plan);border-radius:20px;padding:22px 22px;margin:0 0 26px;font-size:18px}
.schritte{list-style:none;padding:0;margin:0;counter-reset:s;display:grid;gap:22px}
.schritte li{display:grid;grid-template-columns:44px minmax(0,1fr);gap:4px 14px;counter-increment:s}
.schritte li:before{content:counter(s);grid-row:1 / span 2;width:44px;height:44px;border-radius:14px;border:2px solid var(--tusche);display:grid;place-items:center;font-weight:850;font-stretch:115%;font-size:19px}
.schritte h3{font-size:19px;margin:8px 0 2px;line-height:1.25}
.schritte p{margin:0;color:#33373D}
/* Chips und Karten */
.chips{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:8px}
.chips a{display:block;border:1px solid var(--linie2);border-radius:999px;padding:8px 15px;text-decoration:none;font-size:15px;font-weight:600;background:#fff;transition:border-color .2s,color .2s,transform .2s var(--weich)}
.chips a:hover{border-color:var(--rot);color:var(--rot);transform:translateY(-1px)}
.chips .alle a{background:var(--tusche);border-color:var(--tusche);color:#fff}
.karten{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.karte{display:flex;flex-direction:column;gap:10px;text-decoration:none;background:#fff;border:1px solid var(--linie);border-radius:18px;padding:18px;transition:transform .25s var(--weich),box-shadow .25s,border-color .25s}
.karte:hover{transform:translateY(-3px);box-shadow:var(--schatten);border-color:transparent}
.karte b{font-weight:800;font-stretch:110%;font-size:20px;line-height:1.15}
.karte .wert{font-weight:850;font-stretch:115%;font-size:28px;line-height:1;color:var(--rot);font-variant-numeric:tabular-nums}
.karte .wert small{font-size:13px;font-weight:600;color:var(--graphit);font-stretch:100%;margin-left:6px}
.karte .info{display:flex;flex-wrap:wrap;gap:6px}
.karte .info span{font-size:13px;background:var(--plan);border-radius:99px;padding:3px 9px;color:var(--tusche)}
.karte .info .an{background:#FFF1F0;color:var(--rot-tief);font-weight:700}
.karte .mini{height:6px;border-radius:9px;background:var(--plan);overflow:hidden}
.karte .mini i{display:block;height:100%;background:var(--tusche);border-radius:9px;transform-origin:left center}
/* Fuß */
footer{margin-top:80px;border-top:1px solid var(--linie);padding:28px 0 48px;font-size:14px;color:var(--graphit)}
footer .w{display:grid;gap:10px}
footer nav{display:flex;flex-wrap:wrap;gap:6px 18px}
/* Klebeleiste am Handy */
.leiste{display:none}
@media (max-width:720px){.js .leiste{display:flex;position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:30;align-items:center;justify-content:space-between;gap:10px;background:rgba(22,25,29,.94);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);color:#fff;border-radius:18px;padding:10px 10px 10px 16px;box-shadow:0 18px 40px -12px rgba(0,0,0,.5);transform:translateY(140%);transition:transform .45s var(--weich)}.js .leiste.an{transform:none}.leiste span{font-size:14px;line-height:1.3;font-weight:650}.leiste .btn{padding:11px 14px;font-size:15px;box-shadow:none}}
/* Effekte nur mit .fx (JavaScript an, keine "Weniger Bewegung") */
.fx [data-reveal]{opacity:0;transform:translateY(28px);transition:opacity .8s var(--weich) calc(var(--d,0) * 90ms),transform .9s var(--weich) calc(var(--d,0) * 90ms)}
.fx [data-reveal].sichtbar{opacity:1;transform:none}
.fx [data-reveal] .spanne,.fx [data-reveal] .strich i,.fx [data-reveal] .bal i,.fx [data-reveal] .mini i{transform:scaleX(0);transition:transform 1.2s var(--weich) .25s}
.fx [data-reveal].sichtbar .spanne,.fx [data-reveal].sichtbar .strich i,.fx [data-reveal].sichtbar .bal i,.fx [data-reveal].sichtbar .mini i{transform:none}
.fx [data-reveal] .figuren svg{opacity:0;transform:translateY(10px);transition:opacity .4s ease,transform .5s var(--weich);transition-delay:calc(.2s + var(--i,0) * 70ms)}
.fx [data-reveal].sichtbar .figuren svg{opacity:1;transform:none}
.fx .hero h1,.fx .hero .lead{animation:rein .9s var(--weich) both}
.fx .hero .lead{animation-delay:.08s}
.fx .hero .kern{animation:rein 1s var(--weich) .16s both}
@keyframes rein{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}
@media (max-width:560px){.drei{grid-template-columns:1fr;gap:8px}.drei div{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:12px 14px}.drei span{margin:0;text-align:right}}
@media (max-width:360px){.marke{font-size:18px}.btn.klein{padding:8px 10px;font-size:14px}.hero-zahlen div{padding:14px 10px}.drei div,.konk-zahlen div{padding:12px 9px}}"""

JS = """(function(){try{var u=navigator.userAgent||'';if(navigator.webdriver||/bot|crawl|spider|slurp|lighthouse|headless|preview/i.test(u))return;
var q='direkt',h='';try{h=document.referrer?new URL(document.referrer).hostname:''}catch(e){}
if(/studioldk\\.de$/.test(h))q='intern';else if(/(^|\\.)google\\./.test(h))q='google';else if(/bing\\.|duckduckgo|ecosia|yahoo|qwant/.test(h))q='suche';else if(/facebook|fb\\.|messenger/.test(h))q='facebook';else if(/instagram/.test(h))q='instagram';else if(/tiktok/.test(h))q='tiktok';else if(/linkedin|lnkd/.test(h))q='linkedin';else if(/chatgpt|openai|perplexity|claude|copilot|gemini/.test(h))q='ki';else if(h)q='andere';
fetch('https://spsmxuvywjdympvzcqbv.supabase.co/rest/v1/rpc/besuch',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json','apikey':'sb_publishable_m0MvrAV44ilns10dsOmxwA_tQ9ZIyVk','Content-Profile':'tender'},body:JSON.stringify({p_pfad:location.pathname.toLowerCase().slice(0,120),p_quelle:q})}).catch(function(){})}catch(e){}})();
(function(){var d=document,h=d.documentElement;
function fmt(v,art){if(art==='euro'){if(v>=1e6)return (Math.round(v/1e5)/10).toLocaleString('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1})+'\\u00a0Mio.\\u00a0\\u20ac';var s=v<1e4?100:1000;return (Math.round(v/s)*s).toLocaleString('de-DE')+'\\u00a0\\u20ac'}return Math.round(v).toLocaleString('de-DE')}
function zaehl(el){var ziel=+el.getAttribute('data-ziel'),art=el.getAttribute('data-art'),ende=el.textContent,t0=null,dauer=1300;
function schritt(t){if(!t0)t0=t;var p=Math.min(1,(t-t0)/dauer),e=1-Math.pow(1-p,4);el.textContent=fmt(ziel*e,art);if(p<1)requestAnimationFrame(schritt);else el.textContent=ende}
requestAnimationFrame(schritt)}
if(h.classList.contains('fx')){var io=new IntersectionObserver(function(es){es.forEach(function(en){if(!en.isIntersecting)return;var el=en.target;el.classList.add('sichtbar');io.unobserve(el);if(el.hasAttribute('data-ziel'))zaehl(el)})},{rootMargin:'0px 0px -8% 0px'});
d.querySelectorAll('[data-reveal],[data-ziel]').forEach(function(el){io.observe(el)})}
var l=d.querySelector('.leiste'),hero=d.querySelector('.hero');if(l&&hero&&'IntersectionObserver' in window){new IntersectionObserver(function(es){l.classList.toggle('an',!es[0].isIntersecting)}).observe(hero)}
})();"""

PFEIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
FIGUR = '<svg viewBox="0 0 34 52" aria-hidden="true"{k}{s}><circle cx="17" cy="11" r="9" fill="currentColor"/><path d="M2 52c0-12 6.5-22 15-22s15 10 15 22z" fill="currentColor"/></svg>'


def gross(text, ziel, art):
    """Große Kennzahl im Hero. --n (Zeichenzahl) hält sie auf schmalen Handys in einer Zeile."""
    return f'<b data-ziel="{ziel}" data-art="{art}" style="--n:{len(text)}">{text}</b>'


def mehrzahl(n, eins, viele):
    return eins if n == 1 else viele


def tage(frist, stand):
    return (date.fromisoformat(frist) - date.fromisoformat(stand)).days


def knopf(text="30 Tage kostenlos testen", klein=False):
    if klein:
        return f'<a class="btn klein" href="{TESTEN}">Kostenlos testen</a>'
    return f'<a class="btn" href="{TESTEN}">{text} {PFEIL}</a>'


def kopf(titel, beschreibung, pfad, vorschau, breadcrumb):
    robots = '<meta name="robots" content="noindex, nofollow">' if vorschau else f'<link rel="canonical" href="{BASIS}/{pfad}">'
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{BASIS}/{u}"} for i, (n, u) in enumerate(breadcrumb)]}
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titel)}</title>
<meta name="description" content="{e(beschreibung)}">
{robots}
<meta name="theme-color" content="#16191D">
<meta property="og:title" content="{e(titel)}">
<meta property="og:description" content="{e(beschreibung)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:image" content="{BASIS}/img/og.png">
<link rel="icon" href="/app/icons/icon-192.png">
<link rel="apple-touch-icon" href="/app/icons/apple-touch-icon.png">
<link rel="preload" href="/app/fonts/archivo-latin-wdth-normal.woff2" as="font" type="font/woff2" crossorigin>
<script>document.documentElement.classList.add('js');if(window.matchMedia&&!matchMedia('(prefers-reduced-motion: reduce)').matches&&'IntersectionObserver' in window)document.documentElement.classList.add('fx');</script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
{CSS}
</style>
</head>
<body>
{'<div class="vorschau">VORSCHAU, nicht live</div>' if vorschau else ''}
<header class="k"><div class="w"><a class="marke" href="/"><i></i>Bieterblick</a>{knopf(klein=True)}</div></header>
<main>
"""


def fuss(stand, leiste=""):
    return f"""</main>
<footer><div class="w">
<p style="margin:0">Stand {datum(stand)}. Daten: TED (Amtsblatt der EU) und Datenservice Öffentlicher Einkauf, aufbereitet von Bieterblick. Alle Angaben ohne Gewähr, maßgeblich sind die Originalbekanntmachungen.</p>
<nav><a href="/">Bieterblick</a><a href="./">Öffentliche Aufträge</a><a href="/impressum.html">Impressum</a><a href="/datenschutz.html">Datenschutz</a></nav>
</div></footer>
{leiste}
<script>{JS}</script>
</body>
</html>
"""


def leiste(text):
    return f'<div class="leiste" aria-hidden="true"><span>{e(text)}</span><a class="btn" href="{TESTEN}" tabindex="-1">Kostenlos testen</a></div>'


def zeitraum(stand):
    d = date.fromisoformat(stand)
    return f"{MONATE[d.month - 1]} {d.year - 2} bis {MONATE[d.month - 1]} {d.year}"


def cta(titel, text):
    return f"""<section class="w" aria-label="Bieterblick testen"><div class="cta" data-reveal>
<h2>{titel}</h2>
<p>{text}</p>
<ul class="haken">
  <li>Jeden Morgen die passenden neuen Ausschreibungen für dein Gewerk und deinen Umkreis</li>
  <li>Bei jedem Auftrag sehen, wer ähnliche gewonnen hat und zu welchem Preis</li>
  <li>Erinnerung vor jeder Abgabefrist, damit dir nichts durchrutscht</li>
</ul>
{knopf()}
<p class="btn-info">Ohne Zahlungsdaten, endet automatisch.</p>
</div></section>
"""


def vergleich_liste(slug, laender, codes, hier=None):
    """Balken je Bundesland: Vergaben in 12 Monaten, dazu der typische Auftrag."""
    reihen = sorted(codes, key=lambda c: (-laender[c][slug]["vergaben_1j"], LAENDER[c][0]))
    hoch = max(laender[c][slug]["vergaben_1j"] for c in reihen) or 1
    t = ['<ul class="vergleich">\n']
    for c in reihen:
        z = laender[c][slug]
        breite = max(2, round(100 * z["vergaben_1j"] / hoch))
        aktuell = ' class="hier" aria-current="page"' if c == hier else ""
        t.append(f'  <li><a href="{slug}-{LAENDER[c][1]}.html"{aktuell}><span class="land">{LAENDER[c][0]}</span>'
                 f'<span class="bal"><i style="width:{breite}%"></i></span>'
                 f'<span class="wert">{zahl(z["vergaben_1j"])} {mehrzahl(z["vergaben_1j"], "Vergabe", "Vergaben")} · {euro(z["median"])}</span></a></li>\n')
    t.append("</ul>\n")
    return "".join(t)


def seite(slug, z, stand, vorschau, r, im_land, in_laendern, laender):
    g = GEWERKE[slug]
    pfad = f"auftraege/{slug}-{r['kurz']}.html"
    titel = f"Öffentliche Aufträge für {g['name']} in {r['name']}: Preise, Konkurrenz, offene Ausschreibungen"
    beschr = (f"Was zahlen Städte und Gemeinden in {r['name']} für {g['wer']}? Typischer Auftrag {euro(z['median'])}, "
              f"im Mittel {zahl(z['bieter_median'])} Angebote. Aktuelle Ausschreibungen und wer die Aufträge gewinnt, täglich aktualisiert.")
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", "auftraege/"),
                                              (r["name"], f"auftraege/{r['kurz']}.html"), (g["name"], pfad)])]
    of = offene(z.get("offen", []))
    offen_n = z.get("offen_n") or 0
    preise = bool(z.get("median")) and z.get("wert_n", 0) >= 20
    bm = z.get("bieter_median")
    if preise:
        haelfte = f"Die Hälfte der Aufträge liegt zwischen <strong>{euro(z['p25'])}</strong> und <strong>{euro(z['p75'])}</strong>."
    else:
        haelfte = "Mittlerer Auftragswert aus den veröffentlichten Zuschlägen."

    # Hero
    t.append(f"""<section class="hero"><div class="w">
<nav class="pfad" aria-label="Brotkrumen"><a href="./">Öffentliche Aufträge</a><span aria-hidden="true">›</span><a href="{r['kurz']}.html">{r['name']}</a><span aria-hidden="true">›</span><span>{e(g['name'])}</span></nav>
<h1>Öffentliche Aufträge für <em>{e(g['name'])}</em> in {r['name']}</h1>
<p class="lead">Was zahlen Städte, Gemeinden und Landesbehörden in {r['name']} für {e(g['wer'])}, wie viele Betriebe bieten mit, und was ist gerade offen? Alles aus echten Zuschlägen der letzten zwei Jahre.</p>
<div class="kern">
  <div class="kern-zahl"><small>Typischer Auftrag</small>{gross(euro(z['median']), round(float(z['median'])), "euro")}
  <p>{haelfte}</p></div>
  <div class="hero-zahlen">
    <div><b>{zahl(bm) if bm else "?"}</b><span>{mehrzahl(bm or 0, "Angebot", "Angebote")} pro Vergabe im Mittel</span></div>
    <div><b data-ziel="{z['vergaben_1j']}">{zahl(z['vergaben_1j'])}</b><span>{mehrzahl(z['vergaben_1j'], "Vergabe", "Vergaben")} in 12 Monaten</span></div>
    <div><b>{zahl(offen_n)}</b><span>gerade offen</span></div>
  </div>
</div>
<div class="hero-cta">{knopf()}<p class="btn-info">30 Tage gratis, ohne Zahlungsdaten.</p></div>
</div></section>
""")

    # Preise
    if preise:
        hoch = float(z["p75"]) * 1.3
        pos = lambda v: max(0.0, min(100.0, 100 * float(v) / hoch))
        links, rechts, mitte = pos(z["p25"]), pos(z["p75"]), pos(z["median"])
        t.append(f"""<section class="w abschnitt" aria-labelledby="preise">
<p class="marke-zeile">Preise</p>
<h2 id="preise">So viel wird für {e(g['name'])} gezahlt</h2>
<p class="unter">Der typische Auftrag in {r['name']} liegt bei {euro(z['median'])}. Ein Viertel der Aufträge ist kleiner als {euro(z['p25'])}, ein Viertel größer als {euro(z['p75'])}.</p>
<div class="band-karte" data-reveal>
  <div class="band" role="img" aria-label="Preisband: unteres Viertel {euro(z['p25'])}, Median {euro(z['median'])}, oberes Viertel {euro(z['p75'])}">
    <div class="spur"></div>
    <div class="spanne" style="left:{links:.1f}%;width:{rechts - links:.1f}%"></div>
    <div class="mitte" style="left:{mitte:.1f}%"><span>Median {euro(z['median'])}</span></div>
  </div>
  <div class="skala" aria-hidden="true"><span>0 €</span><span>{euro(hoch)}</span></div>
  <div class="drei">
    <div><b>{euro(z['p25'])}</b><span>kleinere Aufträge (unteres Viertel)</span></div>
    <div class="rot"><b>{euro(z['median'])}</b><span>typischer Auftrag (Median)</span></div>
    <div><b>{euro(z['p75'])}</b><span>größere Aufträge (oberes Viertel)</span></div>
  </div>
</div>
<p class="hinweis">Aus {zahl(z['wert_n'])} Zuschlägen mit veröffentlichtem Auftragswert in {r['name']}, {zeitraum(stand)}.</p>
</section>
""")

    # Konkurrenz
    eins = z.get("bieter_eins")
    if eins is None:
        satz = "Wie viele Angebote abgegeben wurden, steht nicht in allen Bekanntmachungen."
    elif eins == 0:
        satz = "Keine Vergabe ging an ein einziges Angebot. Wer mitbietet, trifft also immer auf Wettbewerb, hat bei dieser Zahl an Mitbewerbern aber echte Chancen."
    elif eins <= 5:
        satz = f"Nur bei etwa {zahl(eins)} % der Vergaben gab es ein einziges Angebot. Wer regelmäßig mitbietet, hat echte Chancen, muss aber mit Wettbewerb rechnen."
    else:
        satz = f"Bei etwa {zahl(eins)} % der Vergaben gab es sogar nur ein einziges Angebot. Wer dort mitgeboten hätte, wäre ohne Konkurrenz gewesen."
    figuren = ""
    if bm:
        anzahl = max(1, min(16, round(float(bm))))
        figuren = ('<div class="figuren" role="img" aria-label="Im Mittel ' + zahl(bm) + ' ' + mehrzahl(bm, "Angebot", "Angebote") + ' pro Vergabe">'
                   + "".join(FIGUR.replace("{k}", ' class="du"' if i == 0 else "").replace("{s}", f' style="--i:{i}"') for i in range(anzahl))
                   + '<span class="du-text">du?</span></div>')
    t.append(f"""<section class="w abschnitt" aria-labelledby="konkurrenz">
<p class="marke-zeile">Konkurrenz</p>
<h2 id="konkurrenz">So viele Betriebe bieten mit</h2>
<div class="konkurrenz" data-reveal>
  <div>
    {figuren}
    <p class="unter" style="margin:14px 0 0">Im Mittel gehen bei einer Vergabe in {r['name']} {zahl(bm) if bm else "mehrere"} {mehrzahl(bm or 0, "Angebot", "Angebote")} ein.</p>
  </div>
  <div>
    <div class="konk-zahlen">
      <div><b>{zahl(z['vergaben_1j'])}</b><span>{mehrzahl(z['vergaben_1j'], "Vergabe", "Vergaben")} in 12 Monaten</span></div>
      <div><b>{zahl(z['vergaben_2j'])}</b><span>{mehrzahl(z['vergaben_2j'], "Vergabe", "Vergaben")} in 2 Jahren</span></div>
      <div><b>{zahl(eins) + " %" if eins is not None else "?"}</b><span>mit nur einem Angebot</span></div>
    </div>
    <p class="fazit" style="margin-top:18px">{satz}</p>
  </div>
</div>
</section>
""")

    # Offene Ausschreibungen
    t.append(f"""<section class="w abschnitt" aria-labelledby="offen">
<p class="marke-zeile">Gerade offen</p>
<h2 id="offen">{zahl(offen_n)} offene {mehrzahl(offen_n, "Ausschreibung", "Ausschreibungen")} in {r['name']}</h2>
""")
    if of:
        t.append('<ul class="offen" data-reveal>\n')
        for a, b, c in of:
            n = tage(c, stand)
            rest = "heute" if n <= 0 else f"noch {n} {mehrzahl(n, 'Tag', 'Tage')}"
            knapp = ' class="knapp"' if n <= 7 else ""
            t.append(f'  <li><b>{e(a)}</b><small>{e(b)}</small><span class="frist"><em{knapp}>{rest}</em><span>Frist {datum(c)}</span></span></li>\n')
        t.append("</ul>\n")
        mehr = offen_n - len(of)
        t.append(f'<p class="offen-mehr">{"Eine Auswahl, " + zahl(mehr) + " weitere stehen in Bieterblick. " if mehr > 0 else ""}Alle mit Unterlagen und Link zur Vergabeplattform findest du in der App. <a href="{TESTEN}">Jetzt ansehen</a></p>\n')
    else:
        t.append('<p class="unter">Gerade ist keine passende Ausschreibung mit laufender Frist offen. Neue kommen fast jeden Tag dazu, Bieterblick meldet sie dir am nächsten Morgen.</p>\n')
    t.append("</section>\n")

    t.append(cta(f"Keine Ausschreibung für {e(g['name'])} mehr verpassen",
                 f"Bieterblick durchsucht jeden Tag alle öffentlichen Ausschreibungen in Deutschland und schickt dir morgens, was zu deinem Betrieb in {r['name']} passt."))

    # Auftraggeber und Gewinner
    ag = auftraggeber(z.get("auftraggeber", []))
    gw = gewinner(z.get("gewinner", []))
    if ag or gw:
        t.append('<section class="w abschnitt"><div class="zwei">\n')
        if ag:
            hoch = ag[0][1] or 1
            t.append(f'<div data-reveal><p class="marke-zeile">Auftraggeber</p><h2>Wer in {r["name"]} ausschreibt</h2><ol class="rang">\n' + "".join(
                f'  <li><b>{e(a)}</b><span class="n">{zahl(n)} {mehrzahl(n, "Vergabe", "Vergaben")}</span><span class="strich"><i style="width:{max(4, round(100 * n / hoch))}%"></i></span></li>\n'
                for a, n in ag) + "</ol></div>\n")
        if gw:
            hoch = gw[0][2] or 1
            t.append('<div data-reveal style="--d:1"><p class="marke-zeile">Gewinner</p><h2>Wer die Aufträge gewinnt</h2><ol class="rang">\n' + "".join(
                f'  <li><b>{e(a)}</b><span class="n">{zahl(n)} {mehrzahl(n, "Zuschlag", "Zuschläge")}</span><small>{e(o or "")}</small><span class="strich"><i style="width:{max(4, round(100 * n / hoch))}%"></i></span></li>\n'
                for a, o, n in gw) + "</ol>\n")
            t.append(f'<p class="hinweis">Zuschläge bei Auftraggebern in {r["name"]} in den letzten 2 Jahren, laut den veröffentlichten Bekanntmachungen. Gezeigt werden nur Unternehmen mit Rechtsform wie GmbH oder AG.</p></div>\n')
        t.append("</div></section>\n")

    # Bundesländervergleich
    if len(in_laendern) >= 2:
        reihen = sorted(in_laendern, key=lambda c: -laender[c][slug]["vergaben_1j"])
        platz = reihen.index(r["code"]) + 1
        teurer = sum(1 for c in in_laendern if c != r["code"] and float(laender[c][slug]["median"]) < float(z["median"]))
        andere = len(in_laendern) - 1
        t.append(f"""<section class="w abschnitt" aria-labelledby="vergleich">
<p class="marke-zeile">Vergleich</p>
<h2 id="vergleich">{r['name']} im Vergleich der Bundesländer</h2>
<p class="unter">Bei der Zahl der Vergaben für {e(g['name'])} liegt {r['name']} auf Platz {platz} von {len(in_laendern)}. Der typische Auftrag ist hier größer als in {teurer} von {andere} anderen {mehrzahl(andere, "Bundesland", "Bundesländern")}.</p>
<div data-reveal>{vergleich_liste(slug, laender, in_laendern, r['code'])}</div>
<p class="hinweis">Balken: vergebene Aufträge in den letzten 12 Monaten. Dahinter der typische Auftragswert. Bundesländer mit zu wenigen Zuschlägen fehlen.</p>
</section>
""")

    # Ratgeber
    t.append(f"""<section class="w abschnitt" aria-labelledby="ratgeber"><div class="ratgeber">
<div class="kopf"><p class="marke-zeile">Ratgeber</p><h2 id="ratgeber">So kommst du an öffentliche Aufträge für {e(g['name'])}</h2>
<p class="hinweis">Diese Hinweise sind allgemein und keine Rechtsberatung. Verbindlich sind immer die Vorgaben in der jeweiligen Ausschreibung. Beratung bietet zum Beispiel {r['berater']}.</p></div>
<div>
<p class="typisch"><strong>Typisch bei {e(g['name'])}:</strong> {e(g['text'])}</p>
<ol class="schritte">
  <li><h3>Ausschreibung finden</h3><p>Der Auftraggeber veröffentlicht die Ausschreibung auf einer Vergabeplattform. Bieterblick sammelt sie jeden Tag aus allen Quellen und zeigt dir die passenden.</p></li>
  <li><h3>Unterlagen prüfen</h3><p>Du lädst die Unterlagen herunter, meist mit einem Leistungsverzeichnis, in dem jede Position mit Menge steht. Lies sie früh, damit du Fragen rechtzeitig an die Vergabestelle stellen kannst.</p></li>
  <li><h3>Nachweise bereithalten</h3><p>Typisch sind die Eintragung bei der Handwerkskammer oder im Handelsregister, Referenzen über ähnliche Arbeiten, Angaben zu Mitarbeitern und Umsatz sowie aktuelle Bescheinigungen von Finanzamt, Krankenkasse und Berufsgenossenschaft. Mit einer Präqualifizierung musst du sie nicht jedes Mal neu einreichen.</p></li>
  <li><h3>Angebot abgeben</h3><p>Preise eintragen, alle geforderten Formulare vollständig ausfüllen und bis zur Frist elektronisch einreichen. Verspätete oder unvollständige Angebote werden nicht gewertet. Den Zuschlag bekommt in der Regel das wirtschaftlichste Angebot.</p></li>
  <li><h3>Klein anfangen</h3><p>Aufträge unter dem EU-Schwellenwert werden national ausgeschrieben, oft regional und mit überschaubarem Umfang. Große Vorhaben sind häufig in Lose geteilt, dann bietest du nur für das Los, das zu dir passt.</p></li>
</ol>
</div>
</div></section>
""")

    # Weiter
    t.append(f'<section class="w abschnitt" aria-labelledby="weiter"><p class="marke-zeile">Weiter</p><h2 id="weiter">Weitere Gewerke in {r["name"]}</h2>\n<ul class="chips">\n')
    t.append("".join(f'  <li><a href="{s}-{r["kurz"]}.html">{e(GEWERKE[s]["name"])}</a></li>\n' for s in im_land if s != slug))
    t.append(f'  <li class="alle"><a href="{r["kurz"]}.html">Alle Gewerke in {r["name"]}</a></li>\n</ul>\n')
    if len(in_laendern) >= 2:
        t.append(f'<p class="hinweis" style="margin-top:22px"><a href="{slug}.html">{e(g["name"])}: alle Bundesländer im Vergleich</a></p>\n')
    t.append("</section>\n")
    t.append(fuss(stand, leiste(f"{g['name']} in {r['name']}: passende Aufträge jeden Morgen")))
    return pfad, "".join(t)


def land_seite(r, gw, stand, vorschau, im_land, seiten_land):
    pfad = f"auftraege/{r['kurz']}.html"
    titel = f"Öffentliche Aufträge in {r['name']} nach Gewerk: Preise und offene Ausschreibungen"
    beschr = f"Was Städte, Gemeinden und Behörden in {r['name']} für Handwerk und Dienstleistungen zahlen, wie viel Konkurrenz es gibt und welche Ausschreibungen gerade offen sind. Aus echten Zuschlägen."
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", "auftraege/"), (r["name"], pfad)])]
    offen = sum(gw[s].get("offen_n") or 0 for s in im_land)
    t.append(f"""<section class="hero"><div class="w">
<nav class="pfad" aria-label="Brotkrumen"><a href="./">Öffentliche Aufträge</a><span aria-hidden="true">›</span><span>{r['name']}</span></nav>
<h1>Öffentliche Aufträge in <em>{r['name']}</em></h1>
<p class="lead">Wie viel zahlen öffentliche Auftraggeber in {r['name']} für Handwerk und Dienstleistungen, wie viele Betriebe bieten mit, und was ist gerade offen? Wähl dein Gewerk.</p>
<div class="kern">
  <div class="kern-zahl"><small>Gerade offen</small>{gross(zahl(offen), offen, "zahl")}<p>Ausschreibungen mit laufender Frist in den {len(im_land)} Gewerken auf dieser Seite, Stand {datum(stand)}.</p></div>
</div>
<div class="hero-cta">{knopf()}<p class="btn-info">30 Tage gratis, ohne Zahlungsdaten.</p></div>
</div></section>
<section class="w abschnitt" aria-labelledby="gewerke"><p class="marke-zeile">Gewerke</p><h2 id="gewerke">Dein Gewerk in {r['name']}</h2>
<p class="unter">Typischer Auftragswert aus Zuschlägen der letzten zwei Jahre, Vergaben in den letzten 12 Monaten und was gerade offen ist.</p>
<div class="karten" data-reveal>
""")
    hoch = max(gw[s]["vergaben_1j"] for s in im_land) or 1
    for s in im_land:
        z = gw[s]
        o = z.get("offen_n") or 0
        an = ' class="an"' if o else ""
        t.append(f'  <a class="karte" href="{s}-{r["kurz"]}.html"><b>{e(GEWERKE[s]["name"])}</b>'
                 f'<span class="wert">{euro(z["median"])}<small>typisch</small></span>'
                 f'<span class="mini"><i style="width:{max(3, round(100 * z["vergaben_1j"] / hoch))}%"></i></span>'
                 f'<span class="info"><span>{zahl(z["vergaben_1j"])} {mehrzahl(z["vergaben_1j"], "Vergabe", "Vergaben")} im Jahr</span>'
                 f'<span{an}>{zahl(o)} offen</span></span></a>\n')
    t.append("</div>\n</section>\n")
    t.append(cta(f"Alle Ausschreibungen in {r['name']} im Blick",
                 "Bieterblick durchsucht jeden Tag alle öffentlichen Ausschreibungen in Deutschland und schickt dir morgens die passenden für deinen Betrieb und deinen Umkreis."))
    t.append('<section class="w abschnitt" aria-labelledby="laender"><p class="marke-zeile">Weiter</p><h2 id="laender">Andere Bundesländer</h2>\n<ul class="chips">\n')
    t.append("".join(f'  <li><a href="{k}.html">{n}</a></li>\n' for c, (n, k) in LAENDER.items() if c != r["code"] and c in seiten_land))
    t.append('  <li class="alle"><a href="./">Alle Bundesländer und Gewerke</a></li>\n</ul>\n</section>\n')
    t.append(fuss(stand, leiste(f"Passende Aufträge in {r['name']} jeden Morgen")))
    return pfad, "".join(t)


def gewerk_seite(slug, laender, stand, vorschau, in_laendern):
    g = GEWERKE[slug]
    pfad = f"auftraege/{slug}.html"
    titel = f"Öffentliche Aufträge für {g['name']}: Preise und Konkurrenz in allen Bundesländern"
    beschr = f"Was zahlen öffentliche Auftraggeber für {g['wer']}? Typische Auftragswerte, Zahl der Angebote und offene Ausschreibungen im Vergleich der Bundesländer."
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", "auftraege/"), (g["name"], pfad)])]
    vergaben = sum(laender[c][slug]["vergaben_1j"] for c in in_laendern)
    offen = sum(laender[c][slug].get("offen_n") or 0 for c in in_laendern)
    spitze = max(in_laendern, key=lambda c: laender[c][slug]["vergaben_1j"])
    t.append(f"""<section class="hero"><div class="w">
<nav class="pfad" aria-label="Brotkrumen"><a href="./">Öffentliche Aufträge</a><span aria-hidden="true">›</span><span>{e(g['name'])}</span></nav>
<h1>Öffentliche Aufträge für <em>{e(g['name'])}</em> in Deutschland</h1>
<p class="lead">So viel zahlen Städte, Gemeinden und Behörden für {e(g['wer'])}, und so viel Konkurrenz gibt es, aufgeteilt nach Bundesland.</p>
<div class="kern">
  <div class="kern-zahl"><small>Vergaben in 12 Monaten</small>{gross(zahl(vergaben), vergaben, "zahl")}<p>in den {len(in_laendern)} Bundesländern auf dieser Seite. Die meisten in <strong>{LAENDER[spitze][0]}</strong>.</p></div>
  <div class="hero-zahlen">
    <div><b>{len(in_laendern)}</b><span>Bundesländer mit genug Daten</span></div>
    <div><b>{zahl(offen)}</b><span>gerade offen</span></div>
    <div><b>{euro(laender[spitze][slug]['median'])}</b><span>typisch in {LAENDER[spitze][0]}</span></div>
  </div>
</div>
<div class="hero-cta">{knopf()}<p class="btn-info">30 Tage gratis, ohne Zahlungsdaten.</p></div>
</div></section>
<section class="w abschnitt" aria-labelledby="laender"><p class="marke-zeile">Bundesländer</p><h2 id="laender">Wähl dein Bundesland</h2>
<p class="unter">Balken: vergebene Aufträge in den letzten 12 Monaten. Dahinter der typische Auftragswert. Mit einem Klick siehst du Details, offene Ausschreibungen und die wichtigsten Auftraggeber.</p>
<div data-reveal>{vergleich_liste(slug, laender, in_laendern)}</div>
<p class="hinweis">Bundesländer mit zu wenigen Zuschlägen für eine verlässliche Aussage fehlen.</p>
</section>
<section class="w abschnitt" aria-labelledby="typisch"><p class="marke-zeile">Ratgeber</p><h2 id="typisch">Was ist bei {e(g['name'])} typisch?</h2>
<p class="typisch" data-reveal>{e(g['text'])}</p>
</section>
""")
    t.append(cta(f"Keine Ausschreibung für {e(g['name'])} mehr verpassen",
                 "Bieterblick durchsucht jeden Tag alle öffentlichen Ausschreibungen in Deutschland und schickt dir morgens die passenden für deinen Betrieb und deinen Umkreis."))
    t.append(fuss(stand, leiste(f"{g['name']}: passende Aufträge jeden Morgen")))
    return pfad, "".join(t)


def haupt_seite(stand, vorschau, seiten_land, seiten_gewerk, laender, im_land, in_laendern):
    pfad = "auftraege/"
    titel = "Öffentliche Aufträge für Handwerk und Dienstleister: Preise, Konkurrenz, offene Ausschreibungen"
    beschr = "Was zahlen Städte, Gemeinden und Behörden für Handwerk und Dienstleistungen? Typische Auftragswerte, Zahl der Angebote und offene Ausschreibungen nach Bundesland und Gewerk."
    t = [kopf(titel, beschr, pfad, vorschau, [("Bieterblick", ""), ("Öffentliche Aufträge", pfad)])]
    offen = sum(laender[c][s].get("offen_n") or 0 for c in seiten_land for s in im_land[c])
    t.append(f"""<section class="hero"><div class="w">
<nav class="pfad" aria-label="Brotkrumen"><a href="/">Bieterblick</a><span aria-hidden="true">›</span><span>Öffentliche Aufträge</span></nav>
<h1>Öffentliche Aufträge nach <em>Bundesland</em> und Gewerk</h1>
<p class="lead">Wie viel zahlen öffentliche Auftraggeber für Handwerk und Dienstleistungen, wie viele Betriebe bieten mit, und was ist gerade offen? Alle Zahlen stammen aus echten Zuschlägen der letzten zwei Jahre.</p>
<div class="kern">
  <div class="kern-zahl"><small>Gerade offen</small>{gross(zahl(offen), offen, "zahl")}<p>Ausschreibungen mit laufender Frist in {len(seiten_gewerk)} Gewerken und {len(seiten_land)} Bundesländern, Stand {datum(stand)}.</p></div>
</div>
<div class="hero-cta">{knopf()}<p class="btn-info">30 Tage gratis, ohne Zahlungsdaten.</p></div>
</div></section>
<section class="w abschnitt" aria-labelledby="laender"><p class="marke-zeile">Bundesländer</p><h2 id="laender">Nach Bundesland</h2>
<div class="karten" data-reveal>
""")
    for c in seiten_land:
        o = sum(laender[c][s].get("offen_n") or 0 for s in im_land[c])
        n = len(im_land[c])
        an = ' class="an"' if o else ""
        t.append(f'  <a class="karte" href="{LAENDER[c][1]}.html"><b>{LAENDER[c][0]}</b>'
                 f'<span class="info"><span>{n} {mehrzahl(n, "Gewerk", "Gewerke")}</span><span{an}>{zahl(o)} offen</span></span></a>\n')
    t.append('</div>\n</section>\n<section class="w abschnitt" aria-labelledby="gewerke"><p class="marke-zeile">Gewerke</p><h2 id="gewerke">Nach Gewerk</h2>\n<div class="karten" data-reveal>\n')
    for s in seiten_gewerk:
        n = len(in_laendern[s])
        o = sum(laender[c][s].get("offen_n") or 0 for c in in_laendern[s])
        an = ' class="an"' if o else ""
        t.append(f'  <a class="karte" href="{s}.html"><b>{e(GEWERKE[s]["name"])}</b>'
                 f'<span class="info"><span>{n} {mehrzahl(n, "Bundesland", "Bundesländer")}</span><span{an}>{zahl(o)} offen</span></span></a>\n')
    t.append("</div>\n</section>\n")
    t.append(cta("Keine Ausschreibung mehr verpassen",
                 "Bieterblick durchsucht jeden Tag alle öffentlichen Ausschreibungen in Deutschland und schickt dir morgens die passenden für deinen Betrieb und deinen Umkreis."))
    t.append(fuss(stand, leiste("Passende Aufträge jeden Morgen")))
    return pfad + "index.html", "".join(t)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vorschau = "--vorschau" in sys.argv
    daten = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    ziel = Path(args[1]) / "auftraege"
    stand, laender = daten["stand"], daten["laender"]
    ok = lambda z: (z.get("vergaben_2j") or 0) >= MIN_VERGABEN and z.get("median")
    im_land = {c: [s for s in GEWERKE if s in laender.get(c, {}) and ok(laender[c][s])] for c in LAENDER}
    in_laendern = {s: [c for c in LAENDER if s in im_land[c]] for s in GEWERKE}
    seiten_land = [c for c in LAENDER if im_land[c]]
    seiten_gewerk = [s for s in GEWERKE if len(in_laendern[s]) >= 2]
    ziel.mkdir(parents=True, exist_ok=True)
    for alt in ziel.glob("*.html"):
        alt.unlink()
    pfade = []

    def schreib(pfad, inhalt):
        (ziel.parent / (pfad + "index.html" if pfad.endswith("/") else pfad)).write_text(inhalt, encoding="utf-8")
        pfade.append(pfad)

    for c in seiten_land:
        r = region(c)
        for s in im_land[c]:
            schreib(*seite(s, laender[c][s], stand, vorschau, r, im_land[c], in_laendern[s], laender))
        schreib(*land_seite(r, laender[c], stand, vorschau, im_land[c], seiten_land))
    for s in seiten_gewerk:
        schreib(*gewerk_seite(s, laender, stand, vorschau, in_laendern[s]))
    schreib(*haupt_seite(stand, vorschau, seiten_land, seiten_gewerk, laender, im_land, in_laendern))
    print(f"{len(pfade)} Seiten in {ziel}")
    (ziel / "seiten.txt").write_text("\n".join(pfade) + "\n", encoding="utf-8")
    if not vorschau:
        # Sitemap für Google: Startseite plus alle Gewerk-Seiten
        urls = [f"  <url><loc>{BASIS}/</loc></url>"] + [f"  <url><loc>{BASIS}/{p}</loc><lastmod>{stand}</lastmod></url>" for p in pfade]
        (ziel.parent / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                                  + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
