# Retrieval Evaluation

Corpus: `corpus/emergency_protocols.md` (3357 tokens). 20 test queries (15 English, 3 French, 2 Tunisian Derja). A chunk counts as relevant only if it contains every fact of the expected answer.

| Chunking | Embedding model | Chunks | Precision@3 | Hit@3 | MRR | Hit@3 EN | Hit@3 FR/AR |
|---|---|---|---|---|---|---|---|
| fixed | all-MiniLM-L6-v2 | 23 | 0.300 | 0.800 | 0.706 | 0.933 | 0.400 |
| structured | all-MiniLM-L6-v2 | 24 | 0.300 | 0.750 | 0.699 | 0.933 | 0.200 |
| fixed | multilingual-e5-small | 23 | 0.367 | 0.850 | 0.780 | 0.933 | 0.600 |
| structured | multilingual-e5-small | 24 | 0.383 | 0.900 | 0.818 | 1.000 | 0.600 |
| fixed | multilingual-e5-small (no query prefix) | 23 | 0.383 | 0.850 | 0.804 | 0.933 | 0.600 |
| structured | multilingual-e5-small (no query prefix) | 24 | 0.383 | 0.900 | 0.817 | 1.000 | 0.600 |

## Queries a strategy cannot answer from a single chunk

- **fixed**: none
- **structured**: none

## Rank of the first relevant chunk per query (- = not in top 10)

| Query | fixed + all-MiniLM-L6-v2 | structured + all-MiniLM-L6-v2 | fixed + multilingual-e5-small | structured + multilingual-e5-small | fixed + multilingual-e5-small (no query prefix) | structured + multilingual-e5-small (no query prefix) |
|---|---|---|---|---|---|---|
| q01 (en) What rescue asset is needed for 60 cm of floodwater? | 1 | 1 | 2 | 1 | 2 | 1 |
| q02 (en) Which priority tier applies when the water is 130 cm deep? | 1 | 1 | 1 | 1 | 1 | 1 |
| q03 (en) How deep does moving water need to be to knock an adult off their feet? | 3 | 1 | 1 | 1 | 1 | 1 |
| q04 (en) At what water depth can a car start to float? | 1 | 1 | 1 | 1 | 1 | 1 |
| q05 (en) What does flood hazard class H3 mean and what is its depth limit? | 9 | 4 | 4 | 2 | 5 | 2 |
| q06 (en) Which hazard class means all building types are vulnerable to failure? | 1 | 1 | 1 | 1 | 1 | 1 |
| q07 (en) What should a driver do if their car is trapped in rapidly moving water? | 1 | 1 | 1 | 1 | 1 | 1 |
| q08 (en) What should people do if they are trapped inside a building during a flood? | 1 | 1 | 2 | 1 | 2 | 1 |
| q09 (en) An elderly woman is trapped at home with 40 cm of water. What priority is it? | 1 | 1 | 1 | 1 | 1 | 1 |
| q10 (en) The photo shows 10 cm of water but the caller says they are trapped at chest level. What should happen? | 1 | 3 | 1 | 1 | 1 | 1 |
| q11 (en) What is the civil protection emergency number in Tunisia? | 1 | 2 | 1 | 2 | 1 | 2 |
| q12 (en) What is the order of water rescue methods from lowest to highest risk? | 1 | 1 | 1 | 1 | 1 | 1 |
| q13 (en) How should rescuers reach occupants of a vehicle trapped in flash flood water? | 1 | 1 | 2 | 1 | 1 | 1 |
| q14 (en) Is it safe to enter a room where water covers the electrical outlets? | 2 | 2 | 1 | 2 | 1 | 2 |
| q15 (en) How high is a car wheel hub when estimating water depth from a photo? | 1 | 1 | 1 | 1 | 1 | 1 |
| q16 (fr) Quel véhicule de secours envoyer pour 70 cm d'eau ? | 6 | 5 | 1 | 1 | 1 | 1 |
| q17 (fr) Que recommande la Protection civile tunisienne en cas de fortes pluies ? | 2 | 1 | 1 | 1 | 1 | 1 |
| q18 (fr) Faut-il un bateau quand l'eau dépasse un mètre ? | - | - | 2 | 2 | 2 | 2 |
| q19 (ar) المية وصلت للصدر، شنوة الأولوية؟ | 2 | 5 | 5 | 4 | 4 | 6 |
| q20 (ar) شنوة نعمل كان الكرهبة محصورة في الماء؟ | - | - | 7 | 9 | 8 | 6 |
