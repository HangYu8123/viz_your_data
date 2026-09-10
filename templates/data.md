# data.md — what to parse and what we expect to find

<!-- One section per data source. The "expected outcome" lines let the parser be sanity-checked. -->

## Directory layout
<!-- e.g.
data/<participant_id>_<YYYYMMDD_HHMMSS>/
  rosbag/          ROS 2 bag (mcap or db3)
  video.mp4        screen + webcam recording
  audio.wav
questionnaires/*.csv
Explain how participant id, condition, and trial are encoded in paths or file contents. -->

## Source 1: <name>
- **Files / glob:**
- **Format:** <!-- rosbag2 topics, CSV columns, JSON schema, etc. List topic names and message types if ROS. -->
- **Fields that matter:** <!-- name → meaning → unit -->
- **How to derive the metrics in goal.md from it:**
- **Known quirks:** <!-- clock resets, missing trials, a corrupted session to skip, etc. -->
- **Expected outcome:** <!-- e.g. "about 3–8 interventions per trial; condition C1 should be highest" -->

## Source 2: <name>
- **Files / glob:**
- **Format:**
- **Fields that matter:**
- **How to derive metrics:**
- **Known quirks:**
- **Expected outcome:**

## Mapping tables
<!-- Where condition order / participant assignment lives (a CSV, a spreadsheet, or inline here). -->

## Exclusions
<!-- Sessions or participants to drop, and why. -->
