// Interview-prep plan data. The syllabus is authored as units of chapters that
// share a set of recall topics; the plan the app renders (PLAN) is derived from
// it so that every day holds exactly one chapter, three easy coding problems,
// and its share of that unit's recall topics.

const CIP = "https://www.educative.io/courses/grokking-coding-interview";
const GA = "https://www.educative.io/courses/generative-ai-system-design";
const AI = "https://www.educative.io/courses/ai-engineer-interview-prep";
const M3 = "https://www.educative.io/module/P1vxGOtNzNBPX5PJY/10370001/4640179653312512";

export type PrepTask = { t: string; d: string; u: string };
export type PrepDay = { tag: string; a: PrepTask[]; b: PrepTask[]; r: string[] };

export type BlockKey = "a" | "b" | "r";

export const SESSION_NAMES: Record<BlockKey, string> = {
  a: "Block A · 05:30–08:30 — Coding: three easy problems",
  b: "Block B · 09:30–12:30 — AI / GenAI study & build",
  r: "Recall · 22:00–00:00 — eyes closed, no screen",
};

// ---- study syllabus -------------------------------------------------------
// One chapter becomes one day. A unit's recall topics are split across the days
// its chapters occupy.
type StudyUnit = { b: PrepTask[]; r: string[] };

const SYLLABUS: StudyUnit[] = [
  { b: [
    { t: "Ace AI — Course Overview", d: "Start the 34-lesson interview-theory course.", u: AI + "/course-overview" },
    { t: "Ch.2 — Neural Network Training & Optimization (7 lessons)", d: "Training · Gradient Descent · Transfer Learning · Model Alignment · Model Compression · Fine-Tuning · Synthetic Data. Alignment + synthetic data are your genuinely new material.", u: AI + "/neural-networks-training" }],
    r: ["Backprop in 90 seconds, out loud.", "Three tree traversals — when would you pick each?", "Why did ReLU beat sigmoid? Why did GELU beat ReLU in transformers?"] },

  { b: [
    { t: "Ace AI Ch.3 — Embeddings and Tokenization (3 lessons)", d: "Includes beam search and decoding: greedy, beam, top-k, top-p, temperature — frequently asked, rarely prepared.", u: AI },
    { t: "Ace AI Ch.4 — Attention Mechanisms (6 lessons)", d: "Self-attention, cross-attention, flash attention, normalisation. Know why transformers use layer norm, not batch norm.", u: AI }],
    r: ["BFS vs DFS on a tree — which problems demand which?", "Adam vs SGD, in one clean paragraph.", "Why layer norm in transformers? Why did RNNs lose?"] },

  { b: [
    { t: "Ace AI Ch.5 — Evaluation Techniques (2 lessons)", d: "Perplexity, BLEU, ROUGE — and when automated metrics are useless.", u: AI },
    { t: "Ace AI Ch.6 — Model Architectures & Comparisons (7 lessons)", d: "Model selection, scaling laws, interpretability, hallucinations, jailbreaks. Scaling laws + interpretability separate you from builders-only candidates.", u: AI }],
    r: ["Heap vs sorting vs quickselect for Top-K — complexity of each.", "BLEU vs ROUGE vs human eval — when does each break?", "How would you evaluate your Bhojpuri ASR beyond WER?"] },

  { b: [
    { t: "Ace AI Ch.7 — Learning Techniques (4 lessons)", d: "RAG (fast — you've done four RAG courses), few-shot, chain-of-thought.", u: AI },
    { t: "Ace AI Ch.8 — Scalability & Efficiency (3 lessons)", d: "Mixture of Experts, vector DBs, agentic failure modes. Slow down on MoE and agent errors — genuinely new.", u: AI },
    { t: "Ch.9 Wrap Up + Fundamentals of Generative AI mock", d: "Course complete: 34 lessons in four sessions.", u: AI + "/fundamentals-of-generative-ai/mock-interview" }],
    r: ["Mixture of Experts in one minute — routing, why it scales.", "An agentic failure mode you've actually hit, and the fix.", "What is a KV cache actually caching, and why does it matter for cost?"] },

  { b: [
    { t: "Consolidation + admin (30 min)", d: "Tune the Educative roadmap from your weak-list; confirm the week's application targets; interview slots before 14:00.", u: AI }],
    r: ["Free recall the whole week — every pattern, every concept.", "Anything you blank on is tomorrow's first revision item. Say it, then note it."] },

  { b: [
    { t: "GenAI Ch.2 — Fundamental Concepts (5 lessons)", d: "Parallelism (data/tensor/pipeline/model) and inference optimisation: quantisation, distillation, KV cache, batching, speculative decoding. Fundamentals, not system design — these come up in screens.", u: GA + "/parallelism-in-genai-models" },
    { t: "RAG and Finetuning — Breakout mock", d: "Your single most likely interview question. You should be unusually strong here.", u: GA + "/rag-and-finetuning/mock-interview" }],
    r: ["Four parallelism strategies — one line each.", "RAG or fine-tuning? The decision rule, then three cases where you'd use both.", "Union-Find template from memory."] },

  { b: [
    { t: "Prepare: when does a knowledge graph beat a vector store?", d: "2-minute answer from your Neo4j GraphRAG course. Almost no candidate can answer this.", u: GA }],
    r: ["When does a knowledge graph beat a vector store? Two minutes."] },

  // ---- build track: what the practical/take-home round actually tests ----
  { b: [
    { t: "Portfolio audit — pick the three projects", d: "List everything you've built. Pick three to show: the RAG app, an end-to-end ML pipeline, and one deployed service. For each, write down what's missing — README, real numbers, a public URL.", u: "" },
    { t: "RAG app: repo cleanup", d: "README with problem → architecture → results → how to run. Pin requirements, add .env.example, delete dead code and notebooks nobody will read.", u: "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes" },
    { t: "RAG app: architecture write-up + diagram", d: "300 words and one diagram: chunking strategy, embedding model, hybrid dense + BM25 with RRF, and why each choice. This is your answer to 'walk me through your project'.", u: "" },
    { t: "RAG app: put real evaluation numbers in the README", d: "Run RAGAS — faithfulness, answer relevancy, context precision — and publish the scores. Concrete numbers beat 'it works well' in every interview.", u: "https://docs.ragas.io" },
    { t: "RAG app: deploy to a free tier and link it", d: "Get a public URL (Hugging Face Spaces, Render or Vercel). Put it at the top of the README and on your resume — a live link is the strongest fresher signal there is.", u: "https://huggingface.co/docs/hub/spaces" }],
    r: ["Walk through your RAG app's retrieval choice out loud — why hybrid, why RRF.", "Describe your chunking strategy, and what you'd change if the documents doubled in size.", "Say your RAGAS numbers from memory, and what each metric actually measures.", "Your live demo is down five minutes before a call. What do you say?", "Pitch the RAG app in 60 seconds: problem, approach, result."] },

  { b: [
    { t: "End-to-end ML pipeline: scope it", d: "Pick one dataset and define the whole path: ingest → features → train → evaluate → serve. Small and finished beats ambitious and abandoned.", u: "" },
    { t: "Pipeline: reproducible training + evaluation", d: "One command trains and prints metrics. Fix the seed, log the run, commit the metrics file. Reproducibility is what separates a project from a notebook.", u: "" },
    { t: "Pipeline: serve it behind FastAPI", d: "A /predict endpoint with request validation and a health check. This shape is exactly what the practical round asks for.", u: "https://fastapi.tiangolo.com" },
    { t: "Containerise it", d: "A Dockerfile that builds clean from scratch and runs with one command. Be ready to explain the layers and why the build is ordered the way it is.", u: "https://docs.docker.com" },
    { t: "Add CI and basic monitoring", d: "A GitHub Actions workflow that lints and tests on push. Then log request latency and add one data-quality check — so you can say what you'd monitor in production and what you'd alert on.", u: "https://docs.github.com/en/actions" }],
    r: ["Walk through your pipeline end to end, out loud, in 90 seconds.", "What makes a training run reproducible? Name every knob you had to pin.", "What breaks first when your API gets 100 requests a second?", "Explain your Dockerfile's layer order and why it caches the way it does.", "What would you monitor in production, and what would you alert on?"] },

  { b: [
    { t: "GitHub hygiene pass", d: "Pin the three projects. Real commit history, not one 'initial commit' dump. A profile README that says what you build. Unpin tutorial clones — recruiters do look.", u: "" },
    { t: "Timed take-home dry run (3 hours)", d: "Give yourself a realistic brief — 'build a small RAG over these documents, expose it behind an API' — and ship it in three hours, clock visible. Then review only what slowed you down.", u: "" }],
    r: ["What slowed you down in the dry run? Name the top two, and fix them tomorrow.", "Pitch your three projects in 60 seconds total — one line each."] },

  { b: [
    { t: "Project narrative build (90 min)", d: "Write then rehearse: Bhojpuri STT (data, model choice, 13.70% WER, what broke) · RAG/agent work as design decisions · hindi-form-agent · deal-hunter-india.", u: AI },
    { t: "Paper narrative (30 min)", d: "TADT: 60-second and 5-minute versions. Always 'under peer review at Wireless Personal Communications' — never 'published'.", u: AI },
    { t: "Weekly application review", d: "Pipeline check; interview slots before 14:00.", u: AI }],
    r: ["Deliver the Bhojpuri project narrative, out loud, twice.", "Deliver the paper narrative — 60-second version, then the 5-minute version.", "Free recall the full week."] },

  { b: [
    { t: "Agentic AI Expert — Module 3: Agentic Design Patterns", d: "Routing · parallelisation · orchestrator-worker · evaluator-optimiser. You build agents; this gives you the naming. For each pattern, one line on where you've used it.", u: M3 }],
    r: ["Name the four agentic design patterns and give one use case each.", "Which pattern did your own agent work actually use? Say it in pattern language."] },

  { b: [
    { t: "Sunday admin", d: "Application review; slots before 14:00.", u: AI }],
    r: ["Free recall the whole stretch — every pattern, every concept, every project.", "Whatever you blank on becomes next week's syllabus. Say it, note it."] },

  { b: [
    { t: "STAR bank — 6 stories", d: "Conflict, failure, ownership, ambiguity, learning speed, disagreement.", u: AI },
    { t: "Resume walkthrough, timed to 3 minutes", d: "M.Tech (AI) → internship work → certifications → paper → what you want next. Consistency check: reason-for-leaving and 3-year answers must match everywhere.", u: AI }],
    r: ["The 3-minute resume walkthrough, out loud, twice.", "Two STAR stories, out loud.", "'Why are you leaving?' and 'Where in three years?' — smooth, no hesitation."] },

  { b: [
    { t: "Rapid-fire self-quiz, 60 seconds per answer, spoken", d: "Bias-variance · regularisation · precision/recall · ROC vs PR AUC · overfitting fixes · CV · bagging vs boosting · GD variants · attention · tokenisation · quantisation · LoRA. Over 60s → re-drill tomorrow.", u: AI }],
    r: ["Re-answer every rapid-fire question you fumbled.", "Replay your last mock in your head — where did you go quiet? Quiet loses offers."] },

  { b: [
    { t: "TADT full defence rehearsal", d: "Why BQPSO over PSO/GA · why a digital twin layer · baselines · significance · limitations · real IoV latency. Name your own limitations — it earns respect. Status: under peer review at Wireless Personal Communications, never 'published'.", u: AI },
    { t: "'Walk me through your M.Tech thesis' — 5-minute answer", d: "Rehearse it twice.", u: AI }],
    r: ["The full paper defence, out loud, including the limitations.", "The 60-second version. Then the 5-minute version."] },

  { b: [
    { t: "Round 4: 30-min behavioural + written self-assessment", d: "STAR stories, resume walkthrough, then: what would have cost you the offer? Fix the top two tomorrow. Prepare 5 questions for the interviewer.", u: AI }],
    r: ["Free recall the whole loop. Where did you lose energy or structure?", "Rehearse your 5 questions for the interviewer."] },

  { b: [
    { t: "Final narrative pass", d: "Resume walkthrough · Bhojpuri project · paper · 'why this company' template.", u: AI },
    { t: "Logistics check", d: "Camera, mic, lighting, connection, quiet window before 14:00, IDE set to Python, notes closed. Write one page: what you know now that you didn't on Day 1.", u: AI }],
    r: ["Nothing structured tonight. Rest properly.", "If you want one thing: the 2-minute self-introduction, once. Then sleep."] },
];

// ---- coding block ---------------------------------------------------------
// Three easy problems a day, one pattern per day. Day N takes entry N, so the
// day's tag names the pattern being drilled.
type CodingDay = { tag: string; d: string; easy: string[] };

const CODING: CodingDay[] = [
  { tag: "Two Pointers", d: "Two pointers from opposite ends. Attempt each before revealing the solution.", easy: ["Valid Palindrome", "Reverse String", "Squares of a Sorted Array"] },
  { tag: "Two Pointers · II", d: "In-place partitioning — write from the back when overwriting.", easy: ["Merge Sorted Array", "Remove Element", "Move Zeroes"] },
  { tag: "Two Pointers · III", d: "Same-direction pointers over sorted input.", easy: ["Is Subsequence", "Remove Duplicates from Sorted Array", "Intersection of Two Arrays II"] },
  { tag: "Fast & Slow Pointers", d: "Floyd's cycle detection. Say out loud why the pointers meet.", easy: ["Linked List Cycle", "Middle of the Linked List", "Happy Number"] },
  { tag: "Linked Lists", d: "Pointer rewiring. Draw the nodes before writing code.", easy: ["Reverse Linked List", "Merge Two Sorted Lists", "Remove Duplicates from Sorted List"] },
  { tag: "Linked Lists · II", d: "Dummy-head trick; two passes are fine.", easy: ["Remove Linked List Elements", "Palindrome Linked List", "Intersection of Two Linked Lists"] },
  { tag: "Sliding Window", d: "Fixed-size window first. Know what shrinks the window and why.", easy: ["Maximum Average Subarray I", "Contains Duplicate II", "Longest Harmonious Subsequence"] },
  { tag: "Prefix Sums", d: "Precompute once, answer ranges in O(1).", easy: ["Running Sum of 1d Array", "Find Pivot Index", "Range Sum Query - Immutable"] },
  { tag: "Hash Maps", d: "Trade space for a single pass.", easy: ["Two Sum", "Valid Anagram", "Contains Duplicate"] },
  { tag: "Hash Maps · II", d: "Frequency counting and seen-sets.", easy: ["Ransom Note", "First Unique Character in a String", "Intersection of Two Arrays"] },
  { tag: "Strings", d: "Index arithmetic — watch the boundaries.", easy: ["Longest Common Prefix", "Length of Last Word", "Find the Index of the First Occurrence in a String"] },
  { tag: "Strings · II", d: "Split, reverse, compare. Keep it O(n).", easy: ["Reverse Words in a String III", "Detect Capital", "Repeated Substring Pattern"] },
  { tag: "Stacks", d: "LIFO state. Internalise the monotonic-stack shape.", easy: ["Valid Parentheses", "Min Stack", "Baseball Game"] },
  { tag: "Queues & Design", d: "Amortised cost — explain why the average case holds.", easy: ["Implement Queue using Stacks", "Implement Stack using Queues", "Number of Recent Calls"] },
  { tag: "Binary Search", d: "Write the template from memory. Nail the off-by-one rules.", easy: ["Binary Search", "Search Insert Position", "First Bad Version"] },
  { tag: "Binary Search · II", d: "Binary search on the answer, not the array.", easy: ["Sqrt(x)", "Valid Perfect Square", "Guess Number Higher or Lower"] },
  { tag: "Sorting", d: "Know what the sort costs before you reach for it.", easy: ["Sort Array By Parity", "Height Checker", "Majority Element"] },
  { tag: "Tree DFS", d: "Recursive first, then say what the iterative version would look like.", easy: ["Maximum Depth of Binary Tree", "Same Tree", "Path Sum"] },
  { tag: "Tree DFS · II", d: "Return values up the recursion — decide what each call returns.", easy: ["Invert Binary Tree", "Symmetric Tree", "Diameter of Binary Tree"] },
  { tag: "Tree DFS · III", d: "Carry state down, aggregate on the way back up.", easy: ["Merge Two Binary Trees", "Sum of Left Leaves", "Binary Tree Paths"] },
  { tag: "Tree BFS", d: "Level-order with a queue; track the level size.", easy: ["Average of Levels in Binary Tree", "Minimum Depth of Binary Tree", "Binary Tree Inorder Traversal"] },
  { tag: "Binary Search Trees", d: "Use the BST invariant — never scan the whole tree.", easy: ["Search in a Binary Search Tree", "Range Sum of BST", "Minimum Absolute Difference in BST"] },
  { tag: "Binary Search Trees · II", d: "In-order traversal of a BST is sorted. Use that.", easy: ["Convert Sorted Array to Binary Search Tree", "Two Sum IV - Input is a BST", "Increasing Order Search Tree"] },
  { tag: "Heaps · Top K", d: "heapq cold, including the negation trick for max-heaps.", easy: ["Kth Largest Element in a Stream", "Last Stone Weight", "Relative Ranks"] },
  { tag: "Graphs", d: "Build the adjacency list from memory every time.", easy: ["Flood Fill", "Island Perimeter", "Find the Town Judge"] },
  { tag: "Graphs · II", d: "BFS or DFS over nodes — state the visited-set rule first.", easy: ["Find if Path Exists in Graph", "Find Center of Star Graph", "Destination City"] },
  { tag: "Intervals", d: "Sort by start, then compare against the previous end.", easy: ["Summary Ranges", "Teemo Attacking", "Can Place Flowers"] },
  { tag: "Cyclic Sort · Missing Numbers", d: "Values map to indices — place each number where it belongs.", easy: ["Missing Number", "Find All Numbers Disappeared in an Array", "Single Number"] },
  { tag: "Bit Manipulation", d: "XOR, masks and shifts. Say what each bit means.", easy: ["Number of 1 Bits", "Counting Bits", "Reverse Bits"] },
  { tag: "Bit Manipulation · II", d: "Powers of two and the n & (n-1) trick.", easy: ["Power of Two", "Power of Four", "Complement of Base 10 Integer"] },
  { tag: "Math", d: "Digit handling without converting to strings where you can.", easy: ["Palindrome Number", "Roman to Integer", "Fizz Buzz"] },
  { tag: "Math · II", d: "Carries and base conversion — test the overflow case.", easy: ["Plus One", "Add Binary", "Excel Sheet Column Number"] },
  { tag: "Matrices", d: "Row/column indexing without a scratch matrix.", easy: ["Transpose Matrix", "Matrix Diagonal Sum", "Richest Customer Wealth"] },
  { tag: "Matrices · II", d: "In-place transforms — reason about the order of writes.", easy: ["Flipping an Image", "Reshape the Matrix", "Lucky Numbers in a Matrix"] },
  { tag: "Recursion", d: "Base case, then the recurrence. Write both before coding.", easy: ["Fibonacci Number", "Climbing Stairs", "Pascal's Triangle"] },
  { tag: "Dynamic Programming", d: "Brute force → memoise → tabulate. All three steps, every problem.", easy: ["Min Cost Climbing Stairs", "Best Time to Buy and Sell Stock", "Pascal's Triangle II"] },
  { tag: "Dynamic Programming · II", d: "State the transition out loud before writing the loop.", easy: ["N-th Tribonacci Number", "Divisor Game", "Get Maximum in Generated Array"] },
  { tag: "Greedy", d: "Always be ready to say WHY the greedy choice is safe.", easy: ["Assign Cookies", "Lemonade Change", "Maximum Units on a Truck"] },
];

// ---- derived plan ---------------------------------------------------------
function buildPlan(): PrepDay[] {
  const studyDays = SYLLABUS.flatMap((unit) =>
    unit.b.map((chapter, i) => ({
      b: [chapter],
      r: unit.r.slice(
        Math.floor((i * unit.r.length) / unit.b.length),
        Math.floor(((i + 1) * unit.r.length) / unit.b.length)
      ),
    }))
  );

  return studyDays.map((day, i) => {
    const coding = CODING[i % CODING.length];
    return {
      tag: coding.tag,
      a: coding.easy.map((problem) => ({ t: problem, d: coding.d, u: CIP })),
      b: day.b,
      r: day.r,
    };
  });
}

export const PLAN: PrepDay[] = buildPlan();
export const PLAN_DAYS = PLAN.length;

// Saved progress is keyed by "<day>-<block>-<index>", so any change to how
// chapters and problems map onto days would leave old ticks pointing at the
// wrong task. Bumping this resets saved progress back to Day 1 instead.
export const PLAN_VERSION = 4;

// ---- recall-coach prompt builders (kept identical to the original) ----
export function recallPrompt(topic: string, day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my ${PLAN_DAYS}-day plan, night session — eyes-closed retrieval practice.\n\nTopic: "${topic}"\n\nAsk me one question at a time on this topic and wait for my answer. After each answer: briefly correct anything wrong, then ask one deeper follow-up. Keep your replies to 2–3 sentences — this is spoken-style practice, not an essay. Start now with your first question.`;
}

export function recallAll(items: string[], day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my ${PLAN_DAYS}-day plan, night session — eyes-closed retrieval practice before sleep.\n\nRun me through these topics IN ORDER, one at a time:\n${items.map((x, i) => `${i + 1}. ${x}`).join("\n")}\n\nFor each topic: ask me to explain it from memory, wait for my answer, correct briefly, one follow-up, then move to the next topic. Keep every reply to 2–3 sentences. If I blank on something, tell me it goes on tomorrow's revision list and move on. Start with topic 1.`;
}
