# Multi-Frame Image Analysis Design

Date: 2026-04-05
Project: frigate_api_mcp
Status: Draft approved in chat, awaiting file review

## Goal

Refine image analysis so the system treats time-sequenced frames as first-class evidence instead of collapsing single-camera analysis into one merged image or relying on bounding boxes.

The new behavior should:
- send multiple raw frames for single-camera analysis as separate images in one LLM request
- send multiple per-second merged collages for group analysis as separate images in one LLM request
- remove bounding box generation and storage completely
- simplify the output labels to a small stable set
- show all evidence frames in photos, jobs, and reports instead of only one final image

## Final label set

All analysis paths return exactly one of:
- `working`
- `not_working`
- `no_person`
- `uncertain`

### Definitions
- `working`: a clearly visible person is actively engaged in productive physical work
- `not_working`: a person is visible but not actively working
- `no_person`: no clearly visible person is present
- `uncertain`: visibility is poor or evidence is too ambiguous to classify safely

## Desired behavior

### Single-camera analysis

Settings already define:
- `llm_frames_per_process`
- `llm_seconds_window`
- image resize/compression settings

New intended behavior:
1. Capture `llm_frames_per_process` frames from the same camera, approximately one second apart.
2. Keep those frames as separate image files.
3. Send all captured frames to the LLM in one request as a time sequence.
4. Prompt explicitly states that:
   - all frames are from the same camera
   - all frames show the same place
   - each frame is about one second apart
   - the model must analyze only what is directly visible
5. The model returns one final label, one confidence, and concise notes.
6. All raw frames used for inference are preserved as evidence and exposed through jobs, photos, and report/history views.

### Group analysis

New intended behavior:
1. For each second in the sequence, capture one frame from each camera in the group.
2. Merge only frames from the same second into one collage image with camera labels.
3. Repeat this for the full time window, producing one collage per second.
4. Send all collages to the LLM in one request as a time sequence.
5. Prompt explicitly states that:
   - each collage is one moment in time
   - each collage contains multiple labeled camera views
   - collages are about one second apart
6. The model returns one final label, one confidence, and concise notes.
7. The backend enforces the business rule: **if any visible camera in any collage clearly shows working, final group result must be `working`**.
8. All generated collages used for inference are preserved as evidence and exposed through jobs, photos, and report/history views.

## Decision rule for groups

The user-selected rule is:
- **Any working wins**

This should be implemented as application logic, not left only to prompt compliance.

### Why this must live in backend logic
- prompts are advisory, not authoritative
- a hard business rule should be deterministic
- this keeps group behavior stable across model changes

## Prompt design

## Single-camera prompt

The single-camera prompt should be rewritten around time-sequenced evidence.

Core instructions:
- act as a strict factory work-state auditor
- images are sequential frames from the same camera and same location
- frames are about one second apart
- analyze only directly visible evidence
- do not infer hidden workers or machine operation from context alone
- prefer `uncertain` over guessing
- return strict JSON only

Required JSON shape:
```json
{
  "label": "working|not_working|no_person|uncertain",
  "confidence": 0.0,
  "notes": "short reason"
}
```

Prompt guidance should include:
- `working`: person clearly visible and engaged in work
- `not_working`: person visible but inactive or not productively engaged
- `no_person`: no clearly visible person across the sequence
- `uncertain`: weak, blocked, blurred, or ambiguous evidence

### Recommended note style
Notes should be short and useful, for example:
- `activity seen in frames 2-3`
- `person visible but inactive across sequence`
- `no visible person in all frames`
- `visibility poor in all frames`

## Group prompt

The group prompt should be rewritten around per-second collages.

Core instructions:
- act as a strict factory work-state auditor
- each image is one merged collage representing one second in time
- each collage contains labeled camera sections
- collages are sequential in time
- classify from directly visible evidence only
- prefer `uncertain` over guessing
- return strict JSON only

Required JSON shape:
```json
{
  "label": "working|not_working|no_person|uncertain",
  "confidence": 0.0,
  "notes": "short reason"
}
```

Prompt should mention that if any camera clearly shows productive work in any collage, the correct result is `working`, but backend logic still remains the final authority.

## Data model and stored output

## Segment record

Keep `segments.evidence_path`, but redefine its meaning:
- it becomes the **primary evidence path** only
- for single-camera analysis, use the first captured frame
- for group analysis, use the first generated collage

This preserves compatibility with existing screens that expect one main image.

## raw_result shape

Store all evidence files explicitly in `jobs.raw_result`.

### Single-camera raw_result
```json
{
  "label": "working",
  "confidence": 0.91,
  "notes": "activity seen in frames 2-3",
  "frame_count": 3,
  "primary_evidence_path": "data/evidence/frames/cam_x/frame_0.jpg",
  "evidence_frames": [
    "data/evidence/frames/cam_x/frame_0.jpg",
    "data/evidence/frames/cam_x/frame_1.jpg",
    "data/evidence/frames/cam_x/frame_2.jpg"
  ]
}
```

### Group raw_result
```json
{
  "label": "working",
  "confidence": 0.88,
  "notes": "activity visible in camera A during collage 2",
  "frame_count": 3,
  "primary_evidence_path": "data/evidence/groups/group_x/frame_0_collage.jpg",
  "evidence_frames": [
    "data/evidence/groups/group_x/frame_0_collage.jpg",
    "data/evidence/groups/group_x/frame_1_collage.jpg",
    "data/evidence/groups/group_x/frame_2_collage.jpg"
  ],
  "included_cameras": ["cam_a", "cam_b", "cam_c"],
  "missing_cameras": []
}
```

### Compatibility note
Existing `frame_paths` fields should be replaced by or normalized to `evidence_frames` so the API and UI have one canonical field.

## Removed features

The following should be removed entirely:
- `boxes` in prompts
- `boxes` in response parsing
- bounding box normalization logic
- annotated image generation
- box overlay rendering paths
- annotation-based evidence generation

### Why remove them
- they add complexity without value for this workflow
- they imply precision the user does not want
- they distort the evidence pipeline around a feature no longer needed

## Pipeline changes

## Single-camera processing

Current flow sends separate frames when multiple frames exist, but still creates annotated evidence images and stores box data.

Target flow:
1. collect frames
2. optionally resize/compress frames
3. save raw frames
4. send raw frames directly to the LLM
5. store final label/confidence/notes
6. store all raw frames as evidence
7. set segment primary evidence to the first frame
8. do not create strips for inference
9. do not create annotations

### Important implementation note
If only one frame is requested, still store it through the same evidence model so UI/API behavior stays consistent.

## Group processing

Current flow already generates one collage per frame index across cameras, which aligns with the intended design.

Target flow:
1. collect per-camera frames for the full sequence
2. build one labeled collage for each second
3. send all collages to the LLM
4. apply `any working wins` in backend logic
5. store all collages as evidence
6. set segment primary evidence to the first collage
7. do not annotate collages

## API/UI changes

## API

`/api/evidence/{segment_id}` should expose:
- `segment_id`
- `evidence_path` (primary path for compatibility)
- `evidence_frames` (all evidence images used for inference)

If helpful for migration, the API can temporarily return both `frame_paths` and `evidence_frames`, but the UI should move to `evidence_frames` as the primary field.

## Photos view

Desired behavior:
- photo card may still show one primary thumbnail for fast browsing
- photo modal/gallery must show **all evidence frames** for the segment
- single-camera segments show all raw frames
- group segments show all per-second collages

## Jobs view

Desired behavior:
- job detail should expose all evidence images used in the run
- not only one snapshot path

## Reports / history / efficiency

Desired behavior:
- retain one primary preview where compact display is needed
- provide access to the full evidence set for the segment/job

## Error handling

### Partial single-camera capture failure
- if at least one frame succeeded, continue using available frames
- note missing frames in `notes` or structured metadata
- if all frames fail, fail the job

### Partial group capture failure
- if some cameras fail but at least one camera contributes evidence, continue
- record `missing_cameras`
- if all cameras fail for the whole job, fail the job

### Sequence imbalance
If different cameras produce different frame counts, normalize to the intended sequence length in a predictable way. The implementation should prefer deterministic behavior and record any fallback behavior in logs or metadata.

## Testing requirements

### Single-camera tests
- verify multiple frames are sent as separate images in one request
- verify no merged strip is used for inference
- verify returned labels are limited to the 4-label set
- verify no `boxes` field is required or stored
- verify all evidence frames are stored and exposed

### Group tests
- verify one collage is built per second across cameras
- verify all collages are sent in order
- verify backend enforces `any working wins`
- verify missing cameras are captured in result metadata
- verify all evidence collages are stored and exposed

### UI/API tests
- verify `/api/evidence/{segment_id}` returns all evidence frames
- verify photo modal/gallery renders all images for a segment
- verify jobs/report/history screens can access full evidence arrays
- verify old annotation assumptions no longer exist

## Implementation impact areas

Likely files to update:
- `factory_analytics/integrations/ollama.py`
- `factory_analytics/services.py`
- `factory_analytics/image_annotations.py` (remove usage, possibly remove file)
- `factory_analytics/main.py`
- `factory_analytics/static/photos.js`
- jobs/history/report-related UI files that currently assume a single evidence image
- tests covering image analysis, evidence API, and UI behavior

## Recommended rollout

1. simplify LLM output contract and remove boxes
2. update single-camera evidence storage to keep raw frames only
3. update group evidence storage to keep raw collages only
4. add canonical `evidence_frames` API output
5. update UI to render full evidence sets
6. remove dead annotation code

## Out of scope

This design does not add:
- person counting
- per-frame labels in the final public API
- per-camera group sub-results in the public API
- object detection or localization
- new analytics dimensions beyond the 4-label set

## Open decisions resolved in chat

- final label set: `working`, `not_working`, `no_person`, `uncertain`
- group rule: `any working wins`
- evidence display: show all separate frames, not a single merged result
- bounding boxes: remove completely

## Summary

This design keeps the current multi-frame/group foundation but makes evidence handling match the actual operator workflow:
- separate frames for single-camera time sequences
- one merged collage per second for groups
- deterministic group decision rule in backend
- no bounding boxes
- all evidence visible across the product
