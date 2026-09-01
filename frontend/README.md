# Frontend (HTML + TypeScript)

This frontend is a static HTML dashboard styled for a pro share-market theme.

The app now opens on a dedicated home landing view first. Users enter the terminal from the "Open Analysis Terminal" button.

The analysis page has been redesigned as a denser terminal-style experience with improved hierarchy, panel surfaces, and metric readability.

## Structure

- `index.html` - main UI page
- `static/css/style.css` - theme and component styling
- `static/ts/app.ts` - TypeScript source
- `static/js/app.js` - compiled browser script output

## Build

```powershell
npm install
npm run build
```

## Dev (watch mode)

```powershell
npm run watch
```

## Type check only

```powershell
npm run typecheck
```

## Notes

- `index.html` loads `/static/js/app.js` (compiled output), not the `.ts` source.
- Chart rendering depends on Chart.js CDN already referenced in `index.html`.
- Direct open to analysis view is available via `/#analysis`.



