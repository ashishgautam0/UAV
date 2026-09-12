// Interview-prep plan data. The syllabus below is authored as themed study
// days (SOURCE_PLAN); the plan the app renders (PLAN) is derived from it so
// that every day holds exactly one chapter.

const ML = "https://www.educative.io/courses/grokking-the-machine-learning-interview";
const GA = "https://www.educative.io/courses/generative-ai-system-design";
const AI = "https://www.educative.io/courses/ai-engineer-interview-prep";
const M3 = "https://www.educative.io/module/P1vxGOtNzNBPX5PJY/10370001/4640179653312512";
const M5 = "https://www.educative.io/module/P1vxGOtNzNBPX5PJY/10370001/4941132913836032";

export type PrepTask = { t: string; d: string; u: string };
export type PrepDay = { tag: string; b: PrepTask[]; r: string[] };

export type BlockKey = "b" | "r";

export const SESSION_NAMES: Record<BlockKey, string> = {
  b: "Block B · 09:30–12:30 — ML / GenAI depth",
  r: "Recall · 22:00–00:00 — eyes closed, no screen",
};

const SOURCE_PLAN: PrepDay[] = [
  { tag: "Two Pointers", b: [
    { t: "ML Interview Ch.1 — How this course helps", d: "Read the framing lesson first.", u: ML + "/how-does-this-course-help-in-ml-interviews" },
    { t: "Setting Up a Machine Learning System", d: "Memorise the 6-step skeleton: problem → metrics → architecture → data → modelling → evaluation. Write it from memory before closing.", u: ML + "/setting-up-a-machine-learning-system" }],
    r: ["The 6 steps of setting up an ML system, in order.", "What signals a two-pointer problem? (sorted input, pair/triplet, in-place partition, palindrome)", "Walk through Sort Colors out loud — three pointers, and why."] },

  { tag: "Fast & Slow · Linked Lists", b: [
    { t: "Performance and Capacity Considerations", d: "SLA vs capacity tradeoffs; the layered funnel idea (cheap model filters, expensive model ranks).", u: ML + "/performance-and-capacity-considerations" },
    { t: "Training Data Collection Strategies", d: "User feedback, human raters, open data, weak supervision — and how you actually labelled Bhojpuri speech.", u: ML + "/training-data-collection-strategies" }],
    r: ["Floyd's cycle detection — why does the fast pointer meet the slow one?", "Three training-data collection strategies and when each fails.", "Your Bhojpuri data pipeline, start to finish, out loud."] },

  { tag: "Sliding Window", b: [
    { t: "Online Experimentation", d: "Hypothesis → A/B design → power/sample size → significance → backtesting. Why offline and online metrics disagree.", u: ML + "/online-experimentation-m2NPGEPwkqn" },
    { t: "Embeddings", d: "Text, user, context embeddings; why two-tower architectures exist; embedding reuse across the funnel.", u: ML + "/embeddings" }],
    r: ["When do you shrink a sliding window vs expand it?", "Design an A/B test for a search-ranking change — metric, guardrails, duration.", "Explain embeddings to a non-ML interviewer in 30 seconds."] },

  { tag: "Hash Maps · Tracking", b: [
    { t: "Transfer Learning (fast revision)", d: "You've done the LoRA/QLoRA course — read for interview framing only. Know when transfer learning hurts: domain shift, catastrophic forgetting.", u: ML + "/transfer-learning" },
    { t: "Model Debugging and Testing (the real gap)", d: "Underfitting vs data bug vs leakage vs distribution shift — and the order you'd check.", u: ML + "/model-debugging-and-testing" },
    { t: "Practical ML Techniques — Breakout mock", d: "Run the chapter mock interview.", u: ML + "/practical-ml-techniques-concepts/mock-interview" }],
    r: ["Hash map vs sorting — when is the extra space worth it?", "Full fine-tune vs LoRA vs QLoRA — cost, memory, quality.", "Your model was underperforming. Walk through your debugging order."] },

  { tag: "Stacks", b: [
    { t: "Search Ranking, part 1 (Ch.3, lessons 1–4)", d: "Problem statement · metrics · architecture · document selection. The retrieval-then-ranking shape generalises to recs, ads, feeds — and RAG.", u: ML }],
    r: ["Monotonic stack — what invariant are you maintaining?", "Search ranking: online vs offline metrics, and why both.", "How is a search-ranking stack structurally the same as a RAG pipeline?"] },

  { tag: "Binary Search · Sorting", b: [
    { t: "Search Ranking, part 2 (Ch.3, lessons 5–8)", d: "Feature engineering (actor/query/document/context groups) · training data generation · ranking · filtering.", u: ML },
    { t: "Search Ranking — Breakout mock", d: "Run the mock interview.", u: ML + "/search-ranking/mock-interview" }],
    r: ["Write the binary search template from memory. Off-by-one rules.", "The four feature groups in a ranking system.", "Deliver your 2-minute self-introduction, out loud, cleanly."] },

  { tag: "Consolidation", b: [
    { t: "Handwrite the week", d: "ML setup checklist, search-ranking architecture, four feature groups — by hand, from memory.", u: ML },
    { t: "Search Ranking design, out loud, 20 minutes", d: "Standing, no notes.", u: ML },
    { t: "Sunday admin (30 min)", d: "Tune Educative roadmap from weak-list; confirm the week's application targets; interview slots before 14:00.", u: ML }],
    r: ["Free recall the whole week — every pattern, every ML concept.", "Anything you blank on is Monday's first revision item. Say it, then note it."] },

  { tag: "Tree DFS", b: [
    { t: "Ace AI — Course Overview", d: "Start the 34-lesson interview-theory course (Days 8–11).", u: AI + "/course-overview" },
    { t: "Ch.2 — Neural Network Training & Optimization (7 lessons)", d: "Training · Gradient Descent · Transfer Learning · Model Alignment · Model Compression · Fine-Tuning · Synthetic Data. Alignment + synthetic data are your genuinely new material.", u: AI + "/neural-networks-training" }],
    r: ["Backprop in 90 seconds, out loud.", "Three tree traversals — when would you pick each?", "Why did ReLU beat sigmoid? Why did GELU beat ReLU in transformers?"] },

  { tag: "Tree BFS", b: [
    { t: "Ace AI Ch.3 — Embeddings and Tokenization (3 lessons)", d: "Includes beam search and decoding: greedy, beam, top-k, top-p, temperature — frequently asked, rarely prepared.", u: AI },
    { t: "Ace AI Ch.4 — Attention Mechanisms (6 lessons)", d: "Self-attention, cross-attention, flash attention, normalisation. Know why transformers use layer norm, not batch norm.", u: AI }],
    r: ["BFS vs DFS on a tree — which problems demand which?", "Adam vs SGD, in one clean paragraph.", "Why layer norm in transformers? Why did RNNs lose?"] },

  { tag: "Heaps · Top K", b: [
    { t: "Ace AI Ch.5 — Evaluation Techniques (2 lessons)", d: "Perplexity, BLEU, ROUGE — and when automated metrics are useless.", u: AI },
    { t: "Ace AI Ch.6 — Model Architectures & Comparisons (7 lessons)", d: "Model selection, scaling laws, interpretability, hallucinations, jailbreaks. Scaling laws + interpretability separate you from builders-only candidates.", u: AI }],
    r: ["Heap vs sorting vs quickselect for Top-K — complexity of each.", "BLEU vs ROUGE vs human eval — when does each break?", "How would you evaluate your Bhojpuri ASR beyond WER?"] },

  { tag: "Graphs", b: [
    { t: "Ace AI Ch.7 — Learning Techniques (4 lessons)", d: "RAG (fast — you've done four RAG courses), few-shot, chain-of-thought.", u: AI },
    { t: "Ace AI Ch.8 — Scalability & Efficiency (3 lessons)", d: "Mixture of Experts, vector DBs, agentic failure modes. Slow down on MoE and agent errors — genuinely new.", u: AI },
    { t: "Ch.9 Wrap Up + Fundamentals of Generative AI mock", d: "Course complete: 34 lessons in four sessions.", u: AI + "/fundamentals-of-generative-ai/mock-interview" }],
    r: ["Mixture of Experts in one minute — routing, why it scales.", "An agentic failure mode you've actually hit, and the fix.", "What is a KV cache actually caching, and why does it matter for cost?"] },

  { tag: "Topological Sort · Union Find", b: [
    { t: "GenAI SD Ch.1 — Introduction", d: "Start the system-design course.", u: GA + "/introduction-to-generative-ai-system-design" },
    { t: "Ch.2 — Fundamental Concepts (5 lessons)", d: "Skim overlaps; the new material is parallelism (data/tensor/pipeline/model) and inference optimisation (quantisation, distillation, KV cache, batching, speculative decoding).", u: GA + "/parallelism-in-genai-models" },
    { t: "RAG and Finetuning — Breakout mock", d: "Your single most likely interview question. You should be unusually strong here.", u: GA + "/rag-and-finetuning/mock-interview" }],
    r: ["Four parallelism strategies — one line each.", "RAG or fine-tuning? The decision rule, then three cases where you'd use both.", "Union-Find template from memory."] },

  { tag: "Intervals · Cyclic Sort", b: [
    { t: "GenAI SD Ch.3 + Ch.4 — Back-of-envelope + SCALED", d: "Finish the calculations lessons; memorise the SCALED 6-step framework as your spine.", u: GA },
    { t: "Ch.11 — RAG System Design (2 lessons)", d: "You know RAG building; add the design layer — sizing, latency budgets, throughput, cost per 1,000 queries, failure modes.", u: GA },
    { t: "Prepare: when does a knowledge graph beat a vector store?", d: "2-minute answer from your Neo4j GraphRAG course. Almost no candidate can answer this.", u: GA }],
    r: ["Recite SCALED in order, then design a RAG pipeline with it, out loud.", "When does a knowledge graph beat a vector store? Two minutes.", "Estimate the cost of serving 10,000 daily users on a 7B model — rough numbers, out loud."] },

  { tag: "Timed simulation", b: [
    { t: "Project narrative build (90 min)", d: "Write then rehearse: Bhojpuri STT (data, model choice, 13.70% WER, what broke) · RAG/agent work as design decisions · hindi-form-agent · deal-hunter-india.", u: ML },
    { t: "Paper narrative (30 min)", d: "TADT: 60-second and 5-minute versions. Always 'under peer review at Wireless Personal Communications' — never 'published'.", u: ML },
    { t: "Weekly application review", d: "Pipeline check; interview slots before 14:00.", u: ML }],
    r: ["Deliver the Bhojpuri project narrative, out loud, twice.", "Deliver the paper narrative — 60-second version, then the 5-minute version.", "Free recall the full week."] },

  { tag: "Subsets", b: [
    { t: "GenAI SD Ch.5 — Text-to-Text System (2 lessons)", d: "Training architecture, then deployment. Own the pipeline: pre-training → SFT → RLHF/DPO → serving → safety → feedback loop.", u: GA },
    { t: "ChatGPT — mock interview", d: "The flagship GenAI design question.", u: GA + "/chatgpt-genai/mock-interview" }],
    r: ["Design ChatGPT, out loud, using SCALED. Ten minutes, no notes.", "The subsets recursion template from memory.", "SFT vs RLHF vs DPO — one line each."] },

  { tag: "Backtracking", b: [
    { t: "GenAI SD Ch.10 — Automatic Speech Recognition SD", d: "Maps directly onto your internship. Reframe the Bhojpuri pipeline in this design vocabulary — internship work becomes a senior-sounding answer.", u: GA },
    { t: "Ch.7 — Text-to-Speech + ElevenLabs mock", d: "2 lessons, then the mock.", u: GA + "/elevenlabs/mock-interview" }],
    r: ["Design an ASR system for a low-resource language, out loud.", "How does your actual Bhojpuri pipeline differ from the reference design — and why?", "Backtracking skeleton from memory."] },

  { tag: "Dynamic Programming I", b: [
    { t: "ML Ch.5 — Recommendation System (7 lessons)", d: "Candidate generation → ranking → re-ranking. Collaborative vs content, matrix factorisation, two-tower, cold start, feedback loops. The most-asked ML design question in India.", u: ML },
    { t: "Movie/Show Recommendation — Breakout mock", d: "Run it.", u: ML + "/movie-show-recommendation-system/mock-interview" }],
    r: ["State the DP transition for Coin Change, out loud.", "Design a recommendation system in 10 minutes, no notes.", "How would you handle cold start for a brand-new user?"] },

  { tag: "Dynamic Programming II", b: [
    { t: "ML Ch.8 — Ad Prediction System (7 lessons)", d: "Calibration, CTR, auction dynamics, online learning, extreme class imbalance. Three imbalance techniques with tradeoffs — a near-guaranteed follow-up.", u: ML },
    { t: "Ad Prediction Problem — Breakout mock", d: "Run it.", u: ML + "/ad-prediction-problem/mock-interview" }],
    r: ["Edit distance — the recurrence, out loud.", "Three ways to handle severe class imbalance, and when each is wrong.", "What is model calibration and why does it matter for ads?"] },

  { tag: "Greedy · Matrices", b: [
    { t: "ML Ch.9 — Fraud Detection (5 lessons)", d: "Imbalance-heavy, real-time constrained. Note what's shared: feature stores, streaming inference, thresholds, human-in-the-loop.", u: ML },
    { t: "Ch.10 — Hate Speech Detection + mock", d: "5 lessons, then the Harmful Content Detection mock.", u: ML + "/harmful-content-detection-system/mock-interview" }],
    r: ["When is a greedy choice provably safe? One example, one counter-example.", "Design a real-time fraud detection system, out loud.", "Precision/recall tradeoff for content moderation — which way do you err, and why?"] },

  { tag: "Tries · Bitwise · Agentic patterns", b: [
    { t: "GenAI SD Ch.6 — Text-to-Image + DALL·E mock", d: "2 lessons + mock. Then Ch.12 Conclusion. Skip text-to-video and captioning unless a JD names them. Course complete.", u: GA + "/dall-e/mock-interview" },
    { t: "Agentic AI Expert — Module 3: Agentic Design Patterns", d: "Routing · parallelisation · orchestrator-worker · evaluator-optimiser. You build agents; this gives you the naming. For each pattern, one line on where you've used it.", u: M3 }],
    r: ["Name the four agentic design patterns and give one use case each.", "Which pattern did your own agent work actually use? Say it in pattern language.", "Diffusion vs autoregressive generation — the tradeoff."] },

  { tag: "Timed simulation II · Agentic SD", b: [
    { t: "Agentic AI Expert — Module 5: Agentic System Design (~90 min)", d: "Guardrails, failure containment, NVIDIA Eureka. Have a real answer for looping agents, hallucinated tool calls, runaway cost.", u: M5 },
    { t: "45-min ML design mock, out loud, standing", d: "Pick one un-rehearsed: Feed Based System, Entity Linking, or Dynamic Pricing. Mark every gap against the chapter.", u: ML },
    { t: "Sunday admin", d: "Application review; slots before 14:00.", u: ML }],
    r: ["Free recall the entire three weeks — patterns, ML systems, GenAI systems.", "Whatever you blank on becomes Week 4's syllabus. Say it, note it."] },

  { tag: "Weak-list patch I · Behavioural", b: [
    { t: "STAR bank — 6 stories", d: "Conflict, failure, ownership, ambiguity, learning speed, disagreement.", u: ML },
    { t: "Resume walkthrough, timed to 3 minutes", d: "M.Tech (AI) → internship work → certifications → paper → what you want next. Consistency check: reason-for-leaving and 3-year answers must match everywhere.", u: ML }],
    r: ["The 3-minute resume walkthrough, out loud, twice.", "Two STAR stories, out loud.", "'Why are you leaving?' and 'Where in three years?' — smooth, no hesitation."] },

  { tag: "Mock — technical screen", b: [
    { t: "Machine Learning Fundamentals — mock interview", d: "Run it.", u: ML + "/machine-learning-fundamentals/mock-interview" },
    { t: "Rapid-fire self-quiz, 60 seconds per answer, spoken", d: "Bias-variance · regularisation · precision/recall · ROC vs PR AUC · overfitting fixes · CV · bagging vs boosting · GD variants · attention · tokenisation · quantisation · LoRA. Over 60s → re-drill tomorrow.", u: AI }],
    r: ["Re-answer every rapid-fire question you fumbled.", "Replay the mock in your head — where did you go quiet? Quiet loses offers."] },

  { tag: "Mock — ML depth", b: [
    { t: "Two 45-min design mocks, back to back", d: "Visual Search · ETA · People You May Know · Fraud Detection — pick two untouched. Record one on your phone.", u: ML + "/visual-search-system-design/mock-interview" },
    { t: "Playback the recording", d: "Listen for filler, unstructured openings, and skipped requirement-gathering — the most skipped, most weighted step.", u: ML }],
    r: ["Replay your recorded mock mentally — three things to fix.", "Re-deliver the opening 2 minutes of a system design answer, cleanly."] },

  { tag: "Mock — GenAI design", b: [
    { t: "Run the skipped GenAI mocks", d: "ChatGPT · RAG and Finetuning · ElevenLabs.", u: GA + "/chatgpt-genai/mock-interview" },
    { t: "Self-designed: multilingual voice assistant for low-resource Indian languages", d: "Use SCALED. Sits precisely at ASR × RAG × fine-tuning — the single best question you could be asked. Prepare it as a story to steer interviews toward.", u: GA }],
    r: ["Deliver the multilingual voice assistant design, out loud, end to end.", "Where in that design does your actual internship experience slot in?"] },

  { tag: "Paper defence", b: [
    { t: "TADT full defence rehearsal", d: "Why BQPSO over PSO/GA · why a digital twin layer · baselines · significance · limitations · real IoV latency. Name your own limitations — it earns respect. Status: under peer review at Wireless Personal Communications, never 'published'.", u: ML },
    { t: "'Walk me through your M.Tech thesis' — 5-minute answer", d: "Rehearse it twice.", u: ML }],
    r: ["The full paper defence, out loud, including the limitations.", "The 60-second version. Then the 5-minute version."] },

  { tag: "Full loop simulation", b: [
    { t: "Round 3: 45-min ML or GenAI system design, out loud", d: "Full structure: requirements → metrics → design → tradeoffs.", u: GA },
    { t: "Round 4: 30-min behavioural + written self-assessment", d: "STAR stories, resume walkthrough, then: what would have cost you the offer? Fix the top two tomorrow. Prepare 5 questions for the interviewer.", u: ML }],
    r: ["Free recall the whole loop. Where did you lose energy or structure?", "Rehearse your 5 questions for the interviewer."] },

  { tag: "Taper & readiness", b: [
    { t: "Final narrative pass", d: "Resume walkthrough · Bhojpuri project · paper · 'why this company' template.", u: ML },
    { t: "Logistics check", d: "Camera, mic, lighting, connection, quiet window before 14:00, IDE set to Python, notes closed. Write one page: what you know now that you didn't 28 days ago.", u: ML }],
    r: ["Nothing structured tonight. Rest properly.", "If you want one thing: the 2-minute self-introduction, once. Then sleep."] },
];

// One chapter per day: a themed day carrying k chapters becomes k days of one
// chapter each, with that theme's recall topics split evenly across them.
function oneChapterPerDay(source: PrepDay[]): PrepDay[] {
  return source.flatMap((day) =>
    day.b.map((chapter, i) => ({
      tag: day.b.length > 1 ? `${day.tag} · ${i + 1}/${day.b.length}` : day.tag,
      b: [chapter],
      r: day.r.slice(
        Math.floor((i * day.r.length) / day.b.length),
        Math.floor(((i + 1) * day.r.length) / day.b.length)
      ),
    }))
  );
}

export const PLAN: PrepDay[] = oneChapterPerDay(SOURCE_PLAN);
export const PLAN_DAYS = PLAN.length;

// Saved progress is keyed by "<day>-<block>-<index>", so any change to how
// chapters map onto days would leave old ticks pointing at the wrong chapter.
// Bumping this resets saved progress back to Day 1 instead.
export const PLAN_VERSION = 2;

// ---- recall-coach prompt builders (kept identical to the original) ----
export function recallPrompt(topic: string, day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my ${PLAN_DAYS}-day plan, night session — eyes-closed retrieval practice.\n\nTopic: "${topic}"\n\nAsk me one question at a time on this topic and wait for my answer. After each answer: briefly correct anything wrong, then ask one deeper follow-up. Keep your replies to 2–3 sentences — this is spoken-style practice, not an essay. Start now with your first question.`;
}

export function recallAll(items: string[], day: number): string {
  return `Act as my recall coach for AI/ML interview prep. It's Day ${day} of my ${PLAN_DAYS}-day plan, night session — eyes-closed retrieval practice before sleep.\n\nRun me through these topics IN ORDER, one at a time:\n${items.map((x, i) => `${i + 1}. ${x}`).join("\n")}\n\nFor each topic: ask me to explain it from memory, wait for my answer, correct briefly, one follow-up, then move to the next topic. Keep every reply to 2–3 sentences. If I blank on something, tell me it goes on tomorrow's revision list and move on. Start with topic 1.`;
}
