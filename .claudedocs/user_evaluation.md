# Evaluation guidelines

## Evaluation Process Overview
- Display word and prompt: "请用'[word]'造一个句子" (Please make a sentence using '[word]')
- User types sentence in input field
- User submits sentence
- Validate input (word present, minimum length)
- Make a call with the sentence and the in-session system prompt to the AI model (DeepSeek for ZH, Claude for JP, Gemini Flash as orchestrator) to evaluate sentence and return feedback, scores and examples
- Display feedback to user
- After all attempts for a word, user self-rates mastery (0-5 quality scale) which updates SRS scheduling via SM-2 algorithm
- Repeat for each sentence the user submits
- After the session reaches the unique-word threshold, make a second AI model call with the session transcript and per-word evaluation data

## Input Validation Rules
- **Minimum Length**: Require at least 3-5 characters
- **Character Check**: Ensure target language characters are present (Chinese or Japanese)
- **Word Usage Check**: Verify the target vocabulary word is included

## In-session Feedback by AI Coach
- Detailed explanation in English should be returned to the user after every sentence is evaluated by the AI model
- **Corrections Section**:
  - Highlighted incorrect parts
  - Suggested corrections
  - Before/after comparison
- **Explanations Section**:
  - Why the mistake occurred
  - Grammar rules explanation (if grammar mistake occurred)
  - Common pitfalls
- **Example Sentences**:
  - 2-3 correct examples
  - Different contexts/meanings
  - Pinyin and translations

## End-of-session Summary by AI Coach
- Use the summary prompt in @.claudedocs/llm_invocation.md to provide a summary of the session

## Evaluation Metrics
- isCorrect (Boolean): a sentence is correct if grammar is correct and words are used correctly
- **grammarScore** : (1-10)
  - Word order (SVO structure)
  - Particle usage (了, 的, 地, etc.)
  - Verb tense and aspect
  - Measure words (量词)

- **usageScore** : (1-10)
  - Correct meaning/context
  - Appropriate collocations
  - Natural word combinations

- **naturalnessScore** : (1-10)
  - Native-like expression
  - Idiomatic usage
  - Contextual appropriateness


## Mastery Update (SRS / SM-2 Algorithm)
- After each word in a practice session, the user self-rates their mastery on a 0-5 quality scale
- The SM-2 algorithm updates spaced repetition fields: `repetitions`, `interval_days`, `ease_factor`, `next_review_date`
- **Quality < 3**: Reset to repetition 0, interval 1 day (word needs more practice)
- **Quality 3-4**: Standard SM-2 progression (1d → 3d → 7d → exponential via ease_factor)
- **Quality 5 on first attempt**: Fast-track to 14-day interval, repetition 2
- **Ease factor**: Updated per SM-2 formula, minimum 1.3

## Dynamic Mastery Status
- **Quality 5** → `is_mastered = true`
- **Quality ≤ 3** → `is_mastered = false`
- **Quality 4** → preserves existing mastery state (lenient)
- **"Mark as Known"** → fast-tracks to 90-day interval, `is_mastered = true`

## Word Selection for Practice
- 40% new words (`next_review_date` IS NULL)
- 60% due/overdue words (`next_review_date` ≤ today), sorted by urgency
- Falls back to future words if insufficient due words