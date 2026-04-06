# History Segment Detail Design

**Goal:** Fix the History page so model names render reliably, all evidence thumbnails render inline for each segment, and each capture event has a dedicated detail page at `/history/{segment_id}` with full segment details.

## Scope

This design covers the History surface only:
- `/history` list rendering
- `/api/history/segments` payload usage on the list page
- `/history/{segment_id}` as a new detail page
- `/api/history/segments/{segment_id}` payload completeness for the detail page

It does not redesign the rest of the app, replace the current History table with a client-side app, or introduce modal-based detail inspection.

## User-visible behavior

### 1. History list page

The History page remains the summary/list surface.

Each row should show:
- segment id
- camera name
- model name
- classification label using `reviewed_label` when present, otherwise `label`
- confidence
- start and end timestamps
- notes / LLM response summary
- group badge when applicable
- review actions
- all available evidence thumbnails inline

If a segment has multiple `evidence_frames`, all thumbnails should render inline in the Visual Evidence column.

If a segment has no `evidence_frames` but does have `evidence_path`, render that single image as the fallback.

If neither exists, render the existing neutral placeholder state.

Each row should also provide a clear path to `/history/{segment_id}` for full inspection.

### 2. History segment detail page

A new server-rendered route at `/history/{segment_id}` becomes the canonical per-capture inspection surface.

The page should render one segment in clearly separated sections and include all relevant available details:
- segment identity
- camera metadata
- group metadata when present
- model used
- job id and job type
- label and reviewed label
- confidence
- start and end timestamps
- notes / LLM response
- primary evidence image
- complete evidence frame gallery
- review note and review actor
- raw result / raw metadata when present

Missing values should render as `-` or a neutral empty state rather than disappearing silently.

## Architecture

### Backend

Keep the existing History APIs as the data source:
- `/api/history/segments`
- `/api/history/segments/{segment_id}`

The list endpoint should return enough data for the History table to render all row-level metadata, including `model_used` and the full `evidence_frames` array when available.

The detail endpoint should return enough data for `/history/{segment_id}` to render the full per-segment inspection page without requiring multiple follow-up fetches to other endpoints.

If any required field is missing today, extend the backend query or normalization in the segment detail path rather than compensating with fragile frontend stitching.

### Frontend

Keep the existing server-rendered page structure.

For `/history`:
- keep the existing table layout
- update the evidence cell rendering to show all thumbnails inline
- preserve fallback behavior for missing imagery
- add a detail-navigation affordance per row

For `/history/{segment_id}`:
- add a new dedicated template
- prefer rendering from the route context directly
- keep client-side logic minimal and only use JS if needed for small presentation behavior

No global component abstraction or UI framework migration is needed for this scope.

## Root-cause investigation targets

Before implementation, verify these specific failure points:

1. Whether `/api/history/segments` already includes `model_used` and the UI is failing to render it correctly.
2. Whether the list payload already contains `evidence_frames` for multi-image segments.
3. Whether current History rendering logic is only showing one image because it collapses the array or falls back too early.
4. Whether `/api/history/segments/{segment_id}` already includes all fields needed for a detail page, or whether backend expansion is required.

The fix should address whichever layer is actually dropping the data rather than adding symptom-only UI patches.

## Data flow

### History list
1. User opens `/history`.
2. Frontend loads `/api/history/segments`.
3. Each segment row renders summary metadata from that payload.
4. Visual Evidence renders every image from `evidence_frames` when present.
5. Row detail action opens `/history/{segment_id}`.

### Segment detail page
1. User opens `/history/{segment_id}`.
2. Server route resolves the segment detail payload.
3. Template renders the full segment inspection view from that payload.
4. Evidence images render as a gallery, with the primary evidence image shown when available.

## Testing

### Backend tests
Add focused tests to verify:
- History segment list payload includes `model_used`
- History segment list payload preserves `evidence_frames` arrays
- History segment detail payload includes fields required by the detail page

### UI/source tests
Add focused tests to verify:
- History template contains hooks for rendering all evidence thumbnails inline
- History template contains navigation hooks to the new detail route
- History detail template renders key metadata fields including model, notes, timestamps, evidence, and review data

### Route tests
Add tests that verify:
- `/history` renders successfully
- `/history/{segment_id}` renders successfully for an existing segment
- missing segment ids return 404

## Edge cases

- Missing model metadata → render `-`
- Missing `evidence_frames` with present `evidence_path` → render fallback single image
- Missing all imagery → render placeholder state
- Segment has many frames → render all inline thumbnails on list page, bounded by existing layout styling
- Missing notes / raw metadata / review info → render neutral empty states
- Unknown segment id → return 404

## Out of scope

- modal-based detail inspection
- rewriting History into a SPA
- redesigning unrelated pages
- changing review workflow semantics
- changing how model names are generated beyond exposing and rendering the stored value
