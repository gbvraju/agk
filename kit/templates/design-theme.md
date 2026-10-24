# Theme

The brand record and the rules of this product's design. Every brand value has a source line; a value still in
brackets is a placeholder and is reported as at risk until the owner gives it.

## Brand

- name: [brand name] — source: [where the owner wrote it down]
- primary: [primary colour as a hex value] — source: [where the owner wrote it down]
- font: system-ui — source: the kit's default, a system font with no download

## Tokens

```css
:root {
  --bg: #ffffff;
  --fg: #111111;
  --muted: #555555;
  --accent: #1a56db;
  --accent-fg: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101418;
    --fg: #f2f2f2;
    --muted: #b0b0b0;
    --accent: #8ab4ff;
    --accent-fg: #101418;
  }
}
```

## Contrast

- --fg on --bg
- --muted on --bg
- --accent-fg on --accent

## Rules

1. One token block, light and dark; every colour of a page is a token.
2. Contrast of 4.5:1 or more for each pair above, in both modes, by a computed test (`check_design.py`).
3. Status is word plus colour: a word as well as a colour, never a colour alone.
4. Native controls (button, input, select, a); no custom widget.
5. Targets of 44 px or more.
6. The layout works from 360 px to wide.
7. A system font, no script, no external request.

## Evidence

Evidence: {{evidence}}
