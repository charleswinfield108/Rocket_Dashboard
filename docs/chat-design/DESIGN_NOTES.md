# REMI Chat Widget — Design Iterations

Designed in Claude Design (claude.ai/design). Both versions show the collapsible chat panel fixed to the bottom-right of the operations dashboard.

## Version 1 — design-v1.png

Initial design. Key decisions:
- Dark navy header with REMI name, "R" avatar badge, and green online indicator ("Monitoring 47 units")
- Collapse chevron in top-right of header
- Opening message from REMI sets context immediately
- Timestamp shown under the opening message
- Four quick-action chips below the message: Active alerts, Units offline, Maintenance due, Site overview
- Light grey input bar at the bottom with placeholder "Ask about a unit, site, or alert..."
- Paper-plane send button in muted blue

## Version 2 — design-v2.png

Refined version. Changes from v1:
- Removed the code/JSX editor chrome — cleaner preview
- Chips reorganised to a 2×2 grid (Active alerts, Units offline / Maintenance due, Site overview)
- Slightly more compact layout with tighter spacing between chips
- Same header, same input bar — core identity preserved

## Design Decisions

- **Navy header** (#1e3a5f range): matches Rocket Elevators brand palette used in the dashboard
- **Quick-action chips**: give first-time users an immediate entry point without needing to know what to type
- **"Monitoring N units" subtitle**: reinforces that REMI is connected to real fleet data
- **Collapsed by default**: chat panel does not cover dashboard content on load; user opens it via FAB
