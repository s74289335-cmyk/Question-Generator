import random
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# -----------------------------------------------------------
# DATA MODELS
# -----------------------------------------------------------

@dataclass
class Question:
    id: str
    domain: str
    difficulty: str
    question: str
    options: List[str]
    answer_index: int
    hidden_derivation: str
    meta: Dict[str, Any]

@dataclass
class SolverResult:
    solver_name: str
    success: bool
    answer_value: Optional[float]
    chosen_index: Optional[int]
    reasoning: str

@dataclass
class ValidationResult:
    is_valid: bool
    reason: str


# -----------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------

def format_number(num: float) -> str:
    if abs(num - round(num)) < 1e-6:
        return str(int(round(num)))
    return f"{num:.4f}"

def choose_closest_option(options, numeric_answer):
    diffs = []
    for opt in options:
        val = float(opt)
        diffs.append(abs(val - numeric_answer))
    return diffs.index(min(diffs))

def build_options(answer: float):
    base = float(answer)
    opts = {format_number(base)}
    while len(opts) < 4:
        delta = random.uniform(-3, 3)
        v = base + delta
        if v > 0:
            opts.add(format_number(v))
    opts = list(opts)
    random.shuffle(opts)
    return opts


# -----------------------------------------------------------
# QUESTION GENERATORS
# -----------------------------------------------------------

def generate_tsd_question() -> Question:
    v1 = random.choice([30, 40, 50, 60])
    v2 = random.choice([30, 40, 50, 60])
    t = random.choice([2, 3, 4])
    d = (v1 + v2) * t

    answer = t
    options = build_options(answer)
    ans = format_number(answer)
    if ans not in options:
        options[0] = ans
        random.shuffle(options)
    idx = options.index(ans)

    q = (
        f"Two trains are {d} km apart and move towards each other. "
        f"Train A travels at {v1} km/h, Train B at {v2} km/h. "
        "How long until they meet?"
    )

    sol = (
        f"Relative speed = {v1}+{v2} = {v1+v2}. "
        f"Time = {d}/{v1+v2} = {ans} hours."
    )

    return Question(
        id=str(uuid.uuid4()),
        domain="Time, Speed & Distance",
        difficulty="Easy",
        question=q,
        options=options,
        answer_index=idx,
        hidden_derivation=sol,
        meta={"type": "tsd", "v1": v1, "v2": v2, "d": d},
    )


def generate_work_question() -> Question:
    a = random.choice([6, 8, 10, 12])
    b = random.choice([8, 10, 12, 15])
    t = 1 / (1/a + 1/b)

    answer = t
    options = build_options(answer)
    ans = format_number(answer)
    if ans not in options:
        options[0] = ans
        random.shuffle(options)
    idx = options.index(ans)

    q = (
        f"Worker A completes a job in {a} hours and worker B in {b} hours. "
        "How long to finish it together?"
    )

    sol = (
        f"A = 1/{a}, B = 1/{b}. Combined = {(1/a+1/b):.4f}. "
        f"Time = 1/(combined) = {ans} hours."
    )

    return Question(
        id=str(uuid.uuid4()),
        domain="Work & Time",
        difficulty="Medium",
        question=q,
        options=options,
        answer_index=idx,
        hidden_derivation=sol,
        meta={"type": "work", "a": a, "b": b},
    )


def generate_pipes_question() -> Question:
    fa = random.choice([8, 10, 12, 15])
    eb = random.choice([18, 20, 24, 30])

    net = 1/fa - 1/eb
    if net <= 0:
        eb += 10
        net = 1/fa - 1/eb

    t = 1/net
    ans = t
    options = build_options(ans)
    ans_str = format_number(ans)

    if ans_str not in options:
        options[0] = ans_str
        random.shuffle(options)
    idx = options.index(ans_str)

    q = (
        f"Pipe A fills a tank in {fa} hours, Pipe B empties it in {eb} hours. "
        "If both are opened together, how long to fill the tank?"
    )

    sol = (
        f"A = 1/{fa}, B = -1/{eb}. Net = {net:.6f}. "
        f"Time = 1/net = {ans_str} hours."
    )

    return Question(
        id=str(uuid.uuid4()),
        domain="Pipes & Cisterns",
        difficulty="Medium",
        question=q,
        options=options,
        answer_index=idx,
        hidden_derivation=sol,
        meta={"type": "pipes", "fa": fa, "eb": eb},
    )


def generate_question_for_domain(d: str) -> Question:
    if d == "tsd":
        return generate_tsd_question()
    if d == "work":
        return generate_work_question()
    if d == "pipes":
        return generate_pipes_question()
    raise ValueError("Unknown domain")


# -----------------------------------------------------------
# SOLVERS: A, B, C
# -----------------------------------------------------------

def solve_a(q: Question) -> SolverResult:
    try:
        if q.meta["type"] == "tsd":
            t = q.meta["d"] / (q.meta["v1"] + q.meta["v2"])
        elif q.meta["type"] == "work":
            a, b = q.meta["a"], q.meta["b"]
            t = 1 / (1/a + 1/b)
        else:
            fa, eb = q.meta["fa"], q.meta["eb"]
            t = 1 / (1/fa - 1/eb)

        idx = choose_closest_option(q.options, t)
        return SolverResult("A", True, float(q.options[idx]), idx, "Algebraic")
    except Exception as e:
        return SolverResult("A", False, None, None, f"Error: {e}")


def solve_b(q: Question) -> SolverResult:
    try:
        idx = q.answer_index
        return SolverResult("B", True, float(q.options[idx]), idx, "Generator-consistency")
    except Exception as e:
        return SolverResult("B", False, None, None, f"Error: {e}")


def solve_c(q: Question) -> SolverResult:
    try:
        for i, opt in enumerate(q.options):
            t = float(opt)
            if q.meta["type"] == "tsd":
                if abs((q.meta["v1"] + q.meta["v2"]) * t - q.meta["d"]) < 1e-9:
                    return SolverResult("C", True, t, i, "Exact equation match")

            elif q.meta["type"] == "work":
                a, b = q.meta["a"], q.meta["b"]
                if abs(t/a + t/b - 1) < 1e-9:
                    return SolverResult("C", True, t, i, "Exact equation match")

            else:
                fa, eb = q.meta["fa"], q.meta["eb"]
                if abs(t/fa - t/eb - 1) < 1e-9:
                    return SolverResult("C", True, t, i, "Exact equation match")

        return SolverResult("C", False, None, None, "No exact match")

    except Exception as e:
        return SolverResult("C", False, None, None, f"Error: {e}")


# -----------------------------------------------------------
# ULTRA-STRICT VALIDATION
# -----------------------------------------------------------

def validate(q: Question, s1: SolverResult, s2: SolverResult, s3: SolverResult) -> ValidationResult:

    if not (s1.success and s2.success and s3.success):
        return ValidationResult(False, "One or more solvers failed")

    if None in (s1.chosen_index, s2.chosen_index, s3.chosen_index):
        return ValidationResult(False, "Missing solver outputs")

    if not (s1.chosen_index == s2.chosen_index == s3.chosen_index):
        return ValidationResult(False, "Option mismatch across solvers")

    if not (
        abs(s1.answer_value - s2.answer_value) < 1e-9 and
        abs(s2.answer_value - s3.answer_value) < 1e-9
    ):
        return ValidationResult(False, "Numeric mismatch across solvers")

    if s1.chosen_index != q.answer_index:
        return ValidationResult(False, "Solvers disagree with true answer")

    if s1.answer_value <= 0:
        return ValidationResult(False, "Non-physical answer")

    if format_number(s1.answer_value) not in q.hidden_derivation:
        return ValidationResult(False, "Derivation mismatch")

    return ValidationResult(True, "Perfect question")


# -----------------------------------------------------------
# QUESTION GENERATION LOOP (Core)
# -----------------------------------------------------------

def generate_valid(n: int = 1, max_tries: int = 200):
    """Generate n validated questions, one at a time."""
    accepted: List[Question] = []
    logs: List[Dict[str, Any]] = []
    domains = ["tsd", "work", "pipes"]
    attempt = 0

    while len(accepted) < n and attempt < max_tries:
        attempt += 1
        domain = domains[(attempt - 1) % 3]
        q = generate_question_for_domain(domain)

        s1 = solve_a(q)
        s2 = solve_b(q)
        s3 = solve_c(q)

        valid = validate(q, s1, s2, s3)

        logs.append({
            "attempt": attempt,
            "id": q.id,
            "domain": domain,
            "valid": valid.is_valid,
            "reason": valid.reason,
        })

        if valid.is_valid:
            # Attach solver details into meta
            q.meta["solver_a"] = {
                "value": s1.answer_value,
                "index": s1.chosen_index,
                "reason": s1.reasoning,
            }
            q.meta["solver_b"] = {
                "value": s2.answer_value,
                "index": s2.chosen_index,
                "reason": s2.reasoning,
            }
            q.meta["solver_c"] = {
                "value": s3.answer_value,
                "index": s3.chosen_index,
                "reason": s3.reasoning,
            }

            accepted.append(q)

    return accepted, logs


# -----------------------------------------------------------
# HTML QUIZ BUILDER
# -----------------------------------------------------------

def build_single_question_html(questions: List[Question], path: Path):
    js = []
    for q in questions:
        js.append({
            "question": q.question,
            "options": q.options,
            "answer": q.answer_index,
            "solution": q.hidden_derivation,
            "solver_a": q.meta.get("solver_a", {}),
            "solver_b": q.meta.get("solver_b", {}),
            "solver_c": q.meta.get("solver_c", {}),
        })

    js_json = json.dumps(js, indent=2)

    # BLACK–PURPLE NEON UI TEMPLATE (simple & centered)
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>HydraQuant Quiz</title>

<style>
/* ------ GLOBAL THEME ------ */
body {{
    margin: 0;
    padding: 0;
    background: #0d0b1f;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: "Poppins", sans-serif;
    color: #d4caff;
}}

/* ------ CENTER CONTAINER ------ */
#container {{
    width: 85%;
    max-width: 650px;
    background: rgba(34, 0, 59, 0.45);
    backdrop-filter: blur(14px);
    padding: 35px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0 0 20px rgba(174, 0, 255, 0.45);
}}

/* ------ HEADING ------ */
h1 {{
    margin-top: 0;
    font-size: 28px;
    color: #e8d7ff;
    text-shadow: 0 0 8px #a449ff;
}}

/* ------ QUESTION BOX ------ */
#qbox {{
    background: rgba(66, 0, 109, 0.3);
    padding: 25px;
    border-radius: 15px;
    margin-top: 15px;
    color: #f0e4ff;
    box-shadow: inset 0 0 12px rgba(185, 0, 255, 0.4);
}}

/* ------ OPTIONS ------ */
.option {{
    display: block;
    margin: 12px 0;
    font-size: 17px;
    font-weight: 500;
}}

.option input {{
    transform: scale(1.3);
    margin-right: 12px;
}}

/* ------ BUTTONS ------ */
button {{
    padding: 12px 24px;
    border: none;
    border-radius: 10px;
    margin: 12px 6px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    color: white;
    transition: 0.3s;
}}

#next {{
    background: linear-gradient(135deg, #6a0dad, #b300ff);
    box-shadow: 0 0 12px #b300ff;
}}
#next:hover {{ transform: scale(1.08); }}

#cont {{
    background: linear-gradient(135deg, #1e8b4d, #28ff8a);
    box-shadow: 0 0 12px #28ff8a;
    display: none;
}}
#cont:hover {{ transform: scale(1.08); }}

/* ------ FEEDBACK ------ */
#feedback {{
    font-weight: bold;
    font-size: 18px;
    margin-top: 12px;
}}

/* ------ SOLUTION BOX ------ */
#solution {{
    display: none;
    background: rgba(128, 0, 255, 0.2);
    color: #f1d1ff;
    padding: 15px;
    border-left: 5px solid #c267ff;
    border-radius: 10px;
    margin-top: 15px;
    text-align: left;
}}

/* ------ SCORE ------ */
#score {{
    font-size: 20px;
    margin-top: 20px;
    color: #d7b4ff;
    text-shadow: 0 0 6px #8b45ff;
}}
</style>
</head>

<body>

<div id="container">

<h1>HydraQuant Smart Quiz</h1>

<div id="qbox"></div>

<button id="next" onclick="checkAnswer()">Next</button>
<button id="cont" onclick="nextQuestion()">Continue</button>

<p id="score"></p>

</div>

<script>
const questions = {js_json};
let index = 0, score = 0;

function loadQ() {{
    const q = questions[index];
    let h = `<h3>Question ${{index+1}} / ${{questions.length}}</h3><p>${{q.question}}</p>`;
    q.options.forEach((op, i) => {{
        h += `<label class='option'><input type='radio' name='opt' value='${{i}}'> ${{op}}</label>`;
    }});
    h += "<p id='feedback'></p><div id='solution'></div>";

    document.getElementById("qbox").innerHTML = h;
    document.getElementById("cont").style.display = "none";
    document.getElementById("next").style.display = "inline-block";
}}

function checkAnswer() {{
    const sel = document.querySelector("input[name='opt']:checked");
    if (!sel) return alert("Please select an answer!");

    const ans = parseInt(sel.value);
    const cor = questions[index].answer;
    const fb = document.getElementById("feedback");
    const sol = document.getElementById("solution");

    if (ans === cor) {{
        fb.style.color = "#28ff8a";
        fb.textContent = "Correct!";
        sol.style.display = "none";
        score++;
    }} else {{
        fb.style.color = "#ff6eb7";
        fb.textContent = "Wrong!";
        sol.style.display = "block";

        sol.innerHTML = `
            <h4>Optimal Solution</h4>
            <p>${{questions[index].solution}}</p>
            <button onclick="toggleBreakdown()"
                style="margin-top:10px; padding:8px 14px; background:#6a0dad; border:none; color:white; border-radius:6px;">
                Show Solver Breakdown ▼
            </button>
            <div id="breakdown" style="display:none; margin-top:10px; text-align:left; color:#e0caff;">
                <p><b>Solver A:</b> ${{questions[index].solver_a.reason}} → ${{questions[index].solver_a.value}}</p>
                <p><b>Solver B:</b> ${{questions[index].solver_b.reason}} → ${{questions[index].solver_b.value}}</p>
                <p><b>Solver C:</b> ${{questions[index].solver_c.reason}} → ${{questions[index].solver_c.value}}</p>
            </div>
        `;
    }}

    document.getElementById("next").style.display = "none";
    document.getElementById("cont").style.display = "inline-block";
}}

function toggleBreakdown() {{
    const box = document.getElementById("breakdown");
    if (!box) return;
    box.style.display = (box.style.display === "none") ? "block" : "none";
}}

function nextQuestion() {{
    index++;
    if (index >= questions.length) return finish();
    loadQ();
}}

function finish() {{
    document.getElementById("qbox").style.display = "none";
    document.getElementById("next").style.display = "none";
    document.getElementById("cont").style.display = "none";

    document.getElementById("score").innerHTML =
        `Quiz Completed!<br>Score: ${{score}} / ${{questions.length}}`;
}}

loadQ();
</script>

</body>
</html>
"""

    path.write_text(html, encoding="utf-8")


# -----------------------------------------------------------
# HYBRID MAIN CONTROLLER
# -----------------------------------------------------------

def hybrid_main():
    print("\nHYDRAQUANT QUESTION GENERATOR")
    print("--------------------------------")
    print("1. Infinite Question Generation (Loop Mode)")
    print("2. Generate Fixed Number of Questions (Batch Mode)\n")

    mode = input("Enter choice (1 or 2): ").strip()

    if mode == "1":
        print("\n--- Infinite Mode Activated ---")
        count = 1
        while True:
            print(f"\nGenerating Question #{count} ...")
            accepted, _ = generate_valid(1, 200)

            if not accepted:
                print("❌ Failed. Retrying...")
                continue

            q = accepted[0]
            print(f"\n✔ Question #{count}: {q.question}")
            print("Correct Answer:", q.options[q.answer_index])
            print("Derivation:", q.hidden_derivation)
            print("Solver A:", q.meta["solver_a"])
            print("Solver B:", q.meta["solver_b"])
            print("Solver C:", q.meta["solver_c"])

            Path(f"question_{count}.json").write_text(json.dumps(asdict(q), indent=2))
            count += 1

    elif mode == "2":
        num = int(input("\nHow many questions do you want? "))

        accepted_all: List[Question] = []
        logs_all: List[Dict[str, Any]] = []

        for i in range(1, num + 1):
            print(f"\nGenerating question {i}/{num} ...")
            accepted, logs = generate_valid(1, 200)
            logs_all.extend(logs)

            if accepted:
                accepted_all.append(accepted[0])
                print("✔ Valid question added!")
            else:
                print("❌ Failed. Skipping this one...")

        Path("accepted_questions.json").write_text(
            json.dumps([asdict(q) for q in accepted_all], indent=2)
        )
        Path("generation_logs.json").write_text(
            json.dumps(logs_all, indent=2)
        )

        if accepted_all:
            build_single_question_html(accepted_all, Path("quiz_single.html"))
            print("\n✔ Batch Completed! Open quiz_single.html")
        else:
            print("\nNo valid questions generated.")

    else:
        print("Invalid choice")


# -----------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------

if __name__ == "__main__":
    hybrid_main()
