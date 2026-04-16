# Fonts

Drop font files here. The typesetter looks them up via `src/brand/tokens.py::FONT_ROLES`.

Preferred chain for each role (first match wins):

- `headline_bold`: GTAmerica-Black.otf → Inter-Black.ttf → Arial-Black.ttf
- `headline_regular`: GTAmerica-Regular.otf → Inter-Regular.ttf → Arial.ttf
- `body`: DMSans-Regular.ttf → Inter-Regular.ttf → Arial.ttf
- `body_bold`: DMSans-Bold.ttf → Inter-Bold.ttf → Arial-Bold.ttf
- `label_caps`: DMSans-Medium.ttf → Inter-Medium.ttf → Arial.ttf

Quickest path: download Inter from https://rsms.me/inter/ and drop the `.ttf` files in here. The pipeline will still work with PIL's default font but typography won't be brand-correct until real fonts are in place.

Optional: place the real MM wordmark at `logo.png` and update `src/layouts/logo.py` to prefer it over the font-rendered version.
