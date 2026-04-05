# UI Model Visibility and Heatmap Details Design

**Goal:** Show model names on every relevant list/card view and make Activity Heatmap clicks reveal a usable per-segment list with thumbnails and a path into full job details.

## Scope

This design covers four existing UI surfaces:
- `Efficiency` page heatmap interaction
- `Reports` page visible rows/cards
- `Photos` page cards
- `Jobs` page rows

It does not introduce a new global drawer system or redesign page navigation.

## User-visible behavior

### 1. Efficiency heatmap square click

Clicking any Activity Heatmap square opens a detail panel anchored to the current interaction pattern.

If the square represents one segment, the panel shows a single segment entry.
If the square represents multiple segments, the panel shows a list of segment entries.

Each segment entry contains:
- camera name
- classification label
- confidence
- timestamp / duration summary
- first evidence frame thumbnail only
- model name used for analysis
- **Open Job Details** button

The **Open Job Details** button opens the existing job details view, which remains the canonical full-inspection surface.

### 2. Model names on every row/card

Model name must be visible directly in:
- every relevant `Reports` row/card
- every `Photos` card
- every `Jobs` row

Model name is not limited to a detail modal.

If model metadata is unavailable for a row/card, render `-`.

### 3. Full job details

The job details view remains the place for:
- full request payload
- full response payload
- all evidence images / frames
- model used

The new efficiency list links into this existing flow rather than duplicating the full gallery inline.

## Architecture

### Backend

Backend list APIs should expose display-ready `model_used` values so the frontend does not need separate lookup calls per item.

Required principle:
- list endpoints return enough data for row/card display
- detail endpoints return full payloads and galleries

### Data sourcing

`model_used` should be derived from the linked job/result data, using the same normalization strategy already applied on the jobs API.

The following list/data providers should include `model_used` in their payloads where applicable:
- jobs list
- segment/history-style list data used by efficiency heatmap drilldown
- photo list data
- reports list/card data

### Frontend

Keep each page in its current structure.

Add minimal rendering changes only:
- `Efficiency`: richer segment list in the existing click detail flow
- `Reports`: append model label to visible row/card metadata
- `Photos`: append model label to card metadata
- `Jobs`: keep model column visible in every row

No new shared component framework is required for this scope.

## Efficiency detail panel design

The heatmap click result should render a compact list.

Each row in that list should:
- be visually scannable
- show first-frame thumbnail
- show model name inline
- include an explicit action button to open full job details

If a segment has no evidence image, show a neutral placeholder instead of leaving the area blank.

If job details fail to load, keep the list intact and show the error only in the job detail modal.

## Data flow

### Efficiency
1. User clicks heatmap square.
2. Frontend resolves the square metadata to one or more segments.
3. Frontend renders a segment list.
4. Each list item shows its `model_used` and first thumbnail.
5. Clicking **Open Job Details** loads the existing job detail modal/page for that item.

### Reports / Photos / Jobs
1. Existing list endpoint loads data.
2. Each item already includes or is extended to include `model_used`.
3. Frontend renders model name inline in every row/card.

## Testing

### API tests
Add focused tests that verify `model_used` is present in the relevant list payloads:
- jobs list
- photo list
- any segment/report list payload used by efficiency/report UIs

### UI tests
Add focused UI/source tests that verify:
- jobs rows render model name
- photos cards render model name
- reports rows/cards render model name
- efficiency drilldown markup includes model display and job-detail action hooks

### Interaction tests
Add at least one test covering the multi-segment heatmap case to verify the detail UI is list-oriented rather than assuming a single segment.

## Edge cases

- Missing model metadata → show `-`
- Single segment square → same component with one row
- Multiple segment square → list rendering
- Missing image → placeholder thumbnail area
- Missing job detail payload → show modal error state without breaking the list

## Out of scope

- brand new navigation model
- global shared drawer refactor
- full visual redesign of efficiency/reports/photos/jobs pages
- changing the semantics of model naming beyond exposing and displaying the stored value
