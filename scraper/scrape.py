#!/usr/bin/env python3
"""Genera docs/notificacions.json a partir de la pàgina de previsualització de Gennews (Mautic RDI).

Ús:
    python scraper/scrape.py                      # descarrega la pàgina en directe
    python scraper/scrape.py --html pagina.html   # a partir d'una còpia desada de la pàgina
    python scraper/scrape.py --tsv data/x.tsv     # a partir d'una instantània "id<TAB>títol"

Només fa servir la biblioteca estàndard de Python (3.9+).
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

FONT = "https://portal.gennews.upc.edu/mautic/rdi/preview"
URL_BUTLLETI = "https://gennews.upc.edu/rdi/email/preview/{id}"
ARREL = Path(__file__).resolve().parent.parent
SORTIDA = ARREL / "docs" / "notificacions.json"
EMISSORS = Path(__file__).resolve().parent / "emissors.json"

# Separadors que s'han trobat entre l'emissor i el títol: "|", ":", "-", " I "
SEPARADOR = r"(?:\s*[|:]\s*|\s*[-–]\s*|\s+I\s+)"


class LectorTaula(HTMLParser):
    """Recull els enllaços cap a .../email/preview/NNN i el seu text."""

    def __init__(self):
        super().__init__()
        self.items, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href") or ""
            m = re.search(r"/email/preview/(\d+)", href)
            if m:
                self._href, self._text = m.group(1), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.items.append((int(self._href), "".join(self._text)))
            self._href = None


def descarrega(url, intents=3, timeout=300):
    darrer_error = None
    for i in range(intents):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cercador-notificacions-rdi/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            darrer_error = e
            print(f"Intent {i + 1} fallit: {e}", file=sys.stderr)
            time.sleep(10 * (i + 1))
    raise SystemExit(f"No s'ha pogut descarregar {url}: {darrer_error}")


def neteja(text):
    text = html.unescape(text).replace("’", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def carrega_regles():
    cfg = json.loads(EMISSORS.read_text(encoding="utf-8"))
    regles = []
    for e in cfg["emissors"]:
        prefixos = [re.compile(rf"^(?:{p}){SEPARADOR}(.+)$", re.IGNORECASE) for p in e.get("prefixos", [])]
        conte = [re.compile(p, re.IGNORECASE) for p in e.get("conte", [])]
        regles.append((e, prefixos, conte))
    return cfg["emissors"], regles


def classifica(titol, regles):
    for e, prefixos, _ in regles:
        for rx in prefixos:
            m = rx.match(titol)
            if m:
                return e["id"], m.group(1).strip()
    for e, _, conte in regles:
        if any(rx.search(titol) for rx in conte):
            return e["id"], titol
    return "altres", titol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="Fitxer HTML desat de la pàgina de Gennews")
    ap.add_argument("--tsv", help="Instantània en format id<TAB>títol")
    ap.add_argument("--sortida", default=str(SORTIDA))
    args = ap.parse_args()

    if args.tsv:
        files = Path(args.tsv).read_text(encoding="utf-8").splitlines()
        brut = [(int(a), b) for a, b in (l.split("\t", 1) for l in files if l.strip())]
    else:
        codi = Path(args.html).read_text(encoding="utf-8") if args.html else descarrega(FONT)
        lector = LectorTaula()
        lector.feed(codi)
        brut = lector.items

    emissors, regles = carrega_regles()
    vistos, notificacions = set(), []
    for nid, titol in brut:
        if nid in vistos:
            continue
        vistos.add(nid)
        original = neteja(titol)
        emissor, net = classifica(original, regles)
        notificacions.append({
            "id": nid,
            "emissor": emissor,
            "titol": net,
            "original": original,
            "url": URL_BUTLLETI.format(id=nid),
        })
    notificacions.sort(key=lambda n: n["id"], reverse=True)

    # Salvaguarda: si la pàgina canvia d'estructura i surten molt poques notificacions, no sobreescrivim.
    sortida = Path(args.sortida)
    if sortida.exists():
        anterior = len(json.loads(sortida.read_text(encoding="utf-8")).get("notificacions", []))
        if anterior and len(notificacions) < anterior * 0.5:
            raise SystemExit(f"Només s'han trobat {len(notificacions)} notificacions (abans {anterior}). "
                             "Possible canvi d'estructura de la pàgina: no s'actualitza res.")
    if not notificacions:
        raise SystemExit("No s'ha trobat cap notificació.")

    recompte = {}
    for n in notificacions:
        recompte[n["emissor"]] = recompte.get(n["emissor"], 0) + 1
    dades = {
        "actualitzat": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "font": FONT,
        "emissors": [{"id": e["id"], "nom": e["nom"], "total": recompte.get(e["id"], 0)} for e in emissors],
        "notificacions": notificacions,
    }
    sortida.parent.mkdir(parents=True, exist_ok=True)
    sortida.write_text(json.dumps(dades, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(notificacions)} notificacions desades a {sortida}")
    for e in dades["emissors"]:
        print(f"  {e['nom']}: {e['total']}")


if __name__ == "__main__":
    main()
