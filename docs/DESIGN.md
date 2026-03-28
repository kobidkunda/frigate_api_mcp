# Design System Document: Factory Analytics Digital Excellence



## 1. Overview & Creative North Star



**Creative North Star: "The Industrial Sentinel"**

This design system moves beyond the "standard dashboard" by treating data not as a collection of boxes, but as a high-fidelity control deck. The "Industrial Sentinel" aesthetic combines the precision of high-end editorial layouts with the atmospheric depth of a deep-sea command center.



To break the "template" look, we utilize **Tonal Architecture** rather than structural containment. By eschewing traditional 1px borders and rigid grids, we create a layout that feels fluid yet authoritative. Key sections overlap slightly in visual weight, and high-contrast typography scales are used to create an intentional information hierarchy that prioritizes rapid cognitive processing over decorative clutter.



---



## 2. Colors



The palette is rooted in a deep charcoal and navy foundation, allowing vibrant industrial status indicators to pierce through the darkness with clarity.



### Surface Hierarchy & Nesting

We define depth through background shifts. Avoid the "flat" look by nesting containers using the following progression:

- **Baseline:** `surface` (#10131a)

- **Primary Sections:** `surface_container_low` (#191c22)

- **Interactive Cards:** `surface_container` (#1d2026)

- **Popovers/Highlights:** `surface_container_highest` (#32353c)



### The "No-Line" Rule

**Prohibit 1px solid borders for sectioning.** Boundaries must be defined solely through color transitions. For example, a camera feed table should sit on a `surface_container_low` background, distinguished from the main `surface` by a tonal shift, not a line.



### The "Glass & Gradient" Rule

For floating action panels or tooltips, use **Glassmorphism**. Apply `surface_bright` at 60% opacity with a `backdrop-blur` of 12px. Main CTAs should utilize a subtle linear gradient from `primary` (#b8c3ff) to `on_primary_container` (#5877ff) to provide a "machined" metallic sheen.



---



## 3. Typography



The system utilizes a tri-font strategy to balance industrial precision with modern readability.



* **Display & Headlines (Manrope):** Used for high-level metrics and section headers. Manrope’s geometric balance provides an authoritative, editorial feel.

* **Navigation & UI Labels (Space Grotesk):** This monospaced-adjacent font is used for technical data, status labels, and camera IDs. It evokes a sense of "code" and engineering precision.

* **Body & Titles (Inter):** The workhorse for tables and long-form descriptions, ensuring maximum legibility at high information densities.



**Hierarchy Strategy:**

- **Display-LG (3.5rem):** For hero analytics (e.g., Total System Uptime).

- **Label-SM (0.6875rem):** For metadata inside camera tables, set in `on_surface_variant`.

- **Headline-SM (1.5rem):** Used for major module titles like "System Health" or "Daily Report."



---



## 4. Elevation & Depth



### The Layering Principle

Depth is achieved by "stacking" surface tiers. Place a `surface_container_lowest` element inside a `surface_container_high` section to create a "recessed" look, perfect for input fields or embedded charts.



### Ambient Shadows

When an element must float (e.g., a modal or context menu), use **Ambient Shadows**:

- **Blur:** 24px - 40px

- **Opacity:** 6% - 10%

- **Color:** Use a tinted shadow based on `primary_container` (#001252) rather than pure black to maintain the navy tonal depth.



### The "Ghost Border" Fallback

If accessibility requires a container edge, use a **Ghost Border**: `outline_variant` (#44474c) at **15% opacity**. This provides a hint of structure without interrupting the visual flow.



---



## 5. Components



### Camera Tables & Data Grids

- **Style:** Forbid horizontal dividers. Use a 2px vertical spacing shift (`spacing.0.5`) on hover using `surface_container_highest`.

- **Status Cells:** Use `tertiary` (#00e475) for "Healthy" and `error` (#ffb4ab) for "Issue" in a bold `label-md` weight.



### Buttons

- **Primary:** Gradient-fill (Primary to Primary-Container), `rounded-md`, `label-md` uppercase.

- **Secondary:** Ghost style. No background, `outline_variant` (20% opacity) border.

- **Action Chips:** Use `secondary_container` with `on_secondary_container` text. Keep corners at `rounded-full` for high contrast against rectangular tables.



### Input Fields

- **Container:** `surface_container_lowest` (#0b0e14).

- **Active State:** A 1px bottom-border only using `primary`. No full-box focus rings.

- **Typography:** Labels use `label-sm` in `outline`.



### Analytics Charts

- **Axis Lines:** Use `outline_variant` at 10% opacity.

- **Data Series:** Use `tertiary` for healthy trends and `secondary_fixed` for baseline data.



---



## 6. Do's and Don'ts



### Do

- **Do** use `spacing.8` (1.75rem) between major modules to create "breathing room" in dense layouts.

- **Do** use `tertiary_fixed` for small, high-priority notification dots.

- **Do** utilize `surface_dim` for background areas that are intentionally de-emphasized.



### Don't

- **Don't** use pure black (#000000) or pure white (#ffffff). Stick strictly to the defined tonal tokens.

- **Don't** use traditional "Drop Shadows" with 0 blur. It breaks the sophisticated industrial aesthetic.

- **Don't** use standard blue for links; use `primary` (#b8c3ff) to maintain the "Sentinel" color story.

- **Don't** crowd camera feeds. Ensure each feed container has a minimum padding of `spacing.4`.