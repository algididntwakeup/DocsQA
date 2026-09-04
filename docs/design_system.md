# Stitch Design System Snapshot

**Status:** COMPLETE (2026-09-04)

**Stitch project ID:** 9978725055094825738 (Material QC Document Dashboard)

**Snapshot date:** 2026-09-04

**Source screens:** 
- `fd821940390e47898c54e85c8a4765b2` (MatQC Industrial Logo)
- `710cf0fc0e3b4f07a8a063764b5420a4` (Active Document QC Inspection)
- `78e00f74aa8d4baab07ed9448febeff7` (Active Document QC Inspection (Light Mode))
- `6edbc1734a05464481cee22e2c96387d` (Active Document QC Inspection - Specialized Error Panels)

This file is the versioned, non-secret snapshot of visual tokens fetched from
the approved Stitch project.

---
name: Precision Spec QC
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c3c6d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8d90a0'
  outline-variant: '#434655'
  surface-tint: '#b4c5ff'
  primary: '#b4c5ff'
  on-primary: '#002a78'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#0053db'
  secondary: '#89ceff'
  on-secondary: '#00344d'
  secondary-container: '#00a2e6'
  on-secondary-container: '#00344e'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#007d55'
  on-tertiary-container: '#bdffdb'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#c9e6ff'
  secondary-fixed-dim: '#89ceff'
  on-secondary-fixed: '#001e2f'
  on-secondary-fixed-variant: '#004c6e'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: '600'
    lineHeight: 2.5rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  title-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.375rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.125rem
    letterSpacing: 0.005em
  spec-code-lg:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: -0.01em
  spec-code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: 0em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  2xs: 0.125rem
  xs: 0.25rem
  sm: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  2xl: 2rem
  gutter: 1rem
  sidebar-width: 20rem
  inspector-width: 24rem
---

## Brand & Style

The design system is engineered for material scientists, metallurgists, and structural compliance auditors operating in mission-critical quality control environments. The brand personality is clinical, uncompromising, and deeply utilitarian. It avoids ornamental decoration in favor of density, analytical legibility, and physical instrument ergonomics.

The visual style is **Technical Precision / High-Density Minimalist**:
- High-contrast structural boundaries with crisp micro-borders that emulate engineering blueprints and calibrated lab instrument consoles.
- High-efficiency screen usage prioritizing maximum data density without visual friction.
- Decisive semantic signifiers for fast document scanning, error triage, and verification workflows.

## Colors

The palette is anchored in cold, structural metallurgy—slate steels, titanium, and carbon—with high-signal functional hues calibrated for rapid visual triage.

### Core Surfaces & Grays
- **Base Canvas (App Surface):** `#090d16` (Deep cold carbon void)
- **Document Workspace Surface:** `#ffffff` (High-contrast, true neutral paper grade for document viewport) / `#0f172a` (Document canvas background)
- **Panel Surface (Elevated):** `#0f172a` (Slate 900)
- **Panel Inset / Sub-layer:** `#1e293b` (Slate 800)
- **Borders & Dividers:** `#334155` (Slate 700 - structural outline) / `#1e293b` (Subtle boundary)
- **Primary Text:** `#f8fafc` (Titanium White)
- **Muted Text / Metadata:** `#94a3b8` (Cold Slate 400)

### Functional & Quality Control Semantics
- **Technical Terms / Annotations (Azure):** `#38bdf8` (Border/Icon), `#0369a1` (Fill tint 12%)
- **Data Inconsistencies / Tolerance Warnings (Amber):** `#fbbf24` (Warning state), `#b45309` (Accent shade)
- **Orthographic & Typographical Errors (Crimson):** `#f43f5e` (Critical flag), `#9f1239` (Stroke emphasis)
- **Validated / Approved Spec Pass (Emerald):** `#10b981` (Verification seal), `#064e3b` (Subdued container)

## Typography

Typography enforces a strict dual-engine schema:
1. **Inter** governs human-readable prose, document body copies, high-level headers, and global application navigation.
2. **JetBrains Mono** governs metallurgical standards codes (e.g., `ASTM E8/E8M-21`, `EN 10204 3.1`), chemical compositions, numeric tolerances, heat numbers, and status badges.

All tabular data figures must use tabular numerals (`tnum`, `zero`) to ensure vertical decimal alignment across multi-row analytical reports.

## Layout & Spacing

The layout is built as an instrument workstation: fixed full-height app framing (`100vh`) with fluid multi-pane panels.

- **Workspace Grid**: Fixed 3-column operational layout on desktop:
  - **Left Rail (Navigation & Spec Batch Hierarchy):** Fixed `20rem` (`sidebar-width`), scrollable internally.
  - **Center Stage (Document Viewport & Difference Engine):** Fluid flex pane with dynamic zoom controls and synchronized side-by-side rendering.
  - **Right Rail (QC Inspector & Anomaly Stack):** Fixed `24rem` (`inspector-width`) for detailed deviation lists, tolerance overrides, and chemical composition breakdown.
- **Rhythm & Grid Density**: Uses a micro 4px/8px coordinate system. Component padding defaults to compact sizes (`0.5rem` to `0.75rem`) to maximize visible information above the fold.
- **Responsive Handling**: Below `1280px`, the QC Inspector switches to a docked slide-over drawer; below `1024px`, the workspace locks to single-pane mode with a tabbed viewport switch.

## Elevation & Depth

Visual hierarchy is maintained through **tonal layering and micro-borders** rather than diffused drop shadows.

- **Micro-Borders:** Every panel, card, and modular dock is delineated by a `1px` solid border (`#1e293b` for default panels, `#334155` for active or focused modules).
- **Tonal Stepping:**
  - Base canvas: `#090d16`
  - Inactive / secondary panels: `#0f172a`
  - Active focused panel: `#1e293b`
  - Hover states: Lighten background by 4% surface luminescence without expanding boundaries.
- **Shadows:** Strictly zero drop shadows on standard UI controls. Shadows are reserved solely for floating overlay tooltips and context menus, utilizing a crisp zero-spread technical edge: `box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6), 0 0 0 1px #334155`.

## Shapes

The design uses tight, deliberate chamfering and micro-radii to maintain an industrial, machined tool aesthetic.

- **Base Components (Inputs, Buttons, Badges):** `roundedness: 1` (`0.25rem` / 4px).
- **Cards, Panels, and Viewport Containers:** `0.375rem` (6px) maximum.
- **Tags & Status Flags:** Rectangular with `2px` corners or hard right-angle edges.
- No pill-shaped elements or fully circular buttons exist in this system, preserving geometric alignment with monospace tables and technical drawings.

## Components

### Buttons
- **Primary QC Action (e.g., "Sign-off Batch"):** Background `#2563eb`, text `#ffffff`, border `1px solid #3b82f6`, hover `#1d4ed8`. Height: `32px`. Text in JetBrains Mono `0.75rem` medium.
- **Secondary / Utility:** Background `#0f172a`, text `#f8fafc`, border `1px solid #334155`, hover `#1e293b`.
- **Destructive / Reject:** Background `#1c1917`, text `#f43f5e`, border `1px solid #9f1239`, hover `#9f1239` with text `#ffffff`.

### QC Status Badges & Chips
- Monospaced, uppercase, high contrast with 1px border matching text color at 40% opacity.
- **Typo / Grammar Flag:** Text `#f43f5e`, background `rgba(244, 63, 94, 0.1)`, border `#f43f5e`.
- **Tolerance Inconsistency:** Text `#fbbf24`, background `rgba(251, 191, 36, 0.1)`, border `#fbbf24`.
- **Nomenclature / Terminology:** Text `#38bdf8`, background `rgba(56, 189, 248, 0.1)`, border `#38bdf8`.
- **Approved / Conforming:** Text `#10b981`, background `rgba(16, 185, 129, 0.1)`, border `#10b981`.

### Data Cards & Inspection Tiles
- Background `#0f172a`, border `1px solid #1e293b`.
- Top header row with micro-label in JetBrains Mono uppercase (`0.6875rem`, text `#94a3b8`) paired with an inline status indicator dot (`6px` diameter).
- Row items separated by hairline rules (`#1e293b`).

### Form Inputs & Spec Parameter Fields
- Inset dark styling: background `#090d16`, border `1px solid #334155`, focus ring `1px solid #38bdf8` with zero blur halo.
- Labels positioned strictly above fields in `label-caps` typography.
- Unit adornments (e.g., `MPa`, `HV`, `wt%`, `°C`) locked inside input right-aligned using `#64748b`.

### Document Viewport & Diff Overlay
- Dual rendering mode: High-contrast pure white sheet emulation with vector overlay markings for engineering prints, or dark inverted raster mode.
- In-document highlights:
  - Red strikethrough with `#f43f5e` outline for OCR typographical issues.
  - Amber dotted bounding boxes for numeric deviation outside ASTM/ISO standard ranges.
  - Blue bracketed indicators for technical terminology cross-references.
