// 28-day interview-prep plan data, lifted verbatim from the original
// standalone prep28.html so the in-app page renders the exact same content.
// The localStorage schema ("prep28") and task ids (`${day}-${block}-${i}`) are
// preserved so existing progress and the Dashboard widget keep working.

const CIP = "https://www.educative.io/courses/grokking-coding-interview";
const ML = "https://www.educative.io/courses/grokking-the-machine-learning-interview";
const GA = "https://www.educative.io/courses/generative-ai-system-design";
const AI = "https://www.educative.io/courses/ai-engineer-interview-prep";
const M3 = "https://www.educative.io/module/P1vxGOtNzNBPX5PJY/10370001/4640179653312512";
const M5 = "https://www.educative.io/module/P1vxGOtNzNBPX5PJY/10370001/4941132913836032";
const E99 = "https://www.educative.io/path/educative-99-in-python-accelerate-your-coding-interview-prep";

export type PrepTask = { t: string; d: string; u: string };
export type PrepDay = { tag: string; a: PrepTask[]; b: PrepTask[]; r: string[] };

export type BlockKey = "a" | "b" | "r";

export const SESSION_NAMES: Record<BlockKey, string> = {
  a: "Block A · 05:30–08:30 — Coding patterns",
  b: "Block B · 09:30–12:30 — ML / GenAI depth",
  r: "Recall · 22:00–00:00 — eyes closed, no screen",
};

export const PLAN: PrepDay[] = [
  { tag: "Two Pointers", a: [
    { t: "CIP Ch.1 — Two Pointers: easy set", d: "Valid Palindrome · Reverse String · Squares of Sorted Array · Remove Element · Is Subsequence · Merge Strings Alternately. Attempt before revealing.", u: CIP },
    { t: "CIP Ch.1 — medium set", d: "Sort Colors · Reverse Words in a String · Move Zeroes · Remove Duplicates from Sorted Array.", u: CIP }],
    b: [
    { t: "ML Interview Ch.1 — How this course helps", d: "Read the framing lesson first.", u: ML + "/how-does-this-course-help-in-ml-interviews" },
    { t: "Setting Up a Machine Learning System", d: "Memorise the 6-step skeleton: problem → metrics → architecture → data → modelling → evaluation. Write it from memory before closing.", u: ML + "/setting-up-a-machine-learning-system" }],
    r: ["The 6 steps of setting up an ML system, in order.", "What signals a two-pointer problem? (sorted input, pair/triplet, in-place partition, palindrome)", "Walk through Sort Colors out loud — three pointers, and why."] },

  { tag: "Fast & Slow · Linked Lists", a: [
    { t: "CIP Ch.2 — Fast and Slow Pointers (full, 10 problems)", d: "Happy Number · Linked List Cycle I/II · Middle of List · Find Duplicate · Palindrome List · Circular Array Loop. End-of-chapter AI mock.", u: CIP },
    { t: "CIP Ch.5 — In-Place Linked List Manipulation (start)", d: "Reverse a list iteratively without looking, then reverse in groups of k.", u: CIP }],
    b: [
    { t: "Performance and Capacity Considerations", d: "SLA vs capacity tradeoffs; the layered funnel idea (cheap model filters, expensive model ranks).", u: ML + "/performance-and-capacity-considerations" },
    { t: "Training Data Collection Strategies", d: "User feedback, human raters, open data, weak supervision — and how you actually labelled Bhojpuri speech.", u: ML + "/training-data-collection-strategies" }],
    r: ["Floyd's cycle detection — why does the fast pointer meet the slow one?", "Three training-data collection strategies and when each fails.", "Your Bhojpuri data pipeline, start to finish, out loud."] },

  { tag: "Sliding Window", a: [
    { t: "CIP Ch.3 — Sliding Window (full)", d: "Fixed-size first, then variable-size. Longest substring without repeats · Minimum window substring · Longest repeating char replacement. Drill the shrink condition. AI mock.", u: CIP },
    { t: "Finish Ch.5 leftovers", d: "Only if anything remains from yesterday.", u: CIP }],
    b: [
    { t: "Online Experimentation", d: "Hypothesis → A/B design → power/sample size → significance → backtesting. Why offline and online metrics disagree.", u: ML + "/online-experimentation-m2NPGEPwkqn" },
    { t: "Embeddings", d: "Text, user, context embeddings; why two-tower architectures exist; embedding reuse across the funnel.", u: ML + "/embeddings" }],
    r: ["When do you shrink a sliding window vs expand it?", "Design an A/B test for a search-ranking change — metric, guardrails, duration.", "Explain embeddings to a non-ML interviewer in 30 seconds."] },

  { tag: "Hash Maps · Tracking", a: [
    { t: "CIP Ch.23 — Hash Maps (full)", d: "Design HashMap · Two Sum variants · Group Anagrams · Longest Consecutive Sequence · Isomorphic Strings.", u: CIP },
    { t: "CIP Ch.24 — Knowing What to Track (start)", d: "Frequency counting, prefix state, seen-sets. Quietly one of the highest-yield chapters for screens. Both AI mocks if time.", u: CIP }],
    b: [
    { t: "Transfer Learning (fast revision)", d: "You've done the LoRA/QLoRA course — read for interview framing only. Know when transfer learning hurts: domain shift, catastrophic forgetting.", u: ML + "/transfer-learning" },
    { t: "Model Debugging and Testing (the real gap)", d: "Underfitting vs data bug vs leakage vs distribution shift — and the order you'd check.", u: ML + "/model-debugging-and-testing" },
    { t: "Practical ML Techniques — Breakout mock", d: "Run the chapter mock interview.", u: ML + "/practical-ml-techniques-concepts/mock-interview" }],
    r: ["Hash map vs sorting — when is the extra space worth it?", "Full fine-tune vs LoRA vs QLoRA — cost, memory, quality.", "Your model was underperforming. Walk through your debugging order."] },

  { tag: "Stacks", a: [
    { t: "CIP Ch.18 — Stacks (full)", d: "Valid Parentheses · Min Stack · RPN · Daily Temperatures · Next Greater Element · Largest Rectangle (attempt). Internalise the monotonic stack. AI mock.", u: CIP }],
    b: [
    { t: "Search Ranking, part 1 (Ch.3, lessons 1–4)", d: "Problem statement · metrics · architecture · document selection. The retrieval-then-ranking shape generalises to recs, ads, feeds — and RAG.", u: ML }],
    r: ["Monotonic stack — what invariant are you maintaining?", "Search ranking: online vs offline metrics, and why both.", "How is a search-ranking stack structurally the same as a RAG pipeline?"] },

  { tag: "Binary Search · Sorting", a: [
    { t: "CIP Ch.9 — Modified Binary Search (full)", d: "Rotated array search · first/last position · 2D matrix · minimum in rotated. Give binary-search-on-the-answer a full hour (Koko, ship capacity).", u: CIP },
    { t: "CIP Ch.16 — Sort and Search (start)", d: "Begin the chapter.", u: CIP }],
    b: [
    { t: "Search Ranking, part 2 (Ch.3, lessons 5–8)", d: "Feature engineering (actor/query/document/context groups) · training data generation · ranking · filtering.", u: ML },
    { t: "Search Ranking — Breakout mock", d: "Run the mock interview.", u: ML + "/search-ranking/mock-interview" }],
    r: ["Write the binary search template from memory. Off-by-one rules.", "The four feature groups in a ranking system.", "Deliver your 2-minute self-introduction, out loud, cleanly."] },

  { tag: "Consolidation", a: [
    { t: "Timed review — one problem per chapter", d: "Blank editor, 25 min each, from Ch.1, 2, 3, 9, 18, 23. Misses go on the written weak-list.", u: CIP },
    { t: "CIP Ch.29 — Challenge Yourself: 2 problems", d: "Unlabelled, no pattern hints. Calibrate where you actually are.", u: CIP }],
    b: [
    { t: "Handwrite the week", d: "ML setup checklist, search-ranking architecture, four feature groups — by hand, from memory.", u: ML },
    { t: "Search Ranking design, out loud, 20 minutes", d: "Standing, no notes.", u: ML },
    { t: "Sunday admin (30 min)", d: "Tune Educative roadmap from weak-list; confirm the week's application targets; interview slots before 14:00.", u: ML }],
    r: ["Free recall the whole week — every pattern, every ML concept.", "Anything you blank on is Monday's first revision item. Say it, then note it."] },

  { tag: "Tree DFS", a: [
    { t: "CIP Ch.20 — Tree DFS (full)", d: "Pre/in/post-order, recursive then iterative. Path sums · Diameter · Validate BST · LCA · Serialize/Deserialize. AI mock. Recursion fluency is the bottleneck — slow down if shaky.", u: CIP }],
    b: [
    { t: "Ace AI — Course Overview", d: "Start the 34-lesson interview-theory course (Days 8–11).", u: AI + "/course-overview" },
    { t: "Ch.2 — Neural Network Training & Optimization (7 lessons)", d: "Training · Gradient Descent · Transfer Learning · Model Alignment · Model Compression · Fine-Tuning · Synthetic Data. Alignment + synthetic data are your genuinely new material.", u: AI + "/neural-networks-training" }],
    r: ["Backprop in 90 seconds, out loud.", "Three tree traversals — when would you pick each?", "Why did ReLU beat sigmoid? Why did GELU beat ReLU in transformers?"] },

  { tag: "Tree BFS", a: [
    { t: "CIP Ch.21 — Tree BFS (full)", d: "Level order · Zigzag · Right side view · Connect siblings · Minimum depth. AI mock.", u: CIP },
    { t: "Finish Ch.16 — Sort and Search", d: "Close out the chapter.", u: CIP }],
    b: [
    { t: "Ace AI Ch.3 — Embeddings and Tokenization (3 lessons)", d: "Includes beam search and decoding: greedy, beam, top-k, top-p, temperature — frequently asked, rarely prepared.", u: AI },
    { t: "Ace AI Ch.4 — Attention Mechanisms (6 lessons)", d: "Self-attention, cross-attention, flash attention, normalisation. Know why transformers use layer norm, not batch norm.", u: AI }],
    r: ["BFS vs DFS on a tree — which problems demand which?", "Adam vs SGD, in one clean paragraph.", "Why layer norm in transformers? Why did RNNs lose?"] },

  { tag: "Heaps · Top K", a: [
    { t: "CIP Ch.8 — Top K Elements (full)", d: "Kth largest · Top k frequent · K closest points · Kth largest in a stream. heapq cold, including the negation trick.", u: CIP },
    { t: "CIP Ch.6 — Two Heaps", d: "Median from data stream · Sliding window median · IPO.", u: CIP }],
    b: [
    { t: "Ace AI Ch.5 — Evaluation Techniques (2 lessons)", d: "Perplexity, BLEU, ROUGE — and when automated metrics are useless.", u: AI },
    { t: "Ace AI Ch.6 — Model Architectures & Comparisons (7 lessons)", d: "Model selection, scaling laws, interpretability, hallucinations, jailbreaks. Scaling laws + interpretability separate you from builders-only candidates.", u: AI }],
    r: ["Heap vs sorting vs quickselect for Top-K — complexity of each.", "BLEU vs ROUGE vs human eval — when does each break?", "How would you evaluate your Bhojpuri ASR beyond WER?"] },

  { tag: "Graphs", a: [
    { t: "CIP Ch.19 — Graphs (full)", d: "Adjacency list from edge list — build it from memory every time. Number of Islands · Clone Graph · Course Schedule · Word Ladder · Rotting Oranges. AI mock.", u: CIP }],
    b: [
    { t: "Ace AI Ch.7 — Learning Techniques (4 lessons)", d: "RAG (fast — you've done four RAG courses), few-shot, chain-of-thought.", u: AI },
    { t: "Ace AI Ch.8 — Scalability & Efficiency (3 lessons)", d: "Mixture of Experts, vector DBs, agentic failure modes. Slow down on MoE and agent errors — genuinely new.", u: AI },
    { t: "Ch.9 Wrap Up + Fundamentals of Generative AI mock", d: "Course complete: 34 lessons in four sessions.", u: AI + "/fundamentals-of-generative-ai/mock-interview" }],
    r: ["Mixture of Experts in one minute — routing, why it scales.", "An agentic failure mode you've actually hit, and the fix.", "What is a KV cache actually caching, and why does it matter for cost?"] },

  { tag: "Topological Sort · Union Find", a: [
    { t: "CIP Ch.15 — Topological Sort (full)", d: "Course Schedule I/II · Alien Dictionary · dependency scheduling.", u: CIP },
    { t: "CIP Ch.25 — Union Find (full)", d: "Redundant Connection · Provinces · Accounts Merge. Memorise the 12-line template: path compression + union by rank.", u: CIP }],
    b: [
    { t: "GenAI SD Ch.1 — Introduction", d: "Start the system-design course.", u: GA + "/introduction-to-generative-ai-system-design" },
    { t: "Ch.2 — Fundamental Concepts (5 lessons)", d: "Skim overlaps; the new material is parallelism (data/tensor/pipeline/model) and inference optimisation (quantisation, distillation, KV cache, batching, speculative decoding).", u: GA + "/parallelism-in-genai-models" },
    { t: "RAG and Finetuning — Breakout mock", d: "Your single most likely interview question. You should be unusually strong here.", u: GA + "/rag-and-finetuning/mock-interview" }],
    r: ["Four parallelism strategies — one line each.", "RAG or fine-tuning? The decision rule, then three cases where you'd use both.", "Union-Find template from memory."] },

  { tag: "Intervals · Cyclic Sort", a: [
    { t: "CIP Ch.4 — Intervals (full)", d: "Merge · Insert · Intersections · Meeting Rooms II · Employee Free Time. AI mock.", u: CIP },
    { t: "CIP Ch.14 — Cyclic Sort", d: "Missing Number · Find All Duplicates · First Missing Positive. AI mock.", u: CIP }],
    b: [
    { t: "GenAI SD Ch.3 + Ch.4 — Back-of-envelope + SCALED", d: "Finish the calculations lessons; memorise the SCALED 6-step framework as your spine.", u: GA },
    { t: "Ch.11 — RAG System Design (2 lessons)", d: "You know RAG building; add the design layer — sizing, latency budgets, throughput, cost per 1,000 queries, failure modes.", u: GA },
    { t: "Prepare: when does a knowledge graph beat a vector store?", d: "2-minute answer from your Neo4j GraphRAG course. Almost no candidate can answer this.", u: GA }],
    r: ["Recite SCALED in order, then design a RAG pipeline with it, out loud.", "When does a knowledge graph beat a vector store? Two minutes.", "Estimate the cost of serving 10,000 daily users on a 7B model — rough numbers, out loud."] },

  { tag: "Timed simulation", a: [
    { t: "CIP Ch.29 — 3 problems, 90 minutes, timed", d: "Clock visible, no hints, no lookups. Then 60 min reviewing only the misses — hunt pattern misidentification, not syntax.", u: CIP },
    { t: "Update the weak-list", d: "Rebuild it from today's evidence.", u: CIP }],
    b: [
    { t: "Project narrative build (90 min)", d: "Write then rehearse: Bhojpuri STT (data, model choice, 13.70% WER, what broke) · RAG/agent work as design decisions · hindi-form-agent · deal-hunter-india.", u: ML },
    { t: "Paper narrative (30 min)", d: "TADT: 60-second and 5-minute versions. Always 'under peer review at Wireless Personal Communications' — never 'published'.", u: ML },
    { t: "Weekly application review", d: "Pipeline check; interview slots before 14:00.", u: ML }],
    r: ["Deliver the Bhojpuri project narrative, out loud, twice.", "Deliver the paper narrative — 60-second version, then the 5-minute version.", "Free recall the full week."] },

  { tag: "Subsets", a: [
    { t: "CIP Ch.10 — Subsets (full)", d: "Subsets I/II · Permutations · Combinations · Letter Combinations. Recursion tree on paper before code, every time. AI mock.", u: CIP }],
    b: [
    { t: "GenAI SD Ch.5 — Text-to-Text System (2 lessons)", d: "Training architecture, then deployment. Own the pipeline: pre-training → SFT → RLHF/DPO → serving → safety → feedback loop.", u: GA },
    { t: "ChatGPT — mock interview", d: "The flagship GenAI design question.", u: GA + "/chatgpt-genai/mock-interview" }],
    r: ["Design ChatGPT, out loud, using SCALED. Ten minutes, no notes.", "The subsets recursion template from memory.", "SFT vs RLHF vs DPO — one line each."] },

  { tag: "Backtracking", a: [
    { t: "CIP Ch.12 — Backtracking (full)", d: "N-Queens · Word Search · Sudoku · Palindrome Partitioning · Combination Sum. Choose → explore → un-choose, plus pruning — interviewers probe pruning. AI mock.", u: CIP }],
    b: [
    { t: "GenAI SD Ch.10 — Automatic Speech Recognition SD", d: "Maps directly onto your internship. Reframe the Bhojpuri pipeline in this design vocabulary — internship work becomes a senior-sounding answer.", u: GA },
    { t: "Ch.7 — Text-to-Speech + ElevenLabs mock", d: "2 lessons, then the mock.", u: GA + "/elevenlabs/mock-interview" }],
    r: ["Design an ASR system for a low-resource language, out loud.", "How does your actual Bhojpuri pipeline differ from the reference design — and why?", "Backtracking skeleton from memory."] },

  { tag: "Dynamic Programming I", a: [
    { t: "CIP Ch.13 — DP part 1: 1-D only", d: "Climbing Stairs · House Robber I/II · Coin Change · LIS · Word Break · Decode Ways. Brute force → memoise → tabulate, all three steps, every problem. That progression IS the skill.", u: CIP }],
    b: [
    { t: "ML Ch.5 — Recommendation System (7 lessons)", d: "Candidate generation → ranking → re-ranking. Collaborative vs content, matrix factorisation, two-tower, cold start, feedback loops. The most-asked ML design question in India.", u: ML },
    { t: "Movie/Show Recommendation — Breakout mock", d: "Run it.", u: ML + "/movie-show-recommendation-system/mock-interview" }],
    r: ["State the DP transition for Coin Change, out loud.", "Design a recommendation system in 10 minutes, no notes.", "How would you handle cold start for a brand-new user?"] },

  { tag: "Dynamic Programming II", a: [
    { t: "CIP Ch.13 — DP part 2: 2-D", d: "Unique Paths · Min Path Sum · LCS · Edit Distance · 0/1 Knapsack · Target Sum. Then the Ch.13 AI mock. Two full DP days is deliberate — don't compress.", u: CIP }],
    b: [
    { t: "ML Ch.8 — Ad Prediction System (7 lessons)", d: "Calibration, CTR, auction dynamics, online learning, extreme class imbalance. Three imbalance techniques with tradeoffs — a near-guaranteed follow-up.", u: ML },
    { t: "Ad Prediction Problem — Breakout mock", d: "Run it.", u: ML + "/ad-prediction-problem/mock-interview" }],
    r: ["Edit distance — the recurrence, out loud.", "Three ways to handle severe class imbalance, and when each is wrong.", "What is model calibration and why does it matter for ads?"] },

  { tag: "Greedy · Matrices", a: [
    { t: "CIP Ch.11 — Greedy Techniques (full)", d: "Jump Game I/II · Gas Station · Task Scheduler · Partition Labels. Always be ready to say WHY the greedy choice is safe.", u: CIP },
    { t: "CIP Ch.17 — Matrices", d: "Rotate Image · Spiral Matrix · Set Matrix Zeroes · Game of Life.", u: CIP }],
    b: [
    { t: "ML Ch.9 — Fraud Detection (5 lessons)", d: "Imbalance-heavy, real-time constrained. Note what's shared: feature stores, streaming inference, thresholds, human-in-the-loop.", u: ML },
    { t: "Ch.10 — Hate Speech Detection + mock", d: "5 lessons, then the Harmful Content Detection mock.", u: ML + "/harmful-content-detection-system/mock-interview" }],
    r: ["When is a greedy choice provably safe? One example, one counter-example.", "Design a real-time fraud detection system, out loud.", "Precision/recall tradeoff for content moderation — which way do you err, and why?"] },

  { tag: "Tries · Bitwise · Agentic patterns", a: [
    { t: "CIP Ch.22 — Trie", d: "Implement Trie · Word Search II · Autocomplete.", u: CIP },
    { t: "CIP Ch.27 Bitwise + Ch.28 Math (timeboxed skim)", d: "Single Number · Counting Bits · Reverse Bits. Lower-yield — strict timebox.", u: CIP }],
    b: [
    { t: "GenAI SD Ch.6 — Text-to-Image + DALL·E mock", d: "2 lessons + mock. Then Ch.12 Conclusion. Skip text-to-video and captioning unless a JD names them. Course complete.", u: GA + "/dall-e/mock-interview" },
    { t: "Agentic AI Expert — Module 3: Agentic Design Patterns", d: "Routing · parallelisation · orchestrator-worker · evaluator-optimiser. You build agents; this gives you the naming. For each pattern, one line on where you've used it.", u: M3 }],
    r: ["Name the four agentic design patterns and give one use case each.", "Which pattern did your own agent work actually use? Say it in pattern language.", "Diffusion vs autoregressive generation — the tradeoff."] },

  { tag: "Timed simulation II · Agentic SD", a: [
    { t: "CIP Ch.29 — 4 problems, 2 hours, timed", d: "Compare with Day 14. The metric is time-to-correct-pattern-identification, not completion.", u: CIP },
    { t: "Rebuild the weak-list from scratch", d: "This version drives all of Week 4.", u: CIP }],
    b: [
    { t: "Agentic AI Expert — Module 5: Agentic System Design (~90 min)", d: "Guardrails, failure containment, NVIDIA Eureka. Have a real answer for looping agents, hallucinated tool calls, runaway cost.", u: M5 },
    { t: "45-min ML design mock, out loud, standing", d: "Pick one un-rehearsed: Feed Based System, Entity Linking, or Dynamic Pricing. Mark every gap against the chapter.", u: ML },
    { t: "Sunday admin", d: "Application review; slots before 14:00.", u: ML }],
    r: ["Free recall the entire three weeks — patterns, ML systems, GenAI systems.", "Whatever you blank on becomes Week 4's syllabus. Say it, note it."] },

  { tag: "Weak-list patch I · Behavioural", a: [
    { t: "Weak patterns #1 and #2 — targeted repair", d: "Re-read each chapter intro, re-solve 6 problems each, blank editor, 25-min cap. Still shaky → 'declare and redirect' list.", u: CIP }],
    b: [
    { t: "STAR bank — 6 stories", d: "Conflict, failure, ownership, ambiguity, learning speed, disagreement.", u: ML },
    { t: "Resume walkthrough, timed to 3 minutes", d: "M.Tech (AI) → internship work → certifications → paper → what you want next. Consistency check: reason-for-leaving and 3-year answers must match everywhere.", u: ML }],
    r: ["The 3-minute resume walkthrough, out loud, twice.", "Two STAR stories, out loud.", "'Why are you leaving?' and 'Where in three years?' — smooth, no hesitation."] },

  { tag: "Mock — technical screen", a: [
    { t: "Two back-to-back 60-min AI mock interviews", d: "Talk aloud while coding. No break between — Indian loops run back-to-back and fatigue tolerance matters.", u: CIP },
    { t: "Weak patterns #3 and #4", d: "4 problems each.", u: CIP }],
    b: [
    { t: "Machine Learning Fundamentals — mock interview", d: "Run it.", u: ML + "/machine-learning-fundamentals/mock-interview" },
    { t: "Rapid-fire self-quiz, 60 seconds per answer, spoken", d: "Bias-variance · regularisation · precision/recall · ROC vs PR AUC · overfitting fixes · CV · bagging vs boosting · GD variants · attention · tokenisation · quantisation · LoRA. Over 60s → re-drill tomorrow.", u: AI }],
    r: ["Re-answer every rapid-fire question you fumbled.", "Replay the mock in your head — where did you go quiet? Quiet loses offers."] },

  { tag: "Mock — ML depth", a: [
    { t: "Weak patterns #5 and #6 + 1 AI mock", d: "6 problems each, timed. Then re-solve your 3 most-failed problems of the month from a blank editor.", u: CIP }],
    b: [
    { t: "Two 45-min design mocks, back to back", d: "Visual Search · ETA · People You May Know · Fraud Detection — pick two untouched. Record one on your phone.", u: ML + "/visual-search-system-design/mock-interview" },
    { t: "Playback the recording", d: "Listen for filler, unstructured openings, and skipped requirement-gathering — the most skipped, most weighted step.", u: ML }],
    r: ["Replay your recorded mock mentally — three things to fix.", "Re-deliver the opening 2 minutes of a system design answer, cleanly."] },

  { tag: "Mock — GenAI design", a: [
    { t: "Ch.29 or Educative-99 — 3 problems, 75 min, timed", d: "If Ch.29 is exhausted, draw from Educative-99 (same patterns, fresh problems). Target: pattern identified within 5 minutes on a medium.", u: E99 }],
    b: [
    { t: "Run the skipped GenAI mocks", d: "ChatGPT · RAG and Finetuning · ElevenLabs.", u: GA + "/chatgpt-genai/mock-interview" },
    { t: "Self-designed: multilingual voice assistant for low-resource Indian languages", d: "Use SCALED. Sits precisely at ASR × RAG × fine-tuning — the single best question you could be asked. Prepare it as a story to steer interviews toward.", u: GA }],
    r: ["Deliver the multilingual voice assistant design, out loud, end to end.", "Where in that design does your actual internship experience slot in?"] },

  { tag: "Paper defence", a: [
    { t: "2 problems, 50 minutes, timed", d: "Maintaining sharpness, not building it. Then read-only review of your 5 hardest patterns.", u: CIP }],
    b: [
    { t: "TADT full defence rehearsal", d: "Why BQPSO over PSO/GA · why a digital twin layer · baselines · significance · limitations · real IoV latency. Name your own limitations — it earns respect. Status: under peer review at Wireless Personal Communications, never 'published'.", u: ML },
    { t: "'Walk me through your M.Tech thesis' — 5-minute answer", d: "Rehearse it twice.", u: ML }],
    r: ["The full paper defence, out loud, including the limitations.", "The 60-second version. Then the 5-minute version."] },

  { tag: "Full loop simulation", a: [
    { t: "Round 1: 60-min coding, 2 problems, talking aloud", d: "Then a 10-minute break, exactly like a real call.", u: CIP },
    { t: "Round 2: 45-min ML fundamentals rapid-fire", d: "No lookups at any point today.", u: ML }],
    b: [
    { t: "Round 3: 45-min ML or GenAI system design, out loud", d: "Full structure: requirements → metrics → design → tradeoffs.", u: GA },
    { t: "Round 4: 30-min behavioural + written self-assessment", d: "STAR stories, resume walkthrough, then: what would have cost you the offer? Fix the top two tomorrow. Prepare 5 questions for the interviewer.", u: ML }],
    r: ["Free recall the whole loop. Where did you lose energy or structure?", "Rehearse your 5 questions for the interviewer."] },

  { tag: "Taper & readiness", a: [
    { t: "1 easy + 1 medium, untimed", d: "Purely to stay warm. Read your pattern-signal notes — reading only. Cramming today costs more than it gains.", u: CIP }],
    b: [
    { t: "Final narrative pass", d: "Resume walkthrough · Bhojpuri project · paper · 'why this company' template.", u: ML },
    { t: "Logistics check", d: "Camera, mic, lighting, connection, quiet window before 14:00, IDE set to Python, notes closed. Write one page: what you know now that you didn't 28 days ago.", u: ML }],
    r: ["Nothing structured tonight. Rest properly.", "If you want one thing: the 2-minute self-introduction, once. Then sleep."] },
];

// ---- recall-coach prompt builders (kept identical to the original) ----
export function recallPrompt(topic: string, day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my 28-day plan, night session — eyes-closed retrieval practice.\n\nTopic: "${topic}"\n\nAsk me one question at a time on this topic and wait for my answer. After each answer: briefly correct anything wrong, then ask one deeper follow-up. Keep your replies to 2–3 sentences — this is spoken-style practice, not an essay. Start now with your first question.`;
}

export function recallAll(items: string[], day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my 28-day plan, night session — eyes-closed retrieval practice before sleep.\n\nRun me through these topics IN ORDER, one at a time:\n${items.map((x, i) => `${i + 1}. ${x}`).join("\n")}\n\nFor each topic: ask me to explain it from memory, wait for my answer, correct briefly, one follow-up, then move to the next topic. Keep every reply to 2–3 sentences. If I blank on something, tell me it goes on tomorrow's revision list and move on. Start with topic 1.`;
}
