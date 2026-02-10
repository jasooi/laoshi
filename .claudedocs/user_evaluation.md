# Evaluation guidelines

## Evaluation Process Overview
- Display word and prompt: "请用'[word]'造一个句子" (Please make a sentence using '[word]')
- User types sentence in input field
- User submits sentence
- Validate input (word present, minimum length)
- Make a call with the sentence and the in-session system prompt to the AI model (DeepSeek primary, Gemini 2.5 Flash backup) to evaluate sentence and return feedback, scores and examples
- Display feedback to user
- Update confidence score of the word using the returned scores
- Repeat for each sentence the user submits
- After the session reaches the unique-word threshold, make a second AI model call with the session transcript and per-word evaluation data

## Input Validation Rules
- **Minimum Length**: Require at least 3-5 characters
- **Character Check**: Ensure Chinese characters are present
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


## Confidence Score Update Formula
- Clamped between 0.0 and 1.0
- **Initial Score**: 0.5 (50%) for new words
- **Update Formula**: newScore = currentScore + (correctnessFactor * qualityMultiplier * learningRate)
- correctnessFactor = 1.0 if isCorrect = True, -0.5 if False
- qualityMultiplier = 0.4 * grammarScore + 0.4 * usageScore + 0.2 * naturalnessScore
- learningRate = 0.1


## Status Classification Rubrics
- **Needs Revision** (0.0 - 0.3): Very low confidence (words the user has struggled with)
- **Learning** (0.3 - 0.7): In progress, needs more practice (default state for new words at 0.5)
- **Reviewing** (0.7 - 0.9): Mostly mastered, occasional review
- **Mastered** (0.9 - 1.0): High confidence, minimal review needed


## Status levels
- New words are initialized with `confidenceScore = 0.5` (neutral), which results in the derived field `status = 'Learning'`.
- The **"needs revision"** level is reserved for words that have been practiced and whose confidence drops below 0.3, distinguishing them from unseen/neutral words.