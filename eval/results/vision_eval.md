# Vision Depth Evaluation

Model: `qwen/qwen3.8-27b` (Groq). 29 labelled photos from `test_media/`. Tiers use the Safety Guardrail thresholds (P1 > 100 cm, P2 >= 50, P3 >= 20, P4 below). **Incomplete: 1 answer(s) not yet obtained (daily API quota): V2 03_severe_submerged_120cm.jpg.**

| Prompt | JSON valid | Depth given | In labelled range | Mean error (cm) | Underestimates | Tier accuracy | Dangerous misses (P1 graded P3/P4/none) |
|---|---|---|---|---|---|---|---|
| V1 | 100% | 100% | 21% | 15.2 | 55% | 38% | 0 |
| V2 | 100% | 96% | 25% | 12.4 | 29% | 39% | 0 |

## Per image

| Prompt | Image | Label (cm) | Expected | Estimate (cm) | Predicted | Confidence | Anchor |
|---|---|---|---|---|---|---|---|
| V1 | test_media\imagess\10-15\10-15-1.jpg | 10-15 | P4 | 45.0 | P3 | medium | car tyre |
| V1 | test_media\imagess\10-15\10-15.jpg | 10-15 | P4 | 45.0 | P3 | medium | human leg |
| V1 | test_media\imagess\10-15\images (1).jpg | 10-15 | P4 | 20.0 | P3 | medium | human leg |
| V1 | test_media\imagess\10-15\images (2).jpg | 10-15 | P4 | 25.0 | P3 | medium | human leg |
| V1 | test_media\imagess\10-15\images (3).jpg | 10-15 | P4 | 15.0 | P4 | high | human ankle |
| V1 | test_media\imagess\10-15\images (4).jpg | 10-15 | P4 | 15.0 | P4 | medium | human foot |
| V1 | test_media\imagess\10-15\images (5).jpg | 10-15 | P4 | 30.0 | P3 | medium | car tyre |
| V1 | test_media\imagess\10-15\images (6).jpg | 10-15 | P4 | 5.0 | P4 | medium | pedestrian leg |
| V1 | test_media\imagess\10-15\images (7).jpg | 10-15 | P4 | 60.0 | P2 | high | car tyre |
| V1 | test_media\imagess\10-15\images.jpg | 10-15 | P4 | 25.0 | P3 | medium | door frame |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (2).jpg | 35-45 | P3 | 45.0 | P3 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (3).jpg | 35-45 | P3 | 45.0 | P3 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (4).jpg | 35-45 | P3 | 25.0 | P3 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (5).jpg | 35-45 | P3 | 30.0 | P3 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (6).jpg | 35-45 | P3 | 25.0 | P3 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (8).jpg | 35-45 | P3 | 10.0 | P4 | high | car tyre |
| V1 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images.jpg | 35-45 | P3 | 30.0 | P3 | high | car tyre |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (2).jpg | 100-200 | P1 | 80.0 | P2 | high | car tyre |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (3).jpg | 100-200 | P1 | 60.0 | P2 | high | car door |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (4).jpg | 100-200 | P1 | 60.0 | P2 | high | car door |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (5).jpg | 100-200 | P1 | 80.0 | P2 | medium | human torso |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (6).jpg | 100-200 | P1 | 60.0 | P2 | medium | car door |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (7).jpg | 100-200 | P1 | 120.0 | P1 | medium | human torso |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images.jpg | 100-200 | P1 | 90.0 | P2 | medium | car door |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images3.jpg | 100-200 | P1 | 90.0 | P2 | medium | car roof |
| V1 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\téléchargement.jpg | 100-200 | P1 | 60.0 | P2 | medium | car door |
| V1 | test_media\images\01_shallow_ankle_15cm.jpg | 10-20 | P4 | 20.0 | P3 | high | human leg |
| V1 | test_media\images\02_moderate_wheel_40cm.jpg | 35-45 | P3 | 30.0 | P3 | high | car tyre |
| V1 | test_media\images\03_severe_submerged_120cm.jpg | 110-130 | P1 | 100.0 | P2 | medium | car roof |
| V2 | test_media\imagess\10-15\10-15-1.jpg | 10-15 | P4 | 35.0 | P3 | medium | adult shin/knee |
| V2 | test_media\imagess\10-15\10-15.jpg | 10-15 | P4 | 70.0 | P2 | medium | adult mid-thigh |
| V2 | test_media\imagess\10-15\images (1).jpg | 10-15 | P4 | 30.0 | P3 | medium | adult shin / child knee |
| V2 | test_media\imagess\10-15\images (2).jpg | 10-15 | P4 | 30.0 | P3 | medium | adult shin/knee |
| V2 | test_media\imagess\10-15\images (3).jpg | 10-15 | P4 | 25.0 | P3 | high | adult ankle/shin |
| V2 | test_media\imagess\10-15\images (4).jpg | 10-15 | P4 | 25.0 | P3 | high | adult shin/calf |
| V2 | test_media\imagess\10-15\images (5).jpg | 10-15 | P4 | 15.0 | P4 | medium | adult ankle |
| V2 | test_media\imagess\10-15\images (6).jpg | 10-15 | P4 | - | - | high | - |
| V2 | test_media\imagess\10-15\images (7).jpg | 10-15 | P4 | 48.0 | P3 | high | car wheel hub |
| V2 | test_media\imagess\10-15\images.jpg | 10-15 | P4 | 25.0 | P3 | medium | adult shin (person in background) |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (2).jpg | 35-45 | P3 | 75.0 | P2 | medium | car wheel hub / car door |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (3).jpg | 35-45 | P3 | 90.0 | P2 | high | car bumper / taillight |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (4).jpg | 35-45 | P3 | 25.0 | P3 | high | car wheel hub |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (5).jpg | 35-45 | P3 | 70.0 | P2 | medium | car door handle |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (6).jpg | 35-45 | P3 | 32.0 | P3 | high | car wheel hub |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images (8).jpg | 35-45 | P3 | 32.0 | P3 | high | car wheel hub |
| V2 | test_media\imagess\(Moderate  Car Wheels)depth 35–45 cm\images.jpg | 35-45 | P3 | 42.0 | P3 | high | car wheel hub |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (2).jpg | 100-200 | P1 | 120.0 | P1 | medium | car door handle |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (3).jpg | 100-200 | P1 | 95.0 | P2 | high | car door handle |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (4).jpg | 100-200 | P1 | 115.0 | P1 | high | car door handle / side mirror |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (5).jpg | 100-200 | P1 | 115.0 | P1 | medium | adult chest |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (6).jpg | 100-200 | P1 | 95.0 | P2 | high | car door handle |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images (7).jpg | 100-200 | P1 | 95.0 | P2 | medium | ground-floor window sill |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images.jpg | 100-200 | P1 | 150.0 | P1 | high | car roof |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\images3.jpg | 100-200 | P1 | 150.0 | P1 | high | car roof |
| V2 | test_media\imagess\Photo 3 (Severe  Critical)  depth  100 cm\téléchargement.jpg | 100-200 | P1 | 70.0 | P2 | medium | car bumper / lower door |
| V2 | test_media\images\01_shallow_ankle_15cm.jpg | 10-20 | P4 | 22.0 | P3 | medium | adult ankle |
| V2 | test_media\images\02_moderate_wheel_40cm.jpg | 35-45 | P3 | 32.0 | P3 | high | car wheel hub |
