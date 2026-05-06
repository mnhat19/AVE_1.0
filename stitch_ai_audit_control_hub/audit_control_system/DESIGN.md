---
name: Audit Control System
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a77'
  outline-variant: '#bcc9c6'
  surface-tint: '#006a61'
  primary: '#00685f'
  on-primary: '#ffffff'
  primary-container: '#008378'
  on-primary-container: '#f4fffc'
  inverse-primary: '#6bd8cb'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#924628'
  on-tertiary: '#ffffff'
  tertiary-container: '#b05e3d'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#89f5e7'
  primary-fixed-dim: '#6bd8cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#005049'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb59a'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#773215'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  h1:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  h3:
    fontFamily: Sora
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.4'
  label-caps:
    fontFamily: Source Sans 3
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.05em
  mono-data:
    fontFamily: Source Code Pro
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  grid_columns: '12'
  gutter: 16px
  margin: 24px
---

## Brand & Style

The design system is engineered for precision and high-stakes decision-making. It adopts a "control room" aesthetic that prioritizes information density without sacrificing clarity. The brand personality is authoritative yet unobtrusive, functioning as a sophisticated toolset for expert auditors.

The visual style leans into **Corporate Modernism** with a technical edge. It utilizes clean lines, subtle background grid patterns to imply structure, and high-contrast elements to ensure accessibility (WCAG 2.1 Level AA compliance). The emotional response should be one of absolute reliability and "audit-grade" security—where every pixel serves a functional purpose.

## Colors

The color system is anchored by a sophisticated light grey gradient background that provides depth without the starkness of pure white. **Teal** acts as the primary action color, signaling intelligence and stability, while **Emerald** is used for success states and positive audit confirmations.

To maintain an "audit-grade" feel, the palette avoids decorative hues like purple, focusing strictly on functional color application. High-contrast neutrals (Slate and Navy tones) are used for text and iconography to ensure maximum legibility against the light-grey environment.

## Typography

This design system uses a dual-font strategy to balance character with utility. **Sora** provides a geometric, modern feel for headings, reinforcing the technical "control room" aesthetic. **Source Sans 3** is utilized for all body copy and data displays due to its exceptional legibility at small sizes—critical for high-density audit reports.

For numerical data within tables, a monospaced font is recommended to ensure tabular lining and easy vertical scanning of figures. Labels use an uppercase, tracked-out style to clearly differentiate metadata from primary content.

## Layout & Spacing

The layout philosophy follows a **Rigid Fluid Grid**. While the system responds to screen size, it adheres to a strict 4px baseline shift to maintain the "control room" precision. High-density information is managed through compressed vertical spacing and clear horizontal dividers.

Content is organized into logical "zones" using a 12-column grid. Gutters are kept tight (16px) to maximize the "data-per-square-inch" ratio. Subtle background grid lines (1px stroke, 5% opacity) can be used in dashboard backgrounds to reinforce the technical, structured nature of the tool.

## Elevation & Depth

Hierarchy in this design system is achieved through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows. 

1.  **Base Layer:** The light grey gradient (`--bg-main`).
2.  **Surface Layer:** White cards with a 1px border (`#CBD5E1`).
3.  **Active Layer:** Elements currently being interacted with may use a subtle, crisp 4px shadow with a 10% Teal tint to denote focus.

Depth is used sparingly to keep the UI "lean." Objects "sit" on the grid rather than floating above it. Modal overlays use a blurred backdrop (backdrop-filter: blur(4px)) to maintain the "control room" glass effect without losing the underlying context.

## Shapes

To maintain the professional and trustworthy vibe, the design system utilizes **Soft** geometry (0.25rem/4px radius). This avoids the playfulness of pill shapes while moving away from the harshness of pure 90-degree corners.

- **Standard Elements:** 4px radius (Buttons, Inputs, Cards).
- **Small Elements:** 2px radius (Checkboxes, Status Chips).
- **Large Containers:** 8px radius (Modals).

Lines are consistently 1px wide, using high-contrast colors to define boundaries clearly for accessibility.

## Components

**Buttons & Micro-interactions**
Buttons feature a "hollow-to-solid" transition or a slight weight shift on hover. Use `--teal-600` for primary actions. Micro-interactions should be fast (150ms) and snappy, providing immediate tactile feedback.

**KPI Cards**
High-density cards featuring a bold Sora headline for the metric, a Source Sans 3 label, and a mini sparkline or "trend chip" (Emerald for up, Red for down).

**Data Tables**
Designed for maximum density. Row heights are minimized. Use zebra-striping (subtle grey) on hover. Include integrated filter chips in the header row that allow for instant faceting of audit data.

**Status Badges/Chips**
Small, rectangular chips with a 2px radius. Use low-saturation background tints with high-saturation text for the "audit-grade" look (e.g., light emerald background with dark emerald text).

**File Upload Zones**
Dashed 1px borders using `--border-strong`. The area should change to a solid Teal border with a subtle inner glow when a file is dragged over it.

**Steppers**
Horizontal, slim-line steppers located at the top of audit workflows. Completed steps use the Emerald accent; the active step uses a high-contrast Teal outline.

**Feedback Modals**
Centered, high-contrast dialogs. Use a clear header with a status icon (e.g., a Teal "Info" or Emerald "Success" icon) to ensure the auditor immediately understands the system's state.