# Mandarin Language Learning Chatbot - Detailed Project Plan

## 1. Project Overview

### 1.1 Purpose
A web-based interactive chatbot application that helps users practice Mandarin Chinese sentence formation. The application presents vocabulary words, evaluates user-generated sentences, provides detailed feedback, and tracks learning progress through confidence scores.

### 1.2 Core Features
- **Vocabulary Presentation**: Display Mandarin words with pinyin and definitions
- **Sentence Formation Practice**: Prompt users to create sentences using given vocabulary
- **AI-Powered Evaluation**: Assess sentence correctness, grammar, and usage
- **Detailed Feedback**: Provide corrections, explanations, and example sentences
- **Confidence Tracking**: Maintain and update confidence scores per vocabulary word
- **Vocabulary Management**: Import from CSV and support multiple vocabulary sources

---

## 2. System Architecture

### 2.1 Technology Stack

#### Frontend
- **Framework**: React.js with TypeScript
- **Styling**: Tailwind CSS for clean, minimalist design
- **State Management**: React Context API for global state
- **Routing**: React Router for navigation
- **HTTP Client**: Axios or Fetch API
- **Deployment**: Vercel

#### Backend
- **Framework**: Python Flask
- **AI Integration**: Google Gemini Flash API for sentence evaluation
- **Database**: 
  - MongoDB for user data and vocabulary storage (flexible schema, JSON-native)
  - PyMongo for MongoDB integration
- **Authentication**: Single-user mode (localStorage for MVP Phase 1)

#### Deployment
- **Frontend**: Vercel
- **Backend**: Railway, Render, or similar (Flask-compatible)
- **Database**: MongoDB Atlas (cloud)

### 2.2 Architecture Pattern
- **Client-Server Architecture**: RESTful API
- **Component-Based Frontend**: Modular React components
- **Service Layer**: Separate business logic from API routes

---

## 3. Data Models

### 3.1 Vocabulary Word Schema
```typescript
interface VocabularyWord {
  id: string;                    // Unique identifier
  word: string;                   // Chinese characters (e.g., "工作")
  pinyin: string;                 // Pinyin pronunciation (e.g., "gōngzuò")
  definition: string;              // English definition
  source: string;                  // Vocabulary source identifier
  createdAt: Date;                // Import timestamp
  metadata?: {                    // Optional additional data
    partOfSpeech?: string;
    difficulty?: number;
    frequency?: number;
  };
}
```

### 3.2 User Progress Schema
```typescript
interface UserProgress {
  userId: string;                 // User identifier
  wordId: string;                 // Reference to VocabularyWord
  confidenceScore: number;        // 0.0 to 1.0 (or 0-100)
  totalAttempts: number;          // Total times word was practiced
  correctAttempts: number;        // Number of correct sentences
  lastPracticed: Date;            // Last practice timestamp
  nextReviewDate?: Date;          // For spaced repetition
  masteryLevel: 'needs revision' | 'learning' | 'reviewing' | 'mastered';
}
```

### 3.3 Practice Session Schema
```typescript
interface PracticeSession {
  id: string;
  userId: string;
  wordId: string;
  userSentence: string;           // User's submitted sentence
  isCorrect: boolean;             // Overall correctness
  evaluation: {
    grammarScore: number;         // 0-100
    usageScore: number;           // 0-100
    naturalnessScore: number;    // 0-100
    feedback: string;             // Detailed feedback text
    corrections?: string[];       // List of corrections
    explanations?: string[];      // Explanations for mistakes
    exampleSentences?: string[];  // Additional examples
  };
  timestamp: Date;
}
```

### 3.4 Vocabulary Source Schema
```typescript
interface VocabularySource {
  id: string;
  name: string;                   // Display name (e.g., "HSK Level 1")
  type: 'csv' | 'api' | 'builtin' | 'custom';
  filePath?: string;              // For CSV imports
  wordIds: string[];              // List of word IDs in this source
  createdAt: Date;
}
```

---

## 4. Core Features - Detailed Specifications

### 4.1 Vocabulary Presentation Module

#### 4.1.1 Word Selection Algorithm
- **Confidence-Based Selection**: Prioritize words with lower confidence scores
- **Spaced Repetition**: Use algorithm (e.g., SM-2) to determine review timing
- **Difficulty Balancing**: Mix easy and challenging words
- **User Preferences**: Allow filtering by source, difficulty, or mastery level

#### 4.1.2 Display Components
- **Word Card Component**:
  - Chinese characters (large, clear font)
  - Pinyin with tone marks (shown in tooltip on hover)
  - English definition (shown in tooltip on hover)
  - Part of speech (if available)
  - Current confidence score indicator
  - Example sentence (optional, can be toggled)

#### 4.1.3 User Interface Flow
```
1. On the homepage, the user clicks on the Start Practice button
2. The Practice view opens, showing a word card above a conversational chat interface
3. System selects a word based on the confidence algorithm and displays it in the word card
4. System sends a chat message prompt: "请用'[word]'造一个句子" (Please make a sentence using '[word]')
5. User types their sentence as a chat reply and presses Enter or clicks the Send button
6. System evaluates the sentence and replies in the chat with feedback, scores, and example sentences
7. User can choose to reattempt this word (new attempt for learning, but does not increase the unique word count) or move on to the next word
8. Steps 3–7 repeat until the practiced words threshold of unique words is met (default is 10)
9. After the session ends, the system makes a separate call to Gemini Flash to generate a teacher-style practice session summary (2 strengths, 1 area for improvement)
10. On the sidebar, the user can select the 'Vocabulary' section to view all words and manually add, edit, or delete vocabulary
11. On the sidebar, the user can select the 'Settings' section to change the practiced words threshold
12. On the sidebar, the user can navigate to 'Files' to import vocabulary from CSV files
```

### 4.2 Sentence Formation Practice Module

#### 4.2.1 Input Interface
- **Text Input Field**: 
  - Support for Chinese characters (Pinyin input method)
  - Character count indicator
  - Submit button
  - "Skip" option (counts as incorrect)

#### 4.2.2 Input Validation
- **Minimum Length**: Require at least 3-5 characters
- **Character Check**: Ensure Chinese characters are present
- **Word Usage Check**: Verify the target vocabulary word is included

#### 4.2.3 Practice Session Flow
```
1. Display word and prompt: "请用'[word]'造一个句子" (Please make a sentence using '[word]')
2. User types sentence in input field
3. User submits sentence
4. System validates input (word present, minimum length)
5. Loading indicator while evaluation processes
6. Display evaluation results (feedback, scores, examples) in the chat and results panel
7. User may choose "Reattempt word" to try again with the same word (affects attempts and confidence, but does not increase the unique-words-in-session counter)
8. When user moves on, update confidence score and increment the count of unique words practiced (if this is the first correctly/evaluated attempt for that word in this session)
9. Show the next word in the word card and repeat the chat flow
```

### 4.3 Sentence Evaluation Module

#### 4.3.1 Evaluation Criteria
- **Grammar Correctness** (40% weight):
  - Word order (SVO structure)
  - Particle usage (了, 的, 地, etc.)
  - Verb tense and aspect
  - Measure words (量词)
  
- **Word Usage Accuracy** (30% weight):
  - Correct meaning/context
  - Appropriate collocations
  - Natural word combinations
  
- **Naturalness** (20% weight):
  - Native-like expression
  - Idiomatic usage
  - Contextual appropriateness
  
- **Completeness** (10% weight):
  - Complete sentence structure
  - Proper punctuation

#### 4.3.2 AI Evaluation Implementation
- **API Integration**: 
  - Google Gemini Flash API for sentence evaluation
  - Fast, cost-effective model suitable for real-time evaluation
  
- **Prompt Engineering**:
```
You are a Mandarin Chinese language teacher evaluating a student's sentence.

Target vocabulary word: [word] ([pinyin]) - [definition]
Student's sentence: [user_sentence]

Evaluate the sentence on:
1. Grammar correctness (0-100)
2. Word usage accuracy (0-100)
3. Naturalness (0-100)
4. Overall correctness (true/false)

Provide:
- Detailed feedback in English
- Specific corrections if needed, in English
- Explanation of mistakes, in English
- 2-3 example Mandarin sentences using the word correctly

Return response in JSON format:
{
  "grammarScore": number,
  "usageScore": number,
  "naturalnessScore": number,
  "isCorrect": boolean,
  "feedback": string,
  "corrections": string[],
  "explanations": string[],
  "exampleSentences": string[]
}
```

- **Error Handling**: 
  - Retry logic for API failures
  - Graceful error messages to user
  - Logging for debugging

- **Session Summary Call**:
  - After the session reaches the unique-word threshold, make a second Gemini Flash call with the session transcript and per-word evaluation data.
  - Prompt Gemini to respond as a teacher summarizing the lesson with **2 good things** the student did and **1 area for improvement**.
  - Example tone: “Good job today! You did a good job with using the 以...为 grammar structure and even used difficult phrases like 非物质文化遗产. I noticed you have the tendency to use 做工 instead of 工作 though. Do take note of this in the future.”

### 4.4 Feedback and Correction Module

#### 4.4.1 Feedback Display Components
- **Score Breakdown**: Visual display of grammar, usage, naturalness scores
- **Overall Result**: Green checkmark (correct) or red X (needs improvement)
- **Feedback Text**: Detailed explanation in English
- **Corrections Section**: 
  - Highlighted incorrect parts
  - Suggested corrections
  - Before/after comparison
- **Explanations Section**: 
  - Why the mistake occurred
  - Grammar rules explanation
  - Common pitfalls
- **Example Sentences**: 
  - 2-3 correct examples
  - Different contexts/meanings
  - Pinyin and translations

#### 4.4.2 Feedback UI Design
```
┌─────────────────────────────────────┐
│ Result: ✓ Correct (85/100)          │
├─────────────────────────────────────┤
│ Grammar: 90/100                     │
│ Usage: 85/100                       │
│ Naturalness: 80/100                 │
├─────────────────────────────────────┤
│ Feedback:                           │
│ Your sentence is mostly correct...  │
├─────────────────────────────────────┤
│ Corrections:                        │
│ • Consider using 了 after 工作      │
├─────────────────────────────────────┤
│ Examples:                           │
│ 1. 我每天工作八小时。                │
│    (I work 8 hours every day.)      │
│ 2. 他在公司工作。                    │
│    (He works at the company.)       │
└─────────────────────────────────────┘
```

### 4.5 Confidence Score Tracking Module

#### 4.5.1 Confidence Score Algorithm
- **Initial Score**: 0.5 (50%) for new words
- **Update Formula**:
  ```
  newScore = currentScore + (correctnessFactor * learningRate)
  
  Where:
  - correctnessFactor = 1.0 if correct, -0.5 if incorrect
  - learningRate = 0.1 (adjustable)
  - Clamped between 0.0 and 1.0
  ```

- **Alternative: Spaced Repetition Algorithm (SM-2)**
  ```
  - Correct answer: confidence increases, interval increases
  - Incorrect answer: confidence decreases, interval resets
  - Next review date calculated based on interval
  ```

**Mastery Initialization & Semantics**:
- New vocabulary items are initialized with `confidenceScore = 0.5` (neutral) and `masteryLevel = 'learning'`.
- The **"needs revision"** level is reserved for words that have been practiced and whose confidence drops below 0.3, distinguishing them from unseen/neutral words.

#### 4.5.2 Score Update Logic
```typescript
function updateConfidenceScore(
  currentScore: number,
  isCorrect: boolean,
  evaluationScores: { grammar: number, usage: number, naturalness: number }
): number {
  const correctnessFactor = isCorrect ? 1.0 : -0.5;
  const qualityMultiplier = (
    evaluationScores.grammar * 0.4 +
    evaluationScores.usage * 0.3 +
    evaluationScores.naturalness * 0.2 +
    (isCorrect ? 10 : 0) * 0.1
  ) / 100;
  
  const learningRate = 0.15;
  const change = correctnessFactor * qualityMultiplier * learningRate;
  
  return Math.max(0, Math.min(1, currentScore + change));
}
```

#### 4.5.3 Mastery Level Classification
- **Needs Revision** (0.0 - 0.3): Very low confidence (words the user has struggled with)
- **Learning** (0.3 - 0.7): In progress, needs more practice (default state for new words at 0.5)
- **Reviewing** (0.7 - 0.9): Mostly mastered, occasional review
- **Mastered** (0.9 - 1.0): High confidence, minimal review needed

#### 4.5.4 Progress Visualization
- **Progress Dashboard**: 
  - Overall statistics (total words, mastered count, etc.)
  - Confidence distribution chart
  - Progress over time graph
- **Vocabulary View**: 
  - Sortable by confidence score
  - Color-coded by mastery level
  - Filter by mastery level

### 4.6 Vocabulary Management Module

#### 4.6.1 CSV Import Functionality

**CSV Format Specification**:
```csv
word,definition
工作,gōngzuò to work; job
学习,xuéxí to study; to learn
```

**Alternative Formats Supported**:
```csv
word,pinyin,definition,partOfSpeech
工作,gōngzuò,to work; job,verb
学习,xuéxí,to study; to learn,verb
```

**Import Process**:
1. User uploads CSV file via file input in the **Files** section
2. Client-side validation (file type, structure)
3. Parse CSV (use PapaParse or similar library)
4. Extract word, pinyin, definition
5. Validate data (non-empty fields, valid characters)
6. Create vocabulary source entry
7. Store words in database
8. Display import summary (successful, failed, duplicates)

**Error Handling**:
- Invalid file format
- Missing required columns
- Duplicate words
- Encoding issues (UTF-8 support)
- Large file handling (chunked processing)

**Location in UI**:
- CSV import is accessed **only** via the `Files` section in the sidebar.
- The `Vocabulary` section is used for viewing and manually managing existing vocabulary, not for file uploads.

#### 4.6.2 Vocabulary Source Management
- **Source Selection Interface**:
  - Dropdown or list of available sources
  - "Create New Source" option
  - Preview of words in each source
  
- **Source Operations**:
  - Create new source
  - Import words to existing source
  - Delete source (with confirmation)
  - Merge sources
  - Export source to CSV

#### 4.6.3 Additional Vocabulary Sources (Future)
- **Pre-built Lists**: HSK levels, common words, business Chinese
- **Textbook Integration**: Import from popular textbook word lists
- **API Integration**: Connect to Chinese dictionary APIs
- **Community Sources**: User-shared vocabulary lists

---

## 5. User Interface Design

### 5.1 Main Layout (Minimalist Design)

**Design Philosophy**: Clean, minimal interface with subtle purple accents, inspired by modern note-taking apps.

```
┌─────────────────────────────────────────────────────────┐
│ [Sidebar] │ Main Content Area                           │
│           │                                             │
│ Icons:    │ ┌─────────────────────────────────────┐   │
│ • Home    │ │ Header: Greeting | Progress Summary │   │
│ • Progress│ └─────────────────────────────────────┘   │
│ • Vocabulary                                      │   │
│ • Files   │  Main Content:                        │   │
│ • Settings│  (Start button / Practice chat /      │   │
│           │   Practice session summary)           │   │
│           │                                       │   │
└─────────────────────────────────────────────────────────┘
```

**Design Elements**:
- **Color Scheme**: White background, dark text, subtle purple accents (#9333EA or similar)
- **Sidebar**: Vertical icon navigation on left (icon-only, with text labels shown on hover)
- **Header**: Clean top bar with greeting and progress summary (e.g., mastery percentage, words practiced today)
- **Content Area**: Spacious, uncluttered main area
- **Typography**: Clean, modern sans-serif fonts
- **Spacing**: Generous whitespace, minimal borders
- **Cards**: Subtle shadows, rounded corners, minimal borders

### 5.2 Key Pages/Views

#### 5.2.1 Home/Dashboard
- **Header**: Greeting (e.g., "Good morning") with time-based icon
- Progress Summary (words practiced today, mastery progress)
- "Start Practice" button
- **Get Started Section** (for new users):
  - Checklist items with icons
  - "Import vocabulary from CSV"
  - "Start practicing"



#### 5.2.2 Practice View
- **Word Card**: 
  - Large, centered Chinese characters
  - Tooltip on hover showing pinyin and English definition
  - Confidence indicator (subtle progress bar or badge)
- **Sentence Input**: 
  - Large, clean text input area
  - Character count (subtle, bottom right)
  - Submit button (purple, prominent)
  - Skip option (subtle, text link)
- **Progress Indicator**: Minimal dot indicator or progress bar

#### 5.2.3 Results/Feedback View
- **Result Badge**: Large checkmark (✓) or X icon with score
- **Score Breakdown**: Minimal horizontal bars or numbers
- **Feedback Card**: 
  - Clean white card with subtle border
  - Feedback text in readable format
  - Corrections in highlighted sections
  - Example sentences in separate cards
- **Action Buttons**:
  - **Reattempt word / Try Again** (secondary): lets the user practice the same word again; affects attempts and confidence but does **not** increase the unique words count for the session
  - **Next Word** (primary, purple): moves on to the next vocabulary item and increments the unique word counter (if this is the first evaluated attempt for that word in the session)

#### 5.2.4 Vocabulary Management
- **Source Cards**: Card-based layout (like "Inbox" and "Example space" from reference)
- **CSV Import**: 
  - Drag-and-drop area or file picker
  - Clean upload interface
  - Import progress indicator
- **Word List**: 
  - Minimal table or card grid
  - Confidence score as colored badge
  - Search and filter in header

#### 5.2.5 Progress Dashboard (Future Phase)
- **Stats Cards**: Minimal cards with numbers
- **Chart**: Clean, simple line or bar chart
- **Mastery Breakdown**: Color-coded progress indicators

### 5.3 Responsive Design & UI Guidelines
- **Mobile-First**: Optimized for phones and tablets
- **Touch-Friendly**: Large buttons, easy input, generous tap targets
- **Keyboard Support**: Pinyin input method compatibility
- **Accessibility**: Screen reader support, keyboard navigation
- **Design System**:
  - **Primary Color**: Purple (#9333EA or similar)
  - **Text**: Dark gray (#1F2937) on white (#FFFFFF)
  - **Borders**: Subtle gray (#E5E7EB)
  - **Shadows**: Minimal, soft shadows for depth
  - **Border Radius**: 8-12px for cards, 6px for buttons
  - **Spacing**: Consistent 4px/8px/16px/24px scale
  - **Icons**: Minimal, line-style icons

---

## 6. API Design

### 6.1 RESTful Endpoints (Flask Routes)

#### Vocabulary Endpoints
```
GET    /api/vocabulary                    # Get all vocabulary words
GET    /api/vocabulary/<word_id>          # Get specific word
POST    /api/vocabulary/<word_id>          # Update specific word
DELETE /api/vocabulary/<word_id>          # Delete specific word
POST   /api/vocabulary/import              # Import from CSV
GET    /api/vocabulary/sources             # Get all sources
POST   /api/vocabulary/sources             # Create new source
DELETE /api/vocabulary/sources/<source_id> # Delete source
GET    /api/vocabulary/sources/<source_id>/words  # Get words in source
```

#### Practice Endpoints
```
GET    /api/practice/next-word             # Get next word to practice
POST   /api/practice/evaluate              # Evaluate sentence
GET    /api/practice/sessions              # Get practice history
GET    /api/practice/sessions/<session_id> # Get specific session
```

#### Progress Endpoints
```
GET    /api/progress                       # Get user progress summary (single-user: 'default_user')
GET    /api/progress/words                 # Get all word progress
GET    /api/progress/words/<word_id>       # Get specific word progress
PUT    /api/progress/words/<word_id>       # Update word progress
GET    /api/progress/stats                 # Get statistics
```

### 6.2 Request/Response Examples

#### Evaluate Sentence (Flask Endpoint)
```python
# Flask route example
@app.route('/api/practice/evaluate', methods=['POST'])
def evaluate_sentence():
    data = request.json
    word_id = data.get('wordId')
    sentence = data.get('sentence')
    user_id = 'default_user'  # Single-user mode
    
    # Evaluate using Gemini Flash
    evaluation = evaluate_with_gemini(word_id, sentence)
    
    # Update confidence score
    updated_confidence = update_confidence_score(user_id, word_id, evaluation)
    
    return jsonify({
        "sessionId": str(ObjectId()),
        "isCorrect": evaluation['isCorrect'],
        "evaluation": evaluation,
        "updatedConfidence": updated_confidence
    })
```

**Request:**
```json
POST /api/practice/evaluate
{
  "wordId": "507f1f77bcf86cd799439011",
  "sentence": "我每天工作八小时。"
}
```

**Response:**
```json
{
  "sessionId": "507f191e810c19729de860ea",
  "isCorrect": true,
  "evaluation": {
    "grammarScore": 95,
    "usageScore": 90,
    "naturalnessScore": 85,
    "feedback": "Excellent sentence! Your usage of 工作 is correct...",
    "corrections": [],
    "explanations": [],
    "exampleSentences": [
      "我每天工作八小时。",
      "他在公司工作。"
    ]
  },
  "updatedConfidence": 0.72
}
```

---

## 7. Database Schema (MongoDB)

### 7.1 Collections and Document Schemas

#### 7.1.1 Vocabulary Words Collection
```javascript
// Collection: vocabulary_words
{
  _id: ObjectId,                    // MongoDB auto-generated ID
  word: String,                     // Chinese characters (e.g., "工作")
  pinyin: String,                   // Pinyin pronunciation (e.g., "gōngzuò")
  definition: String,               // English definition
  sourceId: ObjectId,               // Reference to vocabulary_sources
  metadata: {                       // Optional additional data
    partOfSpeech: String,
    difficulty: Number,
    frequency: Number
  },
  createdAt: Date,                  // Import timestamp
  updatedAt: Date                   // Last update timestamp
}

// Indexes:
// - { word: 1 } (unique)
// - { sourceId: 1 }
// - { "metadata.difficulty": 1 }
```

#### 7.1.2 Vocabulary Sources Collection
```javascript
// Collection: vocabulary_sources
{
  _id: ObjectId,                    // MongoDB auto-generated ID
  name: String,                     // Display name (e.g., "HSK Level 1")
  type: String,                     // 'csv' | 'api' | 'builtin' | 'custom'
  filePath: String,                 // For CSV imports (optional)
  wordIds: [ObjectId],              // Array of vocabulary word IDs
  createdAt: Date,
  updatedAt: Date
}

// Indexes:
// - { name: 1 } (unique)
// - { type: 1 }
```

#### 7.1.3 User Progress Collection
```javascript
// Collection: user_progress
{
  _id: ObjectId,                    // MongoDB auto-generated ID
  userId: String,                   // User identifier
  wordId: ObjectId,                 // Reference to vocabulary_words
  confidenceScore: Number,          // 0.0 to 1.0 (default: 0.5)
  totalAttempts: Number,            // Total times word was practiced (default: 0)
  correctAttempts: Number,          // Number of correct sentences (default: 0)
  lastPracticed: Date,              // Last practice timestamp
  nextReviewDate: Date,             // For spaced repetition (optional)
  masteryLevel: String,             // 'needs revision' | 'learning' | 'reviewing' | 'mastered'
  createdAt: Date,
  updatedAt: Date
}

// Indexes:
// - { userId: 1, wordId: 1 } (unique compound index)
// - { userId: 1, confidenceScore: 1 }
// - { userId: 1, masteryLevel: 1 }
// - { userId: 1, nextReviewDate: 1 }
```

#### 7.1.4 Practice Sessions Collection
```javascript
// Collection: practice_sessions
{
  _id: ObjectId,                    // MongoDB auto-generated ID
  userId: String,                   // User identifier
  wordId: ObjectId,                 // Reference to vocabulary_words
  userSentence: String,             // User's submitted sentence
  isCorrect: Boolean,               // Overall correctness
  evaluation: {                     // Detailed evaluation object
    grammarScore: Number,           // 0-100
    usageScore: Number,             // 0-100
    naturalnessScore: Number,       // 0-100
    feedback: String,               // Detailed feedback text
    corrections: [String],          // Array of corrections
    explanations: [String],          // Array of explanations
    exampleSentences: [String]      // Array of example sentences
  },
  timestamp: Date,                   // Practice session timestamp
  createdAt: Date
}

// Indexes:
// - { userId: 1, timestamp: -1 }
// - { wordId: 1, timestamp: -1 }
// - { userId: 1, wordId: 1, timestamp: -1 }
// - { timestamp: -1 } (for time-based queries)
```

### 7.2 Python/PyMongo Schema Definitions

```python
# models/vocabulary_word.py
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

class VocabularyWord:
    def __init__(self, db):
        self.collection = db['vocabulary_words']
        # Create indexes
        self.collection.create_index("word", unique=True)
        self.collection.create_index("sourceId")
    
    def create(self, word, pinyin, definition, source_id, metadata=None):
        doc = {
            "word": word,
            "pinyin": pinyin,
            "definition": definition,
            "sourceId": ObjectId(source_id),
            "metadata": metadata or {},
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        result = self.collection.insert_one(doc)
        return result.inserted_id
    
    def find_by_id(self, word_id):
        return self.collection.find_one({"_id": ObjectId(word_id)})
    
    def find_by_source(self, source_id):
        return list(self.collection.find({"sourceId": ObjectId(source_id)}))
```

```python
# models/user_progress.py
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

class UserProgress:
    def __init__(self, db):
        self.collection = db['user_progress']
        # Create indexes
        self.collection.create_index([("userId", 1), ("wordId", 1)], unique=True)
        self.collection.create_index([("userId", 1), ("confidenceScore", 1)])
        self.collection.create_index([("userId", 1), ("nextReviewDate", 1)])
    
    def create_or_update(self, user_id, word_id, confidence_score=None, 
                        total_attempts=None, correct_attempts=None, 
                        last_practiced=None, next_review_date=None, 
                        mastery_level=None):
        query = {
            "userId": user_id,
            "wordId": ObjectId(word_id)
        }
        
        update = {
            "$set": {
                "updatedAt": datetime.utcnow()
            },
            "$setOnInsert": {
                "createdAt": datetime.utcnow(),
                "confidenceScore": 0.5,
                "totalAttempts": 0,
                "correctAttempts": 0,
            "masteryLevel": "learning"
            }
        }
        
        if confidence_score is not None:
            update["$set"]["confidenceScore"] = confidence_score
        if total_attempts is not None:
            update["$set"]["totalAttempts"] = total_attempts
        if correct_attempts is not None:
            update["$set"]["correctAttempts"] = correct_attempts
        if last_practiced:
            update["$set"]["lastPracticed"] = last_practiced
        if next_review_date:
            update["$set"]["nextReviewDate"] = next_review_date
        if mastery_level:
            update["$set"]["masteryLevel"] = mastery_level
        
        return self.collection.update_one(query, update, upsert=True)
    
    def find_by_user(self, user_id):
        return list(self.collection.find({"userId": user_id}))
    
    def find_by_user_and_word(self, user_id, word_id):
        return self.collection.find_one({
            "userId": user_id,
            "wordId": ObjectId(word_id)
        })
```

### 7.3 MongoDB Connection Details

#### 7.3.1 Required Connection Information

**For MongoDB Atlas (Cloud - Recommended):**
- **Connection String (URI)**: Provided by MongoDB Atlas dashboard
  - Format: `mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority`
  - Example: `mongodb+srv://myuser:mypassword@cluster0.xxxxx.mongodb.net/laoshi-coach?retryWrites=true&w=majority`
- **Username**: Your MongoDB Atlas database user
- **Password**: Your MongoDB Atlas database password
- **Cluster URL**: Your cluster hostname (e.g., `cluster0.xxxxx.mongodb.net`)
- **Database Name**: Name of your database (e.g., `laoshi-coach`)

**For Local MongoDB:**
- **Connection String**: `mongodb://localhost:27017/<database>`
- **Host**: `localhost` (or your MongoDB server IP)
- **Port**: `27017` (default MongoDB port)
- **Database Name**: Your chosen database name

#### 7.3.2 How to Get MongoDB Atlas Connection String

1. **Sign up/Login** to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. **Create a Cluster** (free tier available - M0)
3. **Create Database User**:
   - Go to "Database Access" → "Add New Database User"
   - Choose "Password" authentication
   - Create username and password (save these!)
   - Set user privileges (read/write to any database, or specific database)
4. **Whitelist IP Address**:
   - Go to "Network Access" → "Add IP Address"
   - For development: Add `0.0.0.0/0` (allows all IPs - use with caution)
   - For production: Add specific IP addresses
5. **Get Connection String**:
   - Go to "Database" → "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Replace `<database>` with your database name (e.g., `laoshi-coach`)

#### 7.3.3 Environment Variables Setup

Create a `.env` file in your project root:

```env
# MongoDB Connection
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/laoshi-coach?retryWrites=true&w=majority

# Or for local MongoDB:
# MONGODB_CONNECTION_STRING=mongodb://localhost:27017/laoshi-coach

# Database Name (optional, can be in URI)
DB_NAME=laoshi-coach

# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Flask Environment
FLASK_ENV=development
FLASK_DEBUG=True
```

#### 7.3.4 Connection Code Example (Python Flask)

```python
# config/database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    try:
        connection_string = os.getenv('MONGODB_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("MONGODB_CONNECTION_STRING not found in environment variables")
        
        client = MongoClient(connection_string)
        # Test connection
        client.admin.command('ping')
        
        db_name = os.getenv('DB_NAME', 'laoshi-coach')
        db = client[db_name]
        
        print(f"MongoDB Connected: {db_name}")
        return db
    except ConnectionFailure as e:
        print(f"MongoDB Connection Error: {e}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise

# Initialize database connection
db = connect_db()
```

#### 7.3.5 Security Best Practices

- **Never commit `.env` file** to version control
- **Use environment variables** for all sensitive data
- **Restrict IP access** in MongoDB Atlas (don't use `0.0.0.0/0` in production)
- **Use strong passwords** for database users
- **Enable MongoDB Atlas authentication** (enabled by default)
- **Use connection string with SSL** (MongoDB Atlas uses SSL by default)
- **Rotate passwords** periodically
- **Use separate database users** for development and production

#### 7.3.6 What You Need to Provide

To set up the application, you'll need to provide:

1. **MongoDB Connection String** (or local MongoDB details)
   - For MongoDB Atlas: Full connection URI with username, password, and cluster URL
   - For local: Host, port, and database name

2. **Database Credentials** (if using MongoDB Atlas):
   - Database username
   - Database password
   - Cluster URL/hostname

**Note**: The connection string format is:
- **Atlas**: `mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority`
- **Local**: `mongodb://<host>:<port>/<database>`

You can share the connection string directly, or we can set it up as an environment variable during development.

---

## 8. Implementation Phases

### Phase 1: MVP (Minimum Viable Product) - Single User
**Duration**: 3-4 weeks

**Scope**: Simplified single-user application, no authentication required

**Features**:
- **Frontend (Vercel)**:
  - ✅ Minimalist UI with Tailwind CSS (COMPLETE)
  - Home dashboard with greeting and quick stats
  - Practice view with word card and sentence input
  - Results view with feedback and corrections
  - Vocabulary view for browsing and manually managing words
  - Basic progress tracking display
  
- **Backend (Flask)**:
  - RESTful API endpoints
  - MongoDB integration with PyMongo
  - Gemini Flash API integration for sentence evaluation
  - CSV import and parsing
  - Confidence score calculation and storage
  
- **Core Functionality**:
  - Display vocabulary words from CSV
  - User forms sentences using target word
  - AI evaluation via Gemini Flash
  - Store practice sessions and progress
  - Update confidence scores per word
  - Display learning progress

**Deliverables**:
- Deployed frontend on Vercel
- Deployed backend API (Railway/Render)
- MongoDB Atlas database connection
- CSV vocabulary import working
- End-to-end practice flow functional
- Basic progress tracking

### Phase 2: Enhanced Features
**Duration**: 3-4 weeks

**Features**:
- Improved evaluation with detailed feedback
- Spaced repetition algorithm
- Progress dashboard with charts
- Multiple vocabulary sources
- Better error handling
- Export functionality

### Phase 3: Advanced Features
**Duration**: 3-4 weeks

**Features**:
- User authentication (if multi-user)
- Advanced statistics and analytics
- Customizable confidence algorithms
- Pre-built vocabulary lists
- Mobile app optimization
- Offline mode support

### Phase 4: Polish & Optimization
**Duration**: 2-3 weeks

**Features**:
- Performance optimization
- UI/UX improvements
- Comprehensive testing
- Documentation
- Deployment setup

---

## 9. Technical Considerations

### 9.1 Chinese Text Handling
- **Encoding**: Ensure UTF-8 throughout the stack
- **Input Methods**: Support Pinyin input methods (Sogou, Google Pinyin, etc.)
- **Character Rendering**: Use appropriate fonts (Noto Sans CJK, Microsoft YaHei)
- **Text Processing**: Consider using libraries like `jieba` for word segmentation (if needed)

### 9.2 AI API Integration (Gemini Flash)
- **Rate Limiting**: Implement caching and rate limiting for API calls
- **Cost Management**: Cache evaluations, batch requests when possible
- **Error Handling**: 
  - Retry logic with exponential backoff
  - Graceful error messages to user
  - Logging for debugging API issues
- **Response Time**: Optimize prompts for faster responses (Gemini Flash is optimized for speed)
- **API Setup**: 
  - Get API key from Google AI Studio
  - Use `google-generativeai` Python library
  - Configure model: `gemini-1.5-flash`

### 9.3 Performance Optimization
- **Frontend**: 
  - Code splitting
  - Lazy loading of components
  - Virtual scrolling for long word lists
- **Backend**:
  - Database indexing
  - Query optimization
  - Response caching
  - Connection pooling

### 9.4 Security Considerations
- **Input Validation**: Sanitize all user inputs
- **File Upload**: Validate CSV files, limit file size
- **API Security**: Rate limiting, authentication tokens
- **Data Privacy**: Encrypt sensitive user data

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Confidence score calculation algorithms
- CSV parsing and validation
- Word selection algorithms
- Data transformation functions

### 10.2 Integration Tests
- API endpoints
- Database operations
- AI evaluation integration
- CSV import workflow

### 10.3 End-to-End Tests
- Complete practice session flow
- Vocabulary import process
- Progress tracking updates
- Error handling scenarios

### 10.4 Manual Testing
- Chinese input method compatibility
- Cross-browser testing
- Mobile device testing
- Accessibility testing

---

## 11. Deployment Plan

### 11.1 Development Environment
- **Frontend**: Local React dev server (Vite or Create React App)
- **Backend**: Local Flask development server
- **Database**: MongoDB Atlas (free tier) - connection via `MONGODB_CONNECTION_STRING`
- **Environment Variables**: 
  - `MONGODB_CONNECTION_STRING` - MongoDB connection
  - `GEMINI_API_KEY` - Google Gemini API key
  - `.env` file for local configuration (never commit to git)
- **CORS**: Configure Flask to allow frontend requests

### 11.2 Staging Environment
- Deploy to staging server
- Test with sample data
- Performance testing

### 11.3 Production Environment
- Production database setup
- CDN for static assets
- Monitoring and logging
- Backup strategy

---

## 12. Future Enhancements

### 12.1 Advanced Features
- Voice input/output for pronunciation practice
- Character writing practice
- Grammar pattern recognition
- Social features (share progress, compete with friends)
- Gamification (badges, streaks, achievements)

### 12.2 AI Improvements
- Personalized learning paths
- Adaptive difficulty
- Context-aware word suggestions
- Natural conversation practice

### 12.3 Content Expansion
- Sentence pattern practice
- Idiom and chengyu practice
- Business Chinese vocabulary
- Regional dialect support

---

## 13. Success Metrics

### 13.1 User Engagement
- Daily active users
- Average practice sessions per user
- Words practiced per session
- Return rate

### 13.2 Learning Effectiveness
- Average confidence score improvement over time
- Words mastered per user
- Sentence correctness rate
- User retention

### 13.3 Technical Metrics
- API response time
- Error rate
- Uptime
- Database query performance

---

## 14. Open Questions & Decisions Needed

1. **AI Provider**: Which AI service to use? (OpenAI, Anthropic, local model?)
2. **User Model**: Single-user or multi-user with accounts?
3. **Deployment Target**: Web-only or also mobile apps?
4. **Offline Support**: Should app work offline?
5. **Pricing Model**: Free, freemium, or paid?
6. **Data Persistence**: Cloud database or local storage?
7. **Evaluation Depth**: How detailed should feedback be?
8. **Confidence Algorithm**: Simple or spaced repetition (SM-2)?

---

## 15. Project Timeline Summary

**Total Estimated Duration**: 12-17 weeks

- **Phase 1 (MVP)**: 4-6 weeks
- **Phase 2 (Enhanced)**: 3-4 weeks  
- **Phase 3 (Advanced)**: 3-4 weeks
- **Phase 4 (Polish)**: 2-3 weeks

**Recommended Team Size**: 2-3 developers
- 1 Full-stack developer (frontend + backend)
- 1 AI/ML specialist (for evaluation system)
- 1 UI/UX designer (part-time)

---

## 16. Risk Assessment

### 16.1 Technical Risks
- **AI API Costs**: High usage could be expensive
  - *Mitigation*: Implement caching, rate limiting, fallback evaluation
- **Evaluation Accuracy**: AI may not always be accurate
  - *Mitigation*: Combine AI with rule-based checks, allow manual review
- **Chinese Text Handling**: Encoding and input method issues
  - *Mitigation*: Thorough testing, use established libraries

### 16.2 Project Risks
- **Scope Creep**: Feature requests beyond MVP
  - *Mitigation*: Strict phase-based development, prioritize core features
- **Timeline Delays**: Complex features take longer than expected
  - *Mitigation*: Buffer time in estimates, agile development approach

---

This plan provides a comprehensive roadmap for building the Mandarin language learning chatbot application. Each section can be expanded with more specific implementation details as development progresses.

