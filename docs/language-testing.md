# Language and session testing

## The question

An observed pattern was: changing `target_lang` while reusing a session appeared to retain the earlier response language, while changing both target language and session ID appeared to work. That observation is not enough to declare a backend bug.

## Controlled experiment implemented here

For one exact query, source language, and requested language change, the tool runs these requests sequentially:

| Run | Session | Target language | Why |
| --- | --- | --- | --- |
| A1 | Session A | Initial target | Establishes context in one session |
| A2 | Same Session A | Changed target | Tests target-language change with history present |
| B | Fresh Session B | Changed target | Tests same requested target without A's history |

The tool records query, source language, requested target language, redacted session label, response, status, TTFT, total time, chunk count, and a conservative response-script observation.

## How local response-language observation works

The tool counts Devanagari and Latin characters. It can say things such as:

- “Latin script (likely English, but not guaranteed)”
- “Devanagari script (could be Hindi or Marathi)”
- “Mixed or ambiguous script”

It deliberately cannot certify Hindi versus Marathi from script alone. Any uncertain classification stays explicit.

## CONFIRMED from source

- `source_lang` accepts `hi`, `mr`, or `en`.
- `target_lang` is used by `FarmerContext` and selects the dynamic voice-system prompt file.
- Session history is supplied to the agent before the run and stored afterward.

## Possible explanations - not conclusions

- conversation history can provide a language pattern that influences a model response
- target-language prompt selection may not be the only signal reaching the model
- a gateway, deployment version, or session routing layer may be involved
- the observed response may be mixed/ambiguous rather than clearly in one language

## Interpreting results responsibly

If A2 and B differ, record that session history is associated with the observed difference under this test. It does **not** prove Redis, prompts, or a particular line of code is the root cause.

If A2 and B match, record that the experiment did not reproduce the earlier observation under these conditions. It does **not** prove the behavior can never occur.

For stronger evidence, repeat with multiple queries, at different times, with fresh named test sessions, and record deployed version / environment if those facts are available.
