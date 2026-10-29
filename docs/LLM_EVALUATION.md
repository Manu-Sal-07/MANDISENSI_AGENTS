# LLM explanation layer: evaluation

Generated 2026-10-29T10:41:32Z. Writer `openai/gpt-oss-120b`, judge `qwen/qwen3.8-27b`.

The model only paraphrases sentences whose facts, numbers and names are written by code. Every paraphrase must keep the same slots, add no digit, no overclaim word, stay short and in the right script, and then pass an independent faithfulness judge. Anything that fails keeps its rule-based wording.

## 1. Acceptance (24 explanations, 120 sentences)

| Language | Explanations | Sentences | Kept from model | 95% CI | Judge rejected | Validator rejected | Fully rule-based |
|---|---|---|---|---|---|---|---|
| en | 8 | 40 | 38 | 0.83–0.99 | 2 | 0 | 0 |
| kn | 8 | 40 | 31 | 0.62–0.88 | 9 | 0 | 1 |
| hi | 8 | 40 | 33 | 0.68–0.91 | 7 | 0 | 0 |

The recommended market, day and every figure were identical with and without the model in all 24 cases: yes. Model errors (fell back to rules): 0. Median latency 6685 ms.

Rejection reasons: {"judge": 18}

## 2. Judge power (English, 9 corrupted and 3 faithful rewrites)

Caught 9/9 corruptions (95% CI 0.70–1.00); wrongly rejected 0/3 faithful rewrites (95% CI 0.00–0.56).

| Corruption | Judge says faithful? | Reason given |
|---|---|---|
| faithful | True |  |
| reversed | False | Reverses the comparison; implies the gain is relative to the nearest mandi rather than the alternative option. |
| added_claim | False | Adds a prediction about prices rising and drops 'spoilage' from the cost list. |
| dropped_qualifier | False | Drops the condition 'After transport, fees and spoilage'. |
| faithful | True |  |
| added_claim | False | Adds a claim about being 'crowded with buyers' which is not in the original. |
| reversed | False | Reverses the direction from 'open' to 'closed'. |
| wrong_meaning | False | Changes the meaning from being 'open and trading' to 'pays the best price'. |
| faithful | True |  |
| reversed | False | Reverses the meaning of 'not a promise' to 'firm promise' and changes 'missed' to 'met'. |
| added_claim | False | Adds a claim about the maximum being higher that is not in the original. |
| dropped_qualifier | False | Drops the claim that the minimum is a careful estimate, not a promise. |

## Limits

- The corruptions are hand-written for one language and a few sentence types, so the catch rate is a bound on those failure types, not a general guarantee.
- Kannada and Hindi acceptance depends on the judge model reading those scripts; a native-speaker review of the wording is still needed.
- Writer (OpenAI gpt-oss) and judge (Alibaba Qwen) are different model families but both run on the same hosted service, so an outage or rate limit affects both; when the judge cannot answer, the rule-based wording is kept.