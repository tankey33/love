# Site heading fonts

These fonts are hosted with the site, so loading a page does not contact Google Fonts.
Both are licensed under the SIL Open Font License 1.1; the complete upstream
licenses are included alongside the binaries.

- `memory-latin.woff2`: Cormorant Garamond, normal variable weight 400–600;
  subset to Latin letters, digits, spaces, ampersand, punctuation and the heart.
  [Upstream family](https://github.com/google/fonts/tree/main/ofl/cormorantgaramond)
- `memory-serif.woff2`: Noto Serif SC, normal variable weight 400–600;
  subset to 238 characters used in the site's static headings, homepage copy,
  date labels and digits. Other characters use the system serif fallback.
  [Upstream family](https://github.com/google/fonts/tree/main/ofl/notoserifsc)

Downloaded from the official `fonts.googleapis.com` CSS API and
`fonts.gstatic.com` font CDN on 2026-10-19. The stylesheet in `tokens.css` uses
`font-display: swap`, keeping text visible while the subset loads.
