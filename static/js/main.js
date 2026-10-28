// Geometry Is Not a Prompt: project page interactions
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // ---------------------------------------------------------------- theme
  const root = document.documentElement;
  try { const t = localStorage.getItem("theme"); if (t) root.setAttribute("data-theme", t); } catch (e) {}
  $(".theme-btn").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
  });

  // ---------------------------------------------------------------- video chapters
  const vid = $("#walkthrough");
  const chap = $$(".chapters button");
  chap.forEach(b => b.addEventListener("click", () => { vid.currentTime = +b.dataset.t; vid.play(); }));
  vid.addEventListener("timeupdate", () => {
    let cur = 0;
    chap.forEach((b, i) => { if (vid.currentTime >= +b.dataset.t) cur = i; });
    chap.forEach((b, i) => b.classList.toggle("on", i === cur));
  });

  // ---------------------------------------------------------------- math
  function renderMath() {
    if (!window.katex) return;
    $$(".math[data-m]").forEach(el => katex.render(el.dataset.m, el, { displayMode: true, throwOnError: false }));
    $$(".m").forEach(el => katex.render(el.textContent, el, { throwOnError: false }));
  }
  if (window.katex) renderMath(); else window.addEventListener("load", renderMath);

  // ---------------------------------------------------------------- delegation stepper
  const STEPS = [
    ["Task specification", "The designer, human or AI, starts from instructions ρ and a small calibration set 𝓑 of requests with known answers.",
      "<b>Case B:</b> “Give me the κ clearest views of asset ρ”, plus calibration queries with visibility labels."],
    ["Planner", "An LLM, a human, or both, decompose the objective into sequential sub-tasks h = h_K ∘ ⋯ ∘ h₁, each with a contract σₖ declaring its input and output schema.",
      "<b>Case B:</b> h₁ parse target and κ · h₂ retrieve frames and pose · h₃ decide visibility · h₄ select κ diverse views."],
    ["Sub-task plan: all-LLM baseline", "No tools exist yet: every step is run by the LLM, aₖ = fₖ. This baseline is the reference every tool must beat.",
      "<b>Case B:</b> all-LLM designs return <b>0%</b> in-frame frames on the development query, at any reasoning effort."],
    ["Success evaluator", "Each step is measured for error, latency, cost and flexibility, and combined into a local design loss dₖ. The step with the weakest trade-off is chosen next.",
      "<b>Case B:</b> d(f₃) = 7.734 for visibility, the largest. Next come retrieval (1.980), selection (0.867) and parsing (0.147)."],
    ["Tool maker", "An LLM, a human, or an LLM under review writes a candidate tool τₖ from the contract σₖ, calibration examples and the observed failures, or returns ∅ if none can be built.",
      "<b>Case B:</b> τ₃ projects the camera footprint on the ground plane and tests whether the asset lies inside it, in 0.02 ms per frame."],
    ["Candidate validation", "The candidate must satisfy the interface, pass correctness tests and declare unsupported inputs. It is measured with the same protocol as the LLM.",
      "<b>Case B:</b> τ₃ returns <i>pose unknown</i> when yaw, pitch or height are missing, instead of guessing."],
    ["Acceptance gate", "The gain Δₖ = dₖ(fₖ) − dₖ(τₖ) must exceed a margin δₖ. Choosing δₖ ≥ 2ηₖ guarantees the true loss improves despite estimation error ηₖ.",
      "<b>Case B:</b> Δ₃ = +7.632, Δ₂ = +1.633, Δ₄ = +0.727, but Δ₁ = −0.143."],
    ["Accept tool, or retain LLM", "Above the margin the tool replaces the LLM for this step. Otherwise the current mechanism stays. Flexibility is part of the loss, so brittle tools lose.",
      "<b>Case B:</b> accept τ₂, τ₃, τ₄. Retain f₁: the parser tool is faster, but serves only 30% of paraphrases versus 95%."],
    ["Current design → next sub-task", "The composition is updated and the loop returns to the evaluator for the next weakest step, until all are examined, no candidate helps, or the budget runs out.",
      "<b>Case B:</b> after four visits, the design is f₁ → τ₂ → τ₃ → τ₄."],
    ["Fixed agent design", "The allocation is frozen and executed directly on new requests. The LLM keeps what needs language; geometry is computed.",
      "<b>Held out:</b> precision 0.982 at 0.83 s and 101 tokens per request, 68× fewer tokens than prompting."],
  ];
  const nodes = $$(".flow .n");
  const dots = $("#st-dots");
  STEPS.forEach(() => dots.appendChild(document.createElement("i")));
  let cur = 0, timer = null;
  function show(i) {
    cur = (i + STEPS.length) % STEPS.length;
    const [h, p, ex] = STEPS[cur];
    $("#st-k").textContent = `STEP ${cur + 1} / ${STEPS.length}`;
    $("#st-h").textContent = h;
    $("#st-p").textContent = p;
    $("#st-ex").innerHTML = ex;
    nodes.forEach(n => {
      const k = +n.dataset.i;
      n.classList.toggle("on", k === cur);
      n.classList.toggle("done", k < cur);
    });
    $$("i", dots).forEach((d, k) => d.classList.toggle("on", k === cur));
  }
  function stop() { clearInterval(timer); timer = null; $("#st-play").textContent = "▶ Play"; $("#st-play").classList.remove("on"); }
  $("#st-next").addEventListener("click", () => { stop(); show(cur + 1); });
  $("#st-prev").addEventListener("click", () => { stop(); show(cur - 1); });
  $("#st-play").addEventListener("click", () => {
    if (timer) return stop();
    $("#st-play").textContent = "❚❚ Pause"; $("#st-play").classList.add("on");
    timer = setInterval(() => show(cur + 1), 3800);
  });
  nodes.forEach(n => n.addEventListener("click", () => { stop(); show(+n.dataset.i); }));
  show(0);

  // ---------------------------------------------------------------- allocation calculator (Table 4)
  const SUB = [
    { k: "h₁", name: "Parse request", f: [0.02, 0.35, 0.6, 0.95], t: [0.15, 0.001, 0, 0.30] },
    { k: "h₂", name: "Retrieve frames", f: [1.00, 2.40, 12.0, 0.90], t: [0.00, 0.89, 0, 0.60] },
    { k: "h₃", name: "Visibility", f: [1.00, 20.86, 23.8, 1.00], t: [0.00, 0.006, 0, 0.50] },
    { k: "h₄", name: "Select κ views", f: [0.50, 1.20, 0.35, 1.00], t: [0.02, 0.0002, 0, 0.40] },
  ];
  const T0 = 1, C0 = 10; // seconds, thousand tokens
  const ids = ["wA", "wT", "wC", "wF", "dl"];
  const loss = (m, w) => w.wA * m[0] + w.wT * m[1] / T0 + w.wC * m[2] / C0 + w.wF * (1 - m[3]);
  const strip = $("#calc-strip"), tbody = $("#calc-table tbody");
  function calc() {
    const w = {};
    ids.forEach(i => { w[i] = +$("#" + i).value; $("#v-" + i).textContent = w[i].toFixed(2); });
    const rows = SUB.map(s => {
      const df = loss(s.f, w), dt = loss(s.t, w), d = df - dt;
      return { ...s, df, dt, d, tool: d > w.dl };
    });
    const mx = Math.max(...rows.flatMap(r => [r.df, r.dt]), 1e-9);
    strip.innerHTML = rows.map(r => `
      <div class="rs ${r.tool ? "tool" : "llm"}">
        <div class="h">${r.k}</div><div class="nm">${r.name}</div>
        <span class="chip ${r.tool ? "tool" : "llm"}">${r.tool ? "TOOL τ" : "LLM f"}${r.k.slice(1)}</span>
        <div class="bars"><div class="bar f"><i style="width:${(100 * r.df / mx).toFixed(1)}%"></i></div>
        <div class="bar t"><i style="width:${(100 * r.dt / mx).toFixed(1)}%"></i></div></div>
        <div class="dl">Δ = ${r.d >= 0 ? "+" : ""}${r.d.toFixed(3)}</div>
      </div>`).join("");
    tbody.innerHTML = rows.map(r => `<tr><td>${r.k} ${r.name}</td><td>${r.df.toFixed(3)}</td><td>${r.dt.toFixed(3)}</td>
      <td>${r.d >= 0 ? "+" : ""}${r.d.toFixed(3)}</td><td class="${r.tool ? "toolc" : "llmc"}">${r.tool ? "delegate to tool" : "keep LLM"}</td></tr>`).join("");
    const code = rows.map(r => (r.tool ? "τ" : "f") + r.k.slice(1)).join(" → ");
    const total = rows.reduce((a, r) => a + (r.tool ? r.dt : r.df), 0);
    const allL = rows.reduce((a, r) => a + r.df, 0);
    $("#calc-summary").innerHTML = `Selected design: <b>${code}</b>. Total design loss <b>${total.toFixed(3)}</b>, against <b>${allL.toFixed(3)}</b> for the all-LLM baseline.`;
  }
  ids.forEach(i => $("#" + i).addEventListener("input", calc));
  $$(".presets button").forEach(b => b.addEventListener("click", () => {
    b.dataset.p.split(",").forEach((v, k) => { $("#" + ids[k]).value = v; });
    calc();
  }));
  calc();

  // ---------------------------------------------------------------- frozen benchmark chart (Table 2 + appendix)
  const BENCH = {
    g37: [
      ["LLM, deployed prompt", [0.614, 0.476, 0.750], [0.796, 0.697, 0.893], "6.33 s", "6,893"],
      ["LLM, exact equations given", [0.653, 0.521, 0.781], [0.768, 0.669, 0.864], "8.19 s", "7,640"],
      ["LLM writes and runs code", [0.982, 0.951, 1.0], [0.865, 0.803, 0.925], "5.70 s", "1,747"],
      ["LLM + FOV tool", [0.973, 0.927, 1.0], [0.753, 0.610, 0.887], "3.87 s", "926"],
      ["Deterministic pipeline", [0.982, 0.946, 1.0], [0.757, 0.615, 0.891], "0.01 s", "0"],
      ["Our allocation", [0.982, 0.946, 1.0], [0.757, 0.615, 0.891], "0.83 s", "101"],
    ],
    g25: [
      ["LLM, deployed prompt", [0.423, 0.313, 0.542], [0.573, 0.463, 0.684], "0.79 s", "5,192"],
      ["LLM, exact equations given", [0.493, 0.337, 0.648], [0.530, 0.388, 0.671], "0.82 s", "5,541"],
      ["LLM writes and runs code", [0.952, 0.904, 0.990], [0.476, 0.344, 0.605], "13.61 s", "3,236"],
      ["LLM + FOV tool", [0.986, 0.964, 1.0], [0.724, 0.583, 0.858], "0.54 s", "687"],
      ["Deterministic pipeline", [0.982, 0.946, 1.0], [0.757, 0.615, 0.891], "0.01 s", "0"],
      ["Our allocation", [0.982, 0.946, 1.0], [0.757, 0.615, 0.891], "0.56 s", "101"],
    ],
  };
  const svg = $("#bench-svg"), tip = $("#bench-tip"), chart = $("#bench-chart");
  const NS = "http://www.w3.org/2000/svg";
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); (p || svg).appendChild(e); return e; };
  function drawBench(m) {
    const data = BENCH[m];
    svg.innerHTML = "";
    const L = 230, R = 880, top = 14, rowH = 48;
    const x = v => L + (R - L) * v;
    const g = el("g", { class: "grid" });
    for (let v = 0; v <= 1.0001; v += 0.2) {
      el("line", { x1: x(v), x2: x(v), y1: top, y2: top + rowH * data.length }, g);
      el("text", { x: x(v), y: top + rowH * data.length + 18, "text-anchor": "middle", class: "lbl" }).textContent = v.toFixed(1);
    }
    data.forEach((d, i) => {
      const y = top + rowH * i + rowH / 2;
      const ours = d[0] === "Our allocation";
      const lab = el("text", { x: L - 12, y: y + 4, "text-anchor": "end", class: "tick-net" });
      lab.textContent = d[0];
      if (ours) lab.setAttribute("style", "font-weight:700;fill:var(--accent)");
      [[d[1], "var(--series-1)", -7, "precision"], [d[2], "var(--series-2)", 7, "coverage@κ"]].forEach(([v, col, dy, nm]) => {
        el("line", { x1: x(v[1]), x2: x(v[2]), y1: y + dy, y2: y + dy, stroke: col, "stroke-width": 2.2 });
        const c = el("circle", { cx: x(v[0]), cy: y + dy, r: 6, fill: col, stroke: "var(--bg-card)", "stroke-width": 1.5, style: "cursor:pointer" });
        c.addEventListener("mousemove", ev => {
          const b = chart.getBoundingClientRect();
          tip.textContent = `${d[0]} · ${nm} ${v[0].toFixed(3)} [${v[1].toFixed(3)}, ${v[2].toFixed(3)}]`;
          tip.style.left = Math.min(ev.clientX - b.left + 12, b.width - 280) + "px";
          tip.style.top = (ev.clientY - b.top - 34) + "px";
          tip.style.opacity = 1;
        });
        c.addEventListener("mouseleave", () => { tip.style.opacity = 0; });
      });
    });
    el("line", { x1: x(0.8), x2: x(0.8), y1: top, y2: top + rowH * data.length, stroke: "var(--ink-3)", "stroke-dasharray": "3 4" });
    $("#bench-table tbody").innerHTML = data.map(d => `<tr class="${d[0] === "Our allocation" ? "ours" : ""}"><td>${d[0]}</td>
      <td>${d[1][0].toFixed(3)} <span class="muted">[${d[1][1].toFixed(3)}, ${d[1][2].toFixed(3)}]</span></td>
      <td>${d[2][0].toFixed(3)} <span class="muted">[${d[2][1].toFixed(3)}, ${d[2][2].toFixed(3)}]</span></td>
      <td>${d[3]}</td><td>${d[4]}</td></tr>`).join("");
  }
  $$(".toggle button").forEach(b => b.addEventListener("click", () => {
    $$(".toggle button").forEach(o => o.classList.toggle("on", o === b));
    drawBench(b.dataset.m);
  }));
  drawBench("g37");

  // ---------------------------------------------------------------- copy bibtex
  $$(".copy").forEach(b => b.addEventListener("click", () => {
    const txt = $("#" + b.dataset.copy).textContent;
    (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(
      () => { b.textContent = "Copied"; setTimeout(() => (b.textContent = "Copy BibTeX"), 1500); },
      () => { b.textContent = "Select and copy"; });
  }));
})();
