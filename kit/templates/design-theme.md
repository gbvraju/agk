# Theme

Standard: agk design standard 1

The brand record of this product and its overrides of the kit's design standard (SPEC-0037 rule 2). Every brand value
has a source line; a value still in brackets is a placeholder and is reported as at risk until the owner gives it. The
theme overrides only its theme block (the brand colour roles and the font stacks, in light and dark) and its layout
block (density and alignment); every other token and rule is the standard's, in `standard.css` of each prototype
version.

## Brand

- name: [brand name] — source: [where the owner wrote it down]
- primary: [primary colour as a hex value] — source: [where the owner wrote it down]
- font: system-ui — source: the kit's default, a system font with no download
- logo: [logo file] — source: [where the owner wrote it down]

## Theme

```css
:root {
  --color-accent: #1a56db;
  --color-on-accent: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-accent: #8ab4ff;
    --color-on-accent: #101418;
  }
}
```

## Layout

- density: comfortable
- alignment: start

## Rules

1. Only the theme block and the layout block are the project's; the standard holds every other token and rule.
2. Contrast of 4.5:1 for text and 3:1 for large text and UI parts, in light and dark, computed after the overrides
   (`check_design.py`).
3. Status is word plus colour: a word as well as a colour, never a colour alone.
4. Native controls (button, input, select, a); no custom widget; targets of 44 px or more.
5. The layout works from 360 px to wide.
6. No script but the kit's runtime, and no external request.

## Evidence

Evidence: {{evidence}}
