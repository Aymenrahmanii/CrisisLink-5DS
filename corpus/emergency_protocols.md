# CrisisLink Flood Response Protocols

Knowledge base for the CrisisLink Master Triage Agent. Each section states its source. Sections marked **CrisisLink doctrine** are rules defined by the project team (Week 1 Milestone Pack) and are not official guidance; every other section quotes or converts official public guidance. Depths are given in centimetres (1 inch = 2.54 cm, rounded).

Sources:
- [S1] US National Weather Service, "Turn Around Don't Drown": https://www.weather.gov/safety/flood-turn-around-dont-drown
- [S2] US National Weather Service, "Flood Safety: During a Flood": https://www.weather.gov/safety/flood-during
- [S3] FEMA / Ready.gov, "Floods": https://www.ready.gov/floods
- [S4] Australian Institute for Disaster Resilience, Guideline 7-3 "Flood Hazard" (2017), Tables 1-2 and Figures 8-10: https://knowledge.aidr.org.au/media/3518/adr-guideline-7-3.pdf
- [S5] US Centers for Disease Control and Prevention, "Flood Safety": https://www.cdc.gov/floods/safety/index.html
- [S6] Wikipedia, "Swift water rescue" (rescue hierarchy): https://en.wikipedia.org/wiki/Swift_water_rescue
- [S7] FEMA NIMS 508, "Swiftwater/Flood Search and Rescue Team" resource typing: https://www.fema.gov/sites/default/files/2020-08/fema_swiftwater-flood-sar-team_definition_08-03-2020.pdf
- [S8] Office National de la Protection Civile (Tunisia), recommendations relayed by Tuniscope, 18 Sept 2026: https://www.tuniscope.com/article/440299/actualites/tunisie/pluies-405311
- [S9] CrisisLink Week 1 Milestone Pack (project document, team doctrine)
- [S10] Jaslow et al. (2019), "A New Strategy for Swiftwater Rescue from Roadways during Urban and Small Stream Flash Flooding", Prehospital and Disaster Medicine: https://www.cambridge.org/core/journals/prehospital-and-disaster-medicine/article/new-strategy-for-swiftwater-rescue-from-roadways-during-urban-and-small-stream-flash-flooding/1A5DE66B55943C2F8F69CDE14A34934C

## 1. Priority Classification Matrix (P1 to P4)

Category: priority_matrix. Source: [S9] CrisisLink doctrine.

Every incident receives exactly one operational tier. When several rows apply, the most severe tier wins.

| Tier | Name | Definition | Trigger conditions |
|---|---|---|---|
| P1 | Critical / Immediate | Life-threatening | Water depth above 100 cm; trapped elderly people, infants, injured, sick, pregnant or disabled persons at any depth; people in moving water |
| P2 | High / Urgent | Rapidly worsening | Water depth 50-100 cm; rapidly rising or moving water; stranded vehicles with people inside |
| P3 | Moderate / Secondary | Localized impact | Roadway water 20-50 cm; localized property damage; nobody trapped |
| P4 | Low / Monitoring | Watch status | Pavement flooding below 20 cm; drainage still working |

### 1.1 Hard safety rules

- A report with water deeper than 80 cm is never classified below P2, even if the caller sounds calm.
- A trapped vulnerable person (elderly, infant, child, injured, sick, pregnant, disabled) is always P1, whatever the depth.
- When the photo and the voice report contradict each other, or the report may be a prank, the incident is escalated to a human operator instead of being dispatched automatically.

## 2. Rescue Asset Allocation by Tier

Category: rescue_assets. Source: [S9] CrisisLink doctrine, informed by [S7] and [S10].

| Tier | Primary rescue asset | Why |
|---|---|---|
| P1 | Inflatable Rescue Boat (Zodiac) / Helicopter Hoist | Water above 100 cm makes vehicles unsafe; boat-based or air rescue is required |
| P1 (trapped vulnerable person) | Inflatable Rescue Boat (Zodiac) + Paramedic Team | Medical care is needed on site for the elderly, infants, the injured or the sick |
| P2 | High-Clearance 4x4 Tactical Rescue Vehicle | 50-100 cm water can still be crossed by high-clearance rescue vehicles; small cars float |
| P3 | Tow Trucks / Road Closure Barricades | 20-50 cm water stalls passenger cars; the priority is closing roads and removing vehicles |
| P4 | Patrol Unit / Monitoring Drone | Below 20 cm: monitor drainage and issue a public advisory |

Assets escalate with the tier: a P1 incident must never be assigned a P2, P3 or P4 asset.

## 3. Water Depth Effects on People and Vehicles

Category: hazard_thresholds. Source: [S1], [S2], [S3].

| Depth (moving water) | Effect | Source |
|---|---|---|
| 15 cm (6 inches) | Can knock an adult off their feet | [S1], [S2], [S3] |
| 30 cm (12 inches) | Can float a car or small SUV; carries away most cars | [S1], [S2] |
| 45 cm (18 inches) | Can carry away large vehicles | [S2] |
| 60 cm (2 feet) | Rushing water can carry away SUVs and trucks | [S1] |

"It is NEVER safe to drive or walk into flood waters." [S1] Over half of all flood-related drownings involve vehicles driven into hazardous flood water; the next highest share comes from people walking into or near flood water. [S1]

## 4. Flood Hazard Vulnerability Classification (H1 to H6)

Category: hazard_thresholds. Source: [S4] AIDR Guideline 7-3, Tables 1 and 2.

The classification combines water depth (D, metres) and velocity (V, metres per second). A location belongs to the lowest class whose three limits are all respected.

| Class | Description | D x V limit (m2/s) | Depth limit (D) | Velocity limit (V) |
|---|---|---|---|---|
| H1 | Generally safe for vehicles, people and buildings | D x V <= 0.3 | 0.3 m (30 cm) | 2.0 m/s |
| H2 | Unsafe for small vehicles | D x V <= 0.6 | 0.5 m (50 cm) | 2.0 m/s |
| H3 | Unsafe for vehicles, children and the elderly | D x V <= 0.6 | 1.2 m (120 cm) | 2.0 m/s |
| H4 | Unsafe for vehicles and people | D x V <= 1.0 | 2.0 m (200 cm) | 2.0 m/s |
| H5 | Unsafe for vehicles and people; all buildings vulnerable to structural damage; some less robust buildings vulnerable to failure | D x V <= 4.0 | 4.0 m | 4.0 m/s |
| H6 | Unsafe for vehicles and people; all building types considered vulnerable to failure | D x V > 4.0 | - | - |

### 4.1 People, vehicle and building stability

- People stability (after Cox et al. 2010): limiting depths differ for children and for adults in good conditions, and a lower recommended working limit applies to trained adults working in floodwater. Hazard for adults rises from low to extreme as depth x velocity increases through 0.4, 0.6, 0.8 and 1.2 m2/s. [S4, Figure 8]
- Vehicle stability (after Shand et al. 2011): separate limits apply to small cars, large cars and large 4WD vehicles; beyond them there is extreme hazard for all non-specialty vehicles. [S4, Figure 9]
- Building stability (after Smith et al. 2014): light structures have a lower recommended maximum depth x velocity than all other structures. [S4, Figure 10]

### 4.2 Mapping hazard classes to CrisisLink tiers

Category: priority_matrix. Source: [S9] CrisisLink doctrine, derived from [S4].

| Hazard class | Still-water depth | CrisisLink tier |
|---|---|---|
| H1 | below 30 cm | P4 (below 20 cm) or P3 (20-30 cm) |
| H2 | 30-50 cm | P3 |
| H3 | 50-120 cm | P2, or P1 above 100 cm or when children or the elderly are present |
| H4 to H6 | above 120 cm | P1 |

## 5. Estimating Depth from a Photo: Reference Anchors

Category: visual_reference. Source: CrisisLink field reference (approximate typical heights, not official measurements).

| Reference object | Typical height above ground |
|---|---|
| Street curb | 15 cm |
| Adult ankle | 10-15 cm |
| Car wheel hub (centre of the wheel) | 30-35 cm |
| Top of car tyre / car bumper | 50-65 cm |
| Adult knee | 50 cm |
| Car door handle / bonnet | 90-100 cm |
| Adult waist / house door handle / ground-floor window sill | 100 cm |
| Adult chest | 130 cm |
| Car roof | 145-160 cm |

When the waterline sits between two anchors, report the deeper interval (life-safety bias). Without a visible anchor the depth is unknown and must not be guessed.

## 6. Guidance for Citizens Trapped in a Vehicle

Category: trapped_guidance. Source: [S3], [S2].

- "Stay inside your car if it is trapped in rapidly moving water. Get on the roof if water is rising." [S3]
- "Do NOT drive into flooded roadways or around a barricade": water can hide hazards and vehicles can be swept away in seconds. [S2]
- "Rescue should be attempted via high water vehicles (HWVs) whenever possible, followed by watercraft and 'go rescues' using advanced line systems techniques and/or tethered rescuers, dependent on incident characteristics." [S10]

## 7. Guidance for Citizens Trapped in a Building

Category: trapped_guidance. Source: [S3], [S2].

- "Get to the highest level if trapped in a building. Only get on the roof if necessary." [S3]
- "If you are trapped by moving water, move to the highest possible point and call" for help. [S2] In Tunisia the Civil Protection number is 198. [S8]
- "Don't go into a basement, or any room, if water covers the electrical outlets or if cords are submerged." [S2]

## 8. Electrical and Health Hazards of Floodwater

Category: health_hazards. Source: [S3], [S5], [S2].

- Do not touch electrical equipment if it is wet; be aware of the risk of electrocution. [S3]
- Unplug appliances to prevent electrical shock when power comes back on. [S5]
- Avoid wading in floodwater, which can be contaminated and contain dangerous debris. [S3]
- Keep tetanus vaccination up to date in case of a puncture wound or a wound contaminated during or after the flood. [S5]
- Use a generator or other gasoline-powered machinery only outdoors and away from windows (carbon monoxide). [S3]

## 9. Water Rescue Methods Hierarchy

Category: rescue_methods. Source: [S6], [S7].

Rescuers escalate from the lowest-risk method to the highest-risk one: Talk, Reach, Wade, Throw, Helo, Row, Go, Tow. [S6]

| Method | What it means |
|---|---|
| Talk | Guide the victim to self-rescue verbally |
| Reach | Reach the victim with a pole, branch or similar object from a safe position |
| Throw | Throw bags or flotation; about 80% of moving-water rescues use throw devices [S6] |
| Helo | Helicopter as a stable rescue platform when crews are equipped and trained |
| Row | All boat-based operations, including boats on highline or tether systems |
| Go / Tow | Tethered rescuer enters the water ("live bait" rescue): highest risk, last resort |

A FEMA Swiftwater/Flood Search and Rescue Team provides shore-based and boat-based water rescue for people and animals in swiftwater and flood environments. [S7]

## 10. Vulnerable Persons

Category: priority_matrix. Source: [S4], [S9].

- Floodwater that adults can still stand in is already unsafe for children and the elderly: hazard class H3 (up to 120 cm) is "unsafe for vehicles, children and the elderly". [S4]
- CrisisLink therefore treats any trapped elderly person, infant, child, injured, sick, pregnant or disabled person as P1 and sends a paramedic with the boat team. [S9]

## 11. Tunisia: Civil Protection Recommendations (in French)

Category: local_guidance. Source: [S8] Office National de la Protection Civile, 18 Sept 2026.

- Éviter de conduire sur les routes submergées par les eaux et ne jamais tenter de traverser les cours d'eau ou les oueds.
- S'éloigner des lits des oueds et des zones exposées aux ruissellements.
- Limiter les déplacements non indispensables et rester dans un endroit sûr pendant les périodes d'orage.
- Suivre régulièrement les bulletins météorologiques ainsi que les mises à jour et alertes officielles.
- Vérifier l'état des habitations, notamment les toitures, les terrasses et les points d'évacuation.
- Débrancher les appareils électriques non indispensables.
- En cas de besoin ou d'urgence, contacter les services de la Protection civile au numéro 198.

## 12. Human Escalation and Conflicting Reports

Category: escalation. Source: [S9] CrisisLink doctrine.

A human operator must review the incident before dispatch when:
- the photo and the voice or text report contradict each other (for example, the photo shows less than 20 cm but the caller says they are trapped at chest level);
- the image does not look like a flood, or the depth estimate has low confidence (night, blur, no visible reference object);
- the message may be a joke, a test or a prank;
- the voice note could not be transcribed, or a specialist agent returned unreadable output.

Several reports from the same citizen within 30 minutes are merged into one incident, so the dispatcher sees one ticket per emergency instead of duplicates.
