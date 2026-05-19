## AND-102 Task 7: Executive Report

**Prepared for:** Rocket Elevators Operations Team
**Date:** 2026-05-19
**Author:** Charles Winfield

---

## 1. Data Integration Summary

Four Ontario elevator datasets were unified into a single fleet record using `ElevatingDevicesNumber` as the common join key across all merges.

| Merge | Datasets | Method | Result |
|---|---|---|---|
| 1 | license.csv + installed.json | Inner join | 43,251 rows |
| 2 | + altered.json | Left join (aggregated) | 43,251 rows |
| 3 | + inspection.csv | Left join (most recent only) | 43,251 rows |

**Final dataset:** `data/merged_elevator_data.csv` — 43,251 rows × 25 columns

### Key Decisions

**Province mismatch filter:** 46 rows were dropped at Merge 1 because the province extracted from the license address disagreed with the province in the installed record. A province disagreement indicates two records describing different physical locations rather than a formatting difference — these rows were too unreliable to carry forward.

**Inspection flattening:** The raw inspection file contained 143,181 rows — approximately 3.3 inspections per elevator on average, with a maximum of 24 per device. Joining all inspection rows would have multiplied the dataset more than three times over, making one-elevator-per-row analysis impossible. Only the most recent inspection per elevator was retained, reducing 143,181 rows to 40,954 before joining.

### Data Quality Issues

- **3,429 elevators (7.9% of the fleet) have no inspection record.** These devices exist in the license and installation data but have never appeared in the inspection system.
- **51 elevators (0.1%) have 5 or more alteration records,** which may indicate chronic mechanical issues or active upgrade programs worth monitoring separately.

---

## 2. Incident Analysis Findings

**2,445 incident narratives** from `data/incident.json` were analyzed using TF-IDF vectorization and K-Means clustering (scikit-learn, k=5). Narratives were cleaned — lowercased, punctuation removed, stop words filtered, lemmatization applied — before clustering.

### Incident Type Breakdown

| Incident Type | Count | Share |
|---|---|---|
| General Injuries & Falls | 908 | 37.1% |
| Door Strike Injuries | 567 | 23.2% |
| Hoistway Water Damage | 363 | 14.8% |
| Level Misalignment & Trip Hazards | 311 | 12.7% |
| Pit Flooding & Sump Pump Failure | 296 | 12.1% |

![Incident Type Distribution](../assets/incident_topic_distribution.png)

### Key Patterns

**Door strikes are the most preventable category.** At 567 incidents (23% of all reports), door strikes — passengers hit, caught, or pinched by closing doors — represent a concentrated mechanical failure point. Unlike falls or water damage, which have diverse root causes, door strikes point to a single system: door sensors.

**Water intrusion is the largest systemic risk.** Hoistway Water Damage (363) and Pit Flooding & Sump Pump Failure (296) together account for 659 incidents — 27% of all reported events. Combined, water-related incidents outpace any individual injury category. Most people think of elevators as a personal-safety risk; the data shows infrastructure damage is equally prevalent.

**Level misalignment is both common and fully preventable.** 311 incidents involved elevators stopping above or below the floor threshold, directly causing passenger trips and falls. This is a calibration fault that routine maintenance can eliminate.

---

## 3. Token Cost Analysis

Session costs were captured using the Claude Code statusbar (`scripts/statusline.sh`), which reports real-time token usage and cost against the Anthropic API.

### Session Comparison

| Session | Task | Turns | Input Tokens | Cost | Context % |
|---|---|---|---|---|---|
| Task 6 NLP analysis | Clustering + chart + summary | Multi-turn | 27,089 | **$0.2129** | 14% |
| ETL summary session | 3 prompts reading etl_pipeline.ipynb | 3 | 42,418 | **$0.6428** | 21% |

### Which Session Was Most Expensive and Why

The 3-prompt ETL summary session ($0.6428) cost **3× more** than the full multi-turn Task 6 NLP session ($0.2129), despite fewer turns. The reason is input token volume: reading `intelligence/etl_pipeline.ipynb` — a notebook containing the full output of merging four datasets — loaded 42,418 input tokens in a single pass. This demonstrates that **session cost is driven primarily by context size, not turn count.** A single prompt that reads a large file can cost more than a dozen prompts that operate on small text.

### Cost-Reducing Action: Subagent Delegation

During Task 6, a subagent was launched to compare LDA vs TF-IDF + K-Means before any library decision was made. The research — including library documentation, co-occurrence explanations, and comparison tables — was confined to the subagent's isolated context. Only the recommendation returned to the main session. This kept the main session's input token count at 27,089 rather than the ~42k+ that a full in-session exploration would have required, directly reducing the Task 6 session cost.

---

## 4. Recommendations

**1. Launch a door sensor audit program.**
Door strikes account for 567 incidents — 23% of all reported events — and represent the most concentrated, addressable failure point in the dataset. A targeted audit of door sensor calibration and replacement schedules across the fleet would directly reduce the second-largest incident category. Given the volume, even a 30% reduction would eliminate ~170 incidents per year.

**2. Establish a water intrusion inspection protocol.**
Water-related incidents (pit flooding + hoistway damage) collectively represent 27% of all reports, yet sump pump failure and hoistway waterproofing are not typically surfaced in standard safety inspections. A dedicated annual water intrusion check — particularly for older buildings and basement-level pits — should be added to the inspection checklist.

**3. Prioritize inspection coverage for the 3,429 unrecorded elevators.**
Nearly 8% of the fleet has no inspection record in the system. Whether this reflects data entry gaps or genuinely uninspected devices, the operations team cannot verify compliance or safety status for these elevators. A reconciliation campaign to confirm inspection status for this cohort should be treated as a compliance priority before the next regulatory review.
