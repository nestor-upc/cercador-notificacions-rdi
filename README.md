# Cercador de notificacions R+D+I (prototip)

Aquest cercador permet trobar les notificacions que l'Àrea de Recerca i Transferència de la UPC envia amb Gennews (Mautic). Es poden buscar per paraules i filtrar per emissor: SGERI, Projectes nacionals, Projectes internacionals, Àrea R+D+I, SGI, UCT, etc. Està pensat per inserir-lo en una pàgina Genweb amb un iframe.

- **Font de les dades:** https://portal.gennews.upc.edu/mautic/rdi/preview
- **Adreça del cercador** (un cop activat GitHub Pages): https://nestor-upc.github.io/cercador-notificacions-rdi/

## Com funciona

1. Cada dia, GitHub Actions executa `scraper/scrape.py`. També es pot executar a mà des de la pestanya *Actions*.
2. L'script fa aquestes tasques:
   - descarrega la pàgina de Gennews;
   - extreu de cada notificació el número del butlletí, el títol i l'enllaç;
   - dedueix l'emissor a partir del prefix del títol;
   - desa el resultat a `docs/notificacions.json`.
3. `docs/index.html` és el cercador. És una sola pàgina, sense dependències externes, que llegeix el fitxer JSON.
4. Si no hi ha cap notificació nova, no es desa res. Si de cop surten menys de la meitat de les notificacions que hi havia, l'script s'atura sense tocar res. Això sol indicar que Gennews ha canviat la pàgina.

```
scraper/scrape.py        script de recollida (només Python estàndard)
scraper/emissors.json    taula d'equivalències d'emissors (editable)
docs/index.html          cercador
docs/notificacions.json  dades generades
data/                    instantània inicial (16/11/2026)
.github/workflows/       execució diària
```

## Posada en marxa (una sola vegada)

1. **Activar GitHub Pages:** *Settings → Pages → Build and deployment → Deploy from a branch*. Trieu la branca `main` i la carpeta `/docs`.
2. **Permetre que l'automatització desi canvis:** *Settings → Actions → General → Workflow permissions → Read and write permissions*.
3. **Comprovar l'accés a Gennews:** *Actions → Actualitza les notificacions → Run workflow*.
   - Si acaba en verd, els servidors de GitHub poden llegir Gennews i l'actualització automàtica funciona.
   - Si falla per temps d'espera o accés denegat, `portal.gennews.upc.edu` probablement només és accessible des de la xarxa UPC. En aquest cas, cal executar `scraper/scrape.py` des d'un servidor UPC amb una tasca programada (cron) i publicar-hi la carpeta `docs/`.

## Inserció al Genweb

```html
<iframe src="https://nestor-upc.github.io/cercador-notificacions-rdi/?compacte=1"
        title="Cercador de notificacions R+D+I"
        style="width:100%;height:900px;border:0"></iframe>
```

Abans d'inserir-lo, cal confirmar amb Suport Genweb que es permeten iframes de `github.io`. Si no es permeten, l'alternativa és posar un enllaç destacat a l'adreça del cercador.

### Paràmetres de l'adreça

| Paràmetre | Efecte | Exemple |
|---|---|---|
| `emissor` | Obre el cercador ja filtrat per un o més emissors (identificadors separats per comes) | `?emissor=sgeri` · `?emissor=projectes-nacionals,projectes-internacionals` |
| `q` | Obre el cercador amb una cerca ja feta | `?q=PID2026` |
| `compacte=1` | Amaga el títol i el text introductori (el Genweb ja els posa) | |
| `filtres=0` | Amaga els botons d'emissor, per a una pàgina dedicada a un sol emissor | `?emissor=sgeri&filtres=0&compacte=1` |

Identificadors dels emissors: `area-rdi`, `sgeri`, `projectes-nacionals`, `projectes-internacionals`, `projectes-institucionals`, `sgi`, `uct`, `stge`, `unas`, `ssri`, `parc-upc`, `empren-upc`, `coffee-break`, `teva-idea`, `altres`.

## Editar els emissors

Els emissors es defineixen a `scraper/emissors.json`. Cada emissor té:

- **`prefixos`**: textos que poden aparèixer a l'inici del títol, seguits de `|`, `:`, `-` o ` I `. El prefix s'elimina del títol que es mostra al cercador.
- **`conte`** (opcional): textos que assignen l'emissor si apareixen en qualsevol lloc del títol.

Es poden escriure com a expressions regulars. No distingeixen majúscules de minúscules.

**Decisions provisionals pendents de validar:**
- `ERASMUS` i `EIT RawMaterials` s'assignen a *Projectes internacionals*.
- «Innovació» i «Servei de Gestió de la Innovació» s'assignen a *SGI*.
- Les etiquetes `SAVE THE DATE`, `Recordatori` i `IMPORTANT` no són emissors. Si no hi ha cap altra pista, aquestes notificacions van a *Altres*.

## Limitacions conegudes

- **No hi ha data.** Gennews no publica la data d'enviament, ni a la llista ni al butlletí. El cercador ordena per número de butlletí, que creix amb el temps.
- **L'emissor surt del títol.** Si un títol no porta prefix, la notificació va a *Altres*. La solució de fons és fer servir les categories de Mautic.
- **Dependència de l'estructura de Gennews.** Si Gennews canvia la pàgina, caldrà adaptar `LectorTaula` a `scrape.py`.

## Executar-lo en local

```bash
python3 scraper/scrape.py                                   # des de Gennews (cal accés)
python3 scraper/scrape.py --tsv data/instantania-2026-11-16.tsv
cd docs && python3 -m http.server 8000                      # http://localhost:8000
```
