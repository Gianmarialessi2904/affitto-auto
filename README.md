# Affitti Modena · auto

Pagina che si aggiorna **da sola ogni mattina** con gli affitti per 2/3 persone vicino a
viale Toscanini (Buon Pastore / Gottardi). Niente server, niente framework.

    GitHub Actions (cron 07:00) → scrape.py → history/AAAA-MM-GG.json → commit → Pages
                                                                         → index.html (la apri tu)

## Cosa fa
- **Storico**: ogni giorno è salvato in `history/`. In alto nella pagina c'è un menù
  per rivedere i giorni precedenti.
- **I tuoi link**: aggiungili a mano in `miei-link.json` → la pagina te li mostra in
  cima con badge **Tuo**, sempre, su tutti i giorni.
- Se un portale non risponde, la pagina **non si svuota**: tiene gli ultimi dati validi
  e mostra un avviso con la data.

## Setup (una volta, ~15 min)
1. **Crea un repo** su GitHub e carica questi file con la struttura intatta
   (`index.html`, `scrape.py`, `miei-link.json`, `history/`, `.github/workflows/update.yml`).
2. **Pages**: Settings → Pages → *Deploy from a branch* → `main` / `/ (root)`. Salvi e dopo
   un minuto hai l'URL `https://TUO-UTENTE.github.io/REPO/` → **questo è il link da salvare**.
3. **Permessi**: Settings → Actions → General → *Workflow permissions* → **Read and write**.
4. **Prova**: tab Actions → *aggiorna-affitti* → **Run workflow**. Da domani parte da solo.

> Apri la pagina **dall'URL di Pages**, non con doppio click: su `file://` il browser
> blocca la lettura dei file `.json`.

## Aggiungere un tuo link
Apri `miei-link.json` e aggiungi un oggetto (serve solo `url`):
```json
{ "url": "https://www.subito.it/...", "t": "Bilocale che mi piace", "zona": "Gottardi", "prezzo": 750 }
```
Committi → compare subito. (`zona` aiuta a mostrarlo; `t`/`prezzo` sono opzionali.)

## I selettori (l'unica cosa che ti tocca)
`scrape.py` parte con **Unimore** e **Subito**. I selettori marcati `# VERIFICA` sono una
stima: aprendo il portale e facendo "Ispeziona" sul primo annuncio li allinei in 5 minuti.
Per accendere immobiliare/idealista vedi `ENABLED` in cima a `scrape.py`.

## File
- `index.html` — la pagina (storico + tuoi link)
- `scrape.py` — la ricerca, scrive in `history/`
- `miei-link.json` — i tuoi link manuali
- `history/` — un file per giorno + `index.json` (l'elenco dei giorni)
- `.github/workflows/update.yml` — lo scheduler
