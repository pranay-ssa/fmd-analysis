---
title: Internal weekly deck style reference
date: 2026-11-11
type: reference
status: active
where: decks/reference/internal_deck_style.md
---

# Internal weekly deck style

Extracted from `decks/weekly_decks/FM3_11092026_StatusUpdate_Deck.pptx` (23 slides, presented
9 November 2026). This is a reference for future drafts. It is not a template, and the branding,
logo and footer text must not be copied into a draft.

The deck uses two masters. Content slides use master 1; the dark cover and closing use master 2.
Slide 21 in that file is the week-45 draft slide with Calibri and a grey table header, so ignore it
when reading the house style. The values below come from master 1, the theme XML and the actual
content shapes.

## Canvas and grid

- 16:9, 13.333 x 7.5 inches.
- Content title box: x 0.58, y 0.37 to 0.40, width 12.18, height 0.92. Left aligned, vertically
  centred.
- Body box: x 0.58, y 1.57, width 12.18, height 5.19.
- Title-to-body gap: about 0.65 inch.
- Two-column body: left column x 0.56, width about 6.24; right column starts around x 7.0; gutter
  about 0.3 inch.
- Footer band: full width, y 6.87, height 0.63. It is a white-to-transparent gradient, not a solid
  bar.
- Footer text: x 0.42, y 7.10, width 7.86, height 0.27; 10 pt, muted grey.
- Logo: x 10.06, y 6.96, width 2.71, height 0.46. Do not copy it into a draft.
- Slide number: x 12.84, y 7.10, width 0.49, height 0.40; 12 pt, light grey.

## Typography

- Theme font: Arial for both major and minor. There is no serif in the house style.
- Title: base 36 pt, regular weight, orange `accent2`, 90% line spacing, left aligned. The title
  box has `normAutofit`, so long titles shrink; observed sizes are 28 to 32 pt. The 36 pt base is
  the design intent, not the size on every slide.
- Body: 11 pt in the actual text boxes. The master body style says 24 pt `accent6`, but the slides
  override it with text boxes at 11 pt. For new work, treat 11 pt as the dense-data body size and
  14 pt as the readable body size.
- Section or callout headings: 14, 16 or 20 pt in the deck; not consistent. Use a clean hierarchy
  in new work: 34 to 36 pt title, 18 to 20 pt section, 11 to 14 pt body, 10 pt caption.
- Table text: 9.5 to 11 pt. Table headers are bold white on dark blue.
- Footer: 10 pt. Slide number: 12 pt.
- Bullet colour: `accent1` at level 1, `accent2` at level 2; bullet font Arial.

## Colour

| Token | Hex | Use |
|---|---|---|
| accent1 | `#0074D3` | primary blue, bullets, links |
| accent2 | `#FF8900` | titles, emphasis |
| accent3 | `#37957C` | green accent |
| accent4 | `#ABA9AE` | grey accent |
| accent5 | `#4E509F` | purple accent |
| accent6 | `#0E4B7E` | dark navy body text |
| dk2 | `#44546A` | secondary dark |
| lt2 | `#E7E6E6` | light grey |
| table header | `#1F4E78` | table header fill |
| status highlight | `#FFFF00` | yellow exception row, used sparingly |

White is the content background. The cover uses a dark blue textured image; the closing uses a
centred mark on a dark background. Do not copy the texture or the logo into a draft.

## Recurring motifs

- Orange title as the first anchor on every content slide.
- White content field, left-aligned text, generous margins.
- Dark blue table header with white text; white and light grey row banding.
- Yellow highlight only for the current or exception row.
- Grayscale evidence images arranged in a strict grid, with a fixed metadata line under each.
- Fixed footer fade, logo at the right, confidentiality line at the left.
- No decorative illustrations, no accent stripes, no card grid. The layout is text, table and
  evidence first.

## How this maps to the current draft

- The current week-46 draft is deliberately unbranded: Cambria titles, Calibri body, forest green
  accent. That is a draft identity, not the house style.
- If the draft is moved into the house template, expect the body to shrink from 14 pt to 11 pt and
  the title to autofit from 34 to 28 to 32 pt. Reduce copy volume before that move, or it will
  shrink further than the layout can carry.
- Borrow the grid, the Arial and orange title anchor, the blue table header and the 10 pt footer.
  Do not copy the Intuceo logo, the confidentiality line, the cover texture or the yellow status
  highlight unless the slide is a status table.

## Machine-readable tokens

The same values are in `decks/reference/internal_deck_style.json` for a future builder or template
script.
