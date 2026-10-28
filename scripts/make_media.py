"""Generate the animated media for the project page.

Usage: python3 make_media.py <project_root> <out_dir>
All numbers shown in the animations are taken from main.tex (Case B, Table alloc;
Case D, Table toolsmith; Appendix geometry worked cases). Camera poses in the
retrieval animation are synthetic and labelled as such.
"""
import io
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Circle, FancyArrowPatch
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

INK = "#263238"
INK2 = "#5b6577"
LINE = "#d9dee5"
SOFT = "#f4f6f8"
LLM = "#7451A6"
TOOL = "#168C88"
ORANGE = "#D97732"
RED = "#B55252"
GREEN = "#3A8F5B"
GOLD = "#C89520"
BLUE = "#3366A6"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.edgecolor": INK2,
    "axes.labelcolor": INK2,
    "xtick.color": INK2,
    "ytick.color": INK2,
})

W, H, DPI = 12.8, 7.2, 100  # 1280 x 720


def fig_to_img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save_gif(frames, path, scale=0.75):
    """frames: list of (PIL image, duration_ms)."""
    imgs = []
    durs = []
    for im, d in frames:
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        imgs.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
        durs.append(d)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=durs, loop=0, optimize=True, disposal=2)
    print("wrote", path, len(imgs), "frames")


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def box(ax, x, y, w, h, fc, ec, lw=1.6, r=0.02, alpha=1.0, z=1):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z, transform=ax.transAxes)
    ax.add_patch(p)
    return p


# --------------------------------------------------------------------------------------------
# 1. Delegation loop (Case B, Table alloc)
# --------------------------------------------------------------------------------------------
SUB = [
    dict(k=1, name="Parse request", desc="tag ρ and count κ", df=0.147, dt=0.290,
         f=dict(e=0.02, t="0.35 s", c="0.6k", phi=0.95), tau=dict(e=0.15, t="1 ms", c="0", phi=0.30)),
    dict(k=2, name="Retrieve frames", desc="candidates + pose", df=1.980, dt=0.347,
         f=dict(e=1.00, t="2.40 s", c="12k", phi=0.90), tau=dict(e=0.00, t="0.89 s", c="0", phi=0.60)),
    dict(k=3, name="Visibility", desc="is the asset in the FOV?", df=7.734, dt=0.102,
         f=dict(e=1.00, t="20.9 s", c="23.8k", phi=1.00), tau=dict(e=0.00, t="6 ms", c="0", phi=0.50)),
    dict(k=4, name="Select κ views", desc="diverse viewpoints", df=0.867, dt=0.140,
         f=dict(e=0.50, t="1.20 s", c="0.35k", phi=1.00), tau=dict(e=0.02, t="0.2 ms", c="0", phi=0.40)),
]
ORDER = [2, 1, 3, 0]  # evaluator visits the weakest sub-task first (largest d_k of current mechanism)


def loss_bar_len(v):
    # log scale from 0.05 to 10 mapped to [0, 1]
    return float(np.clip((np.log10(v) - np.log10(0.05)) / (np.log10(10) - np.log10(0.05)), 0.02, 1))


def draw_delegation(st):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # header
    ax.text(0.04, 0.935, "Success-guided agent design", fontsize=22, weight="bold", color=INK, va="center")
    ax.text(0.04, 0.885, "Each sub-task is kept with the LLM or delegated to a tool, by comparing measured design loss  "
            r"$\widehat d_k = w_A\,\widehat e_k + w_T\,\widehat t_k/T_0 + w_C\,\widehat c_k/C_0 + w_F\,(1-\widehat\phi_k)$",
            fontsize=12.5, color=INK2, va="center")

    # request bubble
    if st["request"] > 0:
        a = st["request"]
        box(ax, 0.04, 0.755, 0.62, 0.08, "#eef3fb", BLUE, alpha=a)
        ax.text(0.06, 0.795, "Operator:  “Give me the 10 clearest views of vessel AB230.”", fontsize=15,
                color=INK, va="center", alpha=a)
        box(ax, 0.69, 0.755, 0.27, 0.08, "#f3eefa", LLM, alpha=a)
        ax.text(0.825, 0.795, st.get("planner", "PLANNER  (LLM | human)"), fontsize=12.5, color=LLM,
                ha="center", va="center", weight="bold", alpha=a)

    # sub-task cards
    cw, ch, gap, y0 = 0.205, 0.43, 0.025, 0.25
    for i, s in enumerate(SUB):
        vis = st["cards"][i]
        if vis <= 0:
            continue
        x = 0.04 + i * (cw + gap)
        hl = st.get("hl") == i
        box(ax, x, y0, cw, ch, "white", ORANGE if hl else LINE, lw=3 if hl else 1.6, alpha=vis)
        ax.text(x + 0.015, y0 + ch - 0.04, f"h{s['k']}", fontsize=13, color=ORANGE if hl else INK2,
                weight="bold", family="DejaVu Sans Mono", alpha=vis)
        ax.text(x + 0.055, y0 + ch - 0.04, s["name"], fontsize=14.5, color=INK, weight="bold", alpha=vis)
        ax.text(x + 0.015, y0 + ch - 0.085, s["desc"], fontsize=11.5, color=INK2, alpha=vis)

        # mechanism chip
        mech = st["mech"][i]
        if mech:
            col = {"LLM": LLM, "TOOL": TOOL}[mech]
            lab = {"LLM": f"LLM  f{s['k']}", "TOOL": f"TOOL  τ{s['k']}"}[mech]
            box(ax, x + 0.015, y0 + ch - 0.16, cw - 0.03, 0.055, col, col, alpha=vis)
            ax.text(x + cw / 2, y0 + ch - 0.1325, lab, fontsize=13, color="white", weight="bold",
                    ha="center", va="center", alpha=vis)

        # loss bars
        bx, bw = x + 0.05, cw - 0.125
        for j, (key, col, lab, val) in enumerate([("bf", LLM, f"f{s['k']}", s["df"]), ("bt", TOOL, f"τ{s['k']}", s["dt"])]):
            g = st[key][i]
            if g <= 0:
                continue
            yy = y0 + 0.165 - j * 0.07
            ax.text(x + 0.015, yy + 0.012, lab, fontsize=12, color=col, weight="bold", va="center", alpha=vis)
            ax.add_patch(plt.Rectangle((bx, yy), bw, 0.026, fc=SOFT, ec="none", transform=ax.transAxes))
            ax.add_patch(plt.Rectangle((bx, yy), bw * loss_bar_len(val) * g, 0.026, fc=col, ec="none",
                                       transform=ax.transAxes))
            if g >= 1:
                ax.text(x + cw - 0.012, yy + 0.013, f"{val:.3f}", fontsize=11.5, color=INK, ha="right", va="center", alpha=vis)
        if st["bf"][i] > 0:
            ax.text(x + 0.015, y0 + 0.215, r"local design loss $\widehat{d}_k$ (log bar)", fontsize=10, color=INK2, alpha=vis)

        # verdict
        v = st["verdict"][i]
        if v:
            d = s["df"] - s["dt"]
            ok = d > 0
            ax.text(x + cw / 2, y0 + 0.03, rf"$\widehat{{\Delta}}$ = {d:+.3f}  →  {'accept tool' if ok else 'retain LLM'}",
                    fontsize=11.5, ha="center", va="center", color=GREEN if ok else RED, weight="bold")

    # flow arrows between cards when frozen
    if st.get("frozen", 0) > 0:
        for i in range(3):
            x1 = 0.04 + i * (cw + gap) + cw
            ax.annotate("", xy=(x1 + gap, y0 + ch / 2), xytext=(x1, y0 + ch / 2), xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=2))

    # status bar
    msg = st.get("msg", "")
    if msg:
        box(ax, 0.04, 0.07, 0.92, 0.12, SOFT, LINE)
        ax.text(0.06, 0.13, msg, fontsize=15, color=INK, va="center")
    tag = st.get("tag")
    if tag:
        col = {"PLAN": LLM, "EVALUATE": TOOL, "MAKE TOOL": ORANGE, "GATE": GOLD, "FREEZE": BLUE}[tag]
        box(ax, 0.80, 0.105, 0.14, 0.05, col, col)
        ax.text(0.87, 0.13, tag, fontsize=12, color="white", weight="bold", ha="center", va="center")
    return fig_to_img(fig)


def delegation_frames():
    frames = []
    st = dict(request=0, cards=[0] * 4, mech=[None] * 4, bf=[0] * 4, bt=[0] * 4, verdict=[False] * 4)

    def snap(d=90, **kw):
        s = {**st, **kw}
        s = {k: (list(v) if isinstance(v, list) else v) for k, v in s.items()}
        frames.append((draw_delegation(s), d))

    for a in np.linspace(0, 1, 6):
        st["request"] = ease(a); snap(70, msg="A functional requirement arrives in natural language.")
    snap(1600, msg="A functional requirement arrives in natural language.")
    # planner decomposes
    for i in range(4):
        for a in np.linspace(0, 1, 4):
            st["cards"][i] = ease(a); snap(60, msg="The planner decomposes it into sub-tasks  h = h₄ ∘ h₃ ∘ h₂ ∘ h₁  with contracts σₖ.", tag="PLAN")
    snap(1500, msg="The planner decomposes it into sub-tasks  h = h₄ ∘ h₃ ∘ h₂ ∘ h₁  with contracts σₖ.", tag="PLAN")
    # all-LLM baseline
    st["mech"] = ["LLM"] * 4
    for a in np.linspace(0, 1, 10):
        st["bf"] = [ease(a)] * 4
        snap(60, msg="Start from the all-LLM baseline, and measure error, latency, cost and flexibility per step.", tag="EVALUATE")
    snap(2000, msg="Start from the all-LLM baseline, and measure error, latency, cost and flexibility per step.", tag="EVALUATE")

    for i in ORDER:
        s = SUB[i]
        snap(1500, hl=i, msg=rf"The evaluator flags the weakest step: h{s['k']} ({s['name'].lower()}), $\widehat{{d}}$ = {s['df']:.3f}.", tag="EVALUATE")
        for a in np.linspace(0, 1, 8):
            st["bt"][i] = ease(a)
            snap(60, hl=i, msg=f"The tool maker builds τ{s['k']} from the contract σ{s['k']} and the observed failures.", tag="MAKE TOOL")
        snap(1400, hl=i, msg=f"The tool maker builds τ{s['k']} from the contract σ{s['k']} and the observed failures.", tag="MAKE TOOL")
        st["verdict"][i] = True
        d = s["df"] - s["dt"]
        if d > 0:
            st["mech"][i] = "TOOL"
            m = rf"Gain $\widehat{{\Delta}}_{s['k']}$ = {d:+.3f} > $\delta_{s['k']}$:  the tool replaces the LLM for h{s['k']}."
        else:
            m = rf"$\widehat{{\Delta}}_{s['k']}$ = {d:+.3f}: the parser tool is faster but brittle to paraphrases, so the LLM stays."
        snap(2300, hl=i, msg=m, tag="GATE")

    for a in np.linspace(0, 1, 4):
        snap(80, frozen=a, msg="The allocation is frozen:  f₁ → τ₂ → τ₃ → τ₄.  The LLM keeps language; geometry is computed.", tag="FREEZE")
    snap(3800, frozen=1, msg="The allocation is frozen:  f₁ → τ₂ → τ₃ → τ₄.  The LLM keeps language; geometry is computed.", tag="FREEZE")
    return frames


# --------------------------------------------------------------------------------------------
# 2. FOV geometry (Appendix: Field-of-View Geometry, worked cases)
# --------------------------------------------------------------------------------------------
TH, TV = np.radians(48.5), np.radians(33.4)


def footprint(cam, yaw_deg, pitch_deg, rmax=500.0):
    """Ground footprint of a pinhole camera (ENU, target at origin). Returns 4x2 polygon."""
    psi, th = np.radians(yaw_deg), np.radians(pitch_deg)
    d = np.array([np.cos(th) * np.sin(psi), np.cos(th) * np.cos(psi), np.sin(th)])
    r = np.array([np.cos(psi), -np.sin(psi), 0.0])
    u = np.cross(r, d)
    pts = []
    for sh, sv in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        q = d + sh * np.tan(TH / 2) * r + sv * np.tan(TV / 2) * u
        if q[2] < -1e-6:
            t = -cam[2] / q[2]
            g = cam[:2] + t * q[:2]
        else:
            g = cam[:2] + q[:2] / (np.linalg.norm(q[:2]) + 1e-9) * rmax
        v = g - cam[:2]
        n = np.linalg.norm(v)
        if n > rmax:
            g = cam[:2] + v / n * rmax
        pts.append(g)
    return np.array(pts)


def inside(poly, p):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                c = not c
    return c


def heuristic(cam, yaw_deg):
    bearing = np.degrees(np.arctan2(-cam[0], -cam[1])) % 360
    gap = abs((yaw_deg - bearing + 180) % 360 - 180)
    return gap < 25, gap


def draw_fov(cam, yaw, pitch, caption):
    fig = plt.figure(figsize=(W, H))
    fig.text(0.04, 0.935, "Why visibility is computed, not inferred", fontsize=22, weight="bold", color=INK, va="center")
    fig.text(0.04, 0.885, "Projection tool τ₃ intersects the four corner rays with the ground plane and tests whether the asset lies in the footprint.",
             fontsize=12.5, color=INK2, va="center")

    poly = footprint(cam, yaw, pitch)
    geo = inside(poly, (0, 0))
    heur, gap = heuristic(cam, yaw)

    # top-down map
    ax = fig.add_axes([0.04, 0.12, 0.40, 0.70])
    ax.set_aspect("equal"); ax.set_xlim(-160, 110); ax.set_ylim(-120, 120)
    ax.set_facecolor("#fbfbf8")
    ax.grid(color=LINE, lw=0.6)
    ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
    ax.set_title("top-down: ground footprint", fontsize=12.5, color=INK2)
    ax.add_patch(Polygon(poly, closed=True, fc=(TOOL if geo else RED), alpha=0.18, ec=(TOOL if geo else RED), lw=2))
    for p in poly:
        ax.plot([cam[0], p[0]], [cam[1], p[1]], color=INK2, lw=0.7, alpha=0.5)
    for a in [(-30, 25), (35, -40), (-60, -50), (20, 60)]:
        ax.add_patch(plt.Rectangle((a[0] - 4, a[1] - 4), 8, 8, fc="#c9ced6", ec="none"))
    ax.plot(0, 0, marker="*", ms=20, color=(TOOL if geo else RED), mec="white", mew=1.2, zorder=5)
    ax.text(4, -12, "AB230", fontsize=11, color=INK, weight="bold")
    ax.plot(cam[0], cam[1], marker="o", ms=11, color=INK, zorder=6)
    dv = np.array([np.sin(np.radians(yaw)), np.cos(np.radians(yaw))]) * 22
    ax.annotate("", xy=(cam[0] + dv[0], cam[1] + dv[1]), xytext=(cam[0], cam[1]),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=2))
    ax.text(cam[0] + 4, cam[1] + 8, "camera", fontsize=10.5, color=INK)

    # side view (along the camera heading)
    ax2 = fig.add_axes([0.52, 0.47, 0.44, 0.33])
    ax2.set_xlim(-160, 60); ax2.set_ylim(-5, 95)
    ax2.set_title("side view along the camera heading", fontsize=12.5, color=INK2)
    ax2.axhline(0, color=INK2, lw=1.2)
    ax2.set_xlabel("distance ahead of camera (m, negative = in front)")
    ax2.set_ylabel("height (m)")
    ax2.grid(color=LINE, lw=0.6)
    # project target onto heading axis
    hd = np.array([np.sin(np.radians(yaw)), np.cos(np.radians(yaw))])
    t_along = np.dot(-np.array(cam[:2]), hd)
    h = cam[2]
    th = np.radians(pitch)
    for a, ls in [(th - TV / 2, "-"), (th + TV / 2, "-"), (th, ":")]:
        if a < -1e-3:
            dist = min(h / np.tan(-a), 500)
        else:
            dist = 500
        ax2.plot([0, -dist], [h, max(h - dist * np.tan(-a), 0) if a < 0 else h + dist * np.tan(a)], ls, color=INK2, lw=1.2)
    near = h / np.tan(-(th - TV / 2)) if (th - TV / 2) < 0 else 0
    far = h / np.tan(-(th + TV / 2)) if (th + TV / 2) < -1e-3 else 500
    ax2.fill_between([-min(far, 500), -near], 0, 4, color=(TOOL if geo else RED), alpha=0.35)
    ax2.plot(0, h, "o", color=INK, ms=11)
    ax2.plot(-t_along, 0, marker="*", ms=18, color=(TOOL if geo else RED), mec="white", zorder=5)

    # verdict board
    ax3 = fig.add_axes([0.52, 0.10, 0.44, 0.28]); ax3.axis("off"); ax3.set_xlim(0, 1); ax3.set_ylim(0, 1)
    ax3.text(0.0, 0.92, f"camera 60 m high · yaw {yaw:.0f}° · pitch {pitch:.0f}° · bearing gap {gap:.0f}°",
             fontsize=12.5, color=INK2, va="center")
    for j, (lab, ok, col) in enumerate([("Prompt heuristic  (bearing gap < 25°)", heur, LLM),
                                         ("Projection tool τ₃  (footprint test)", geo, TOOL)]):
        y = 0.62 - j * 0.32
        box(ax3, 0.0, y - 0.12, 1.0, 0.24, "white", col, lw=2)
        ax3.text(0.03, y, lab, fontsize=14, color=col, weight="bold", va="center")
        box(ax3, 0.80, y - 0.085, 0.17, 0.17, GREEN if ok else RED, GREEN if ok else RED)
        ax3.text(0.885, y, "IN" if ok else "OUT", fontsize=15, color="white", weight="bold", ha="center", va="center")
    fig.text(0.04, 0.045, caption, fontsize=14.5, color=INK, va="center")
    return fig_to_img(fig)


def fov_frames():
    frames = []
    cam = np.array([40.0, 0.0, 60.0])
    # pitch sweep while facing the target directly (gap = 0)
    for p in list(np.linspace(-20, -88, 30)):
        frames.append((draw_fov(cam, 270, p, "Facing AB230 directly: the heuristic always says IN, but geometry depends on pitch."), 140))
    frames.append((draw_fov(cam, 270, -35, "Worked case (paper App. C): 40 m east, yaw 270°, pitch −35°: footprint stops at E = −7.4 m, so OUT."), 3200))
    # yaw sweep at a pitch that frames the target
    for y in list(np.linspace(270, 330, 18)) + list(np.linspace(330, 250, 26)):
        frames.append((draw_fov(cam, y, -55, "Turning the camera: angular gap and footprint disagree near the frame edge."), 120))
    # nadir worked cases
    for x in np.linspace(10, 40, 14):
        frames.append((draw_fov(np.array([x, 0, 60.0]), 270, -90, "Nadir camera at 60 m: in at 10 m east, out at 40 m east. Distance alone does not decide."), 150))
    frames.append((draw_fov(np.array([40, 0, 60.0]), 270, -90, "Nadir camera at 60 m: in at 10 m east, out at 40 m east. Distance alone does not decide."), 2500))
    return frames


# --------------------------------------------------------------------------------------------
# 3. Retrieval pipeline (Case B) on synthetic poses
# --------------------------------------------------------------------------------------------
def synth_cameras(n=420, seed=3):
    rng = np.random.default_rng(seed)
    cams = []
    while len(cams) < n:
        r = 15 + 130 * np.sqrt(rng.random())
        a = rng.random() * 2 * np.pi
        x, y = r * np.cos(a), r * np.sin(a)
        # the survey looks at many assets: yaw toward a random point of the site
        site = rng.normal(0, 60, size=2)
        yaw = np.degrees(np.arctan2(site[0] - x, site[1] - y)) % 360 + rng.normal(0, 10)
        pitch = rng.uniform(-80, -25)
        h = rng.uniform(35, 80)
        poly = footprint(np.array([x, y, h]), yaw, pitch)
        cams.append((x, y, yaw, pitch, h, inside(poly, (0, 0))))
    return cams


def fps(points, k):
    sel = [int(np.argmax(np.linalg.norm(points, axis=1)))]
    d = np.linalg.norm(points - points[sel[0]], axis=1)
    while len(sel) < k:
        i = int(np.argmax(d))
        sel.append(i)
        d = np.minimum(d, np.linalg.norm(points - points[i], axis=1))
    return sel


def draw_retrieval(cams, shown, stage, chosen, title_msg, nearest=None):
    fig = plt.figure(figsize=(W, H))
    fig.text(0.04, 0.935, "Case B · asset-aware retrieval, delegated", fontsize=22, weight="bold", color=INK, va="center")
    fig.text(0.04, 0.885, "Request: 10 clearest views of AB230.   LLM keeps h₁ (parsing); tools run h₂ retrieve → h₃ visibility → h₄ selection.",
             fontsize=12.5, color=INK2, va="center")
    ax = fig.add_axes([0.04, 0.12, 0.52, 0.72])
    ax.set_aspect("equal"); ax.set_xlim(-155, 155); ax.set_ylim(-150, 150)
    ax.set_facecolor("#fbfbf8"); ax.grid(color=LINE, lw=0.6)
    ax.set_xticks([]); ax.set_yticks([])
    for i in range(shown):
        x, y, yaw, p, h, vis = cams[i]
        if stage >= 2:
            col, a, s = (TOOL, 0.9, 18) if vis else ("#c3c9d2", 0.5, 10)
        else:
            col, a, s = (INK2, 0.6, 12)
        ax.scatter([x], [y], s=s, color=col, alpha=a, lw=0)
    if nearest is not None:
        for i in nearest:
            x, y, yaw, p, h, vis = cams[i]
            ax.scatter([x], [y], s=110, facecolor="none", edgecolor=GREEN if vis else RED, lw=2.2)
    for n, i in enumerate(chosen):
        x, y, yaw, p, h, vis = cams[i]
        dv = np.array([np.sin(np.radians(yaw)), np.cos(np.radians(yaw))]) * 18
        ax.annotate("", xy=(x + dv[0], y + dv[1]), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2))
        ax.scatter([x], [y], s=150, color=ORANGE, edgecolor="white", lw=1.5, zorder=6)
        ax.text(x, y, str(n + 1), fontsize=8.5, color="white", ha="center", va="center", weight="bold", zorder=7)
    ax.plot(0, 0, marker="*", ms=22, color=INK, mec="white", zorder=8)
    ax.text(6, -14, "AB230", fontsize=11, weight="bold", color=INK)
    ax.text(-150, -143, "synthetic camera poses, for illustration", fontsize=9.5, color=INK2)

    # pipeline column
    axp = fig.add_axes([0.60, 0.12, 0.37, 0.72]); axp.axis("off"); axp.set_xlim(0, 1); axp.set_ylim(0, 1)
    steps = [("h₁", "Parse “AB230”, κ = 10", "LLM f₁", LLM),
             ("h₂", "Bulk retrieve nearby frames", "tool τ₂ · 0.89 s", TOOL),
             ("h₃", "In field of view?", "tool τ₃ · 0.02 ms/frame", TOOL),
             ("h₄", "Farthest-point selection", "tool τ₄ · 0.2 ms", TOOL)]
    for j, (k, name, mech, col) in enumerate(steps):
        y = 0.86 - j * 0.2
        active = j == stage
        done = j < stage
        box(axp, 0.0, y - 0.075, 1.0, 0.15, "white" if not active else "#fff7ef", ORANGE if active else (col if done else LINE), lw=2.4 if active else 1.5)
        axp.text(0.04, y + 0.02, k, fontsize=13, weight="bold", color=INK2, family="DejaVu Sans Mono", va="center")
        axp.text(0.15, y + 0.025, name, fontsize=13.5, color=INK, weight="bold", va="center")
        box(axp, 0.15, y - 0.055, 0.5, 0.05, col, col, r=0.01)
        axp.text(0.4, y - 0.03, mech, fontsize=10.5, color="white", ha="center", va="center", weight="bold")
        if done:
            axp.text(0.94, y, "✓", fontsize=20, color=GREEN, ha="center", va="center")
    axp.text(0.0, 0.03, title_msg, fontsize=13, color=INK, va="bottom", wrap=True)
    return fig_to_img(fig)


def retrieval_frames():
    cams = synth_cameras()
    frames = []
    pts = np.array([[c[0], c[1]] for c in cams])
    n = len(cams)
    frames.append((draw_retrieval(cams, 0, 0, [], "The LLM parses the request:\ntarget AB230, κ = 10."), 2000))
    for s in np.linspace(0, n, 12).astype(int)[1:]:
        frames.append((draw_retrieval(cams, s, 1, [], "τ₂ pulls every nearby frame with its\npose in one bulk query."), 90))
    frames.append((draw_retrieval(cams, n, 1, [], "τ₂ pulls every nearby frame with its\npose in one bulk query."), 1500))
    near = list(np.argsort(np.linalg.norm(pts, axis=1))[:10])
    hit = sum(cams[i][5] for i in near)
    frames.append((draw_retrieval(cams, n, 1, [], f"Proximity is a weak signal: the 10 nearest\nframes contain the asset only {hit}/10 times.", nearest=near), 3000))
    frames.append((draw_retrieval(cams, n, 2, [], "τ₃ projects each camera footprint and keeps\nonly frames that contain AB230."), 2600))
    vis = [i for i in range(n) if cams[i][5]]
    order = fps(pts[vis], 10)
    chosen = []
    for o in order:
        chosen.append(vis[o])
        frames.append((draw_retrieval(cams, n, 3, list(chosen), "τ₄ picks 10 distinct viewpoints among\nthe valid frames (farthest-point)."), 380))
    frames.append((draw_retrieval(cams, n, 4, list(chosen), "10 / 10 in frame, spread around the asset,\nwith no model in the serving path."), 3500))
    return frames


# --------------------------------------------------------------------------------------------
# 4. Tool maker (Case D, Table toolsmith)
# --------------------------------------------------------------------------------------------
def draw_toolmaker(state, msg):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.04, 0.935, "Case D · when the tool maker is an LLM", fontsize=22, weight="bold", color=INK, va="center")
    ax.text(0.04, 0.885, "Same model, same examples. Only the specification differs: with or without the 5 field clauses of this corpus.",
            fontsize=12.5, color=INK2, va="center")
    labels = ["toward", "away", "sideways", "bearing A", "bearing B", "distant", "nadir", "no position",
              "no yaw", "no pitch", "vendor keys", "alt = 0", "shallow pitch"]
    for r, arm in enumerate(["full", "core"]):
        y = 0.66 - r * 0.33
        title = "Spec WITH field clauses" if arm == "full" else "Spec WITHOUT field clauses"
        box(ax, 0.04, y - 0.13, 0.92, 0.27, "white", LINE)
        ax.text(0.06, y + 0.095, title, fontsize=15, weight="bold", color=TOOL if arm == "full" else RED)
        ax.text(0.40, y + 0.095, state[arm]["ver"], fontsize=12.5, color=INK2)
        for i, lab in enumerate(labels):
            x = 0.06 + i * 0.068
            st = state[arm]["tests"][i]
            col = {"pending": "#e7eaee", "pass": GREEN, "fail": RED, "skip": "white"}[st]
            ec = GOLD if i >= 8 else LINE
            box(ax, x, y - 0.03, 0.058, 0.08, col, ec, lw=2 if i >= 8 else 1.2, r=0.01)
            if st == "skip":
                ax.text(x + 0.029, y + 0.01, "not\ngated", fontsize=8, ha="center", va="center", color=INK2)
            ax.text(x + 0.029, y - 0.06, lab, fontsize=8.6, ha="center", va="center", color=INK2, rotation=0)
        ax.text(0.06, y - 0.105, "8 core tests", fontsize=10.5, color=INK2)
        ax.text(0.06 + 8 * 0.068, y - 0.105, "5 field tests (corpus conventions)", fontsize=10.5, color=GOLD, weight="bold")
        if state[arm].get("res"):
            ax.text(0.94, y + 0.095, state[arm]["res"], fontsize=13, color=INK, ha="right", weight="bold")
    box(ax, 0.04, 0.05, 0.92, 0.1, SOFT, LINE)
    ax.text(0.06, 0.10, msg, fontsize=15, color=INK, va="center")
    return fig_to_img(fig)


def toolmaker_frames():
    frames = []
    S = {a: dict(ver="", tests=["pending"] * 13) for a in ["full", "core"]}
    S["core"]["tests"] = ["pending"] * 8 + ["skip"] * 5

    def snap(d, msg):
        frames.append((draw_toolmaker({k: dict(v, tests=list(v["tests"])) for k, v in S.items()}, msg), d))

    snap(2000, "Each arm writes in_field_of_view(row, lat, lon) from a contract; it never sees the reference code.")
    S["full"]["ver"] = S["core"]["ver"] = "version 1"
    for i in range(13):
        S["full"]["tests"][i] = "pass"
        if i < 8:
            S["core"]["tests"][i] = "fail" if i == 6 else "pass"
        snap(110, "The generated code runs against the acceptance gate described to its arm.")
    snap(2000, "The core arm fails one assertion; it gets the failing test and may repair (up to 3 times).")
    S["core"]["ver"] = "version 2 (repaired)"
    S["core"]["tests"][6] = "pass"
    S["full"]["res"] = "gate passed · pass@1 = 1.00"
    S["core"]["res"] = "gate passed · pass@3 = 1.00"
    snap(2600, "Both arms are certified by their own gates.")
    for i in range(8, 13):
        S["core"]["tests"][i] = "fail"
        snap(260, "Now run the core tool on all 13 tests …")
    S["core"]["res"] = "all 13: 0.00 · field frames 0.625"
    S["full"]["res"] = "all 13: 1.00 · field frames 0.964"
    snap(4200, "It cannot recover conventions absent from its spec. The spec and its validation, not the maker, set reliability.")
    return frames


# --------------------------------------------------------------------------------------------
# 5. Grounding slideshow from the paper images
# --------------------------------------------------------------------------------------------
def card_from_image(path, label, sub, col):
    canvas = Image.new("RGB", (1280, 720), "white")
    im = Image.open(path).convert("RGB")
    im.thumbnail((700, 600))
    canvas.paste(im, (40 + (700 - im.width) // 2, 80 + (600 - im.height) // 2))
    d = ImageDraw.Draw(canvas)
    fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    fr = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
    fs = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
    d.text((40, 24), "Prompt:  “Highlight the vessel AB230”", font=fr, fill=INK2)
    d.rounded_rectangle((780, 200, 1240, 260), radius=12, fill=col)
    d.text((800, 213), label, font=fb, fill="white")
    y = 290
    for line in sub:
        d.text((780, y), line, font=fr, fill=INK)
        y += 36
    d.text((780, 660), "gemini-3.7-flash, single call · images from the paper", font=fs, fill=INK2)
    return canvas


def grounding_frames():
    F = os.path.join(ROOT, "Figures")
    cards = [
        card_from_image(os.path.join(F, "gemini.png"), "(a) Tag legible", ["The returned box tightly and", "correctly localizes the asset."], GREEN),
        card_from_image(os.path.join(F, "gt2.png"), "(b) Confident, but wrong", ["Oblique view, tag cropped.", "The model returns found = true", "and boxes the wrong object."], RED),
        card_from_image(os.path.join(F, "image1.png"), "(b) Ground truth", ["The same frame: AB230 is the", "cropped vessel on the right edge."], GREEN),
        card_from_image(os.path.join(F, "image2.png"), "(c) FOV tool output", ["Deterministic projection certifies", "geometric inclusion, or returns ∅", "instead of a plausible box."], TOOL),
    ]
    frames = []
    for i, c in enumerate(cards):
        frames.append((c, 3200))
        nxt = cards[(i + 1) % len(cards)]
        for a in np.linspace(0.2, 0.8, 4):
            frames.append((Image.blend(c, nxt, float(a)), 70))
    return frames


# --------------------------------------------------------------------------------------------
# Title cards and video
# --------------------------------------------------------------------------------------------
def title_card(kicker, title, sub):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc="#10161d", transform=ax.transAxes))
    ax.text(0.08, 0.62, kicker.upper(), fontsize=15, color="#5fd3c8", weight="bold")
    ax.text(0.08, 0.50, title, fontsize=38, color="white", weight="bold", va="center")
    ax.text(0.08, 0.38, sub, fontsize=17, color="#b7c0cc", va="center")
    return fig_to_img(fig)


def image_card(path, title, caption):
    canvas = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(canvas)
    fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)
    fr = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    d.text((50, 30), title, font=fb, fill=INK)
    im = Image.open(path).convert("RGB")
    im.thumbnail((1180, 540))
    canvas.paste(im, ((1280 - im.width) // 2, 95 + (540 - im.height) // 2))
    d.text((50, 660), caption, font=fr, fill=INK2)
    return canvas


def write_video(segments, path, fps_=10):
    tmp = os.environ.get("FRAMES_DIR", path + "_frames")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    idx = 0
    chapters = []
    t = 0.0
    for name, frames in segments:
        chapters.append((name, round(t, 1)))
        for im, d in frames:
            reps = max(1, int(round(d / 1000 * fps_)))
            im = im.resize((1280, 720))
            for _ in range(reps):
                im.save(os.path.join(tmp, f"{idx:05d}.png"))
                idx += 1
                t += 1 / fps_
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps_), "-i", os.path.join(tmp, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-movflags", "+faststart", path], check=True)
    print("wrote", path, f"{t:.1f}s", chapters)
    return chapters


if __name__ == "__main__":
    which = set(sys.argv[3:]) or {"all"}
    dele = delegation_frames(); save_gif(dele, os.path.join(OUT, "delegation_loop.gif"))
    fov = fov_frames(); save_gif(fov, os.path.join(OUT, "fov_geometry.gif"))
    ret = retrieval_frames(); save_gif(ret, os.path.join(OUT, "caseB_retrieval.gif"))
    tm = toolmaker_frames(); save_gif(tm, os.path.join(OUT, "caseD_toolmaker.gif"))
    gr = grounding_frames(); save_gif(gr, os.path.join(OUT, "caseA_grounding.gif"), scale=0.6)
    imgdir = os.path.join(os.path.dirname(OUT), "images", "paper")
    segments = [
        ("Intro", [(title_card("PhysWorldAI · NeurIPS 2026 Workshop", "Geometry Is Not a Prompt",
                               "What physical-world agents should compute instead of infer"), 3500)]),
        ("Failure", [(title_card("Case A", "An LLM can be confident and wrong", "Visual grounding of an industrial asset"), 2000)] + gr[:-4]),
        ("Delegation", [(title_card("Method", "Mechanism allocation", "Keep each sub-task with the LLM, or delegate it to a tool, by measured design loss"), 2500)] + dele),
        ("Geometry", [(title_card("Why compute", "Visibility is a projection", "Camera pose and field of view decide, not proximity or prose"), 2000)] + fov),
        ("Retrieval", [(title_card("Case B", "Asset-aware retrieval", "Parse with the LLM; retrieve, filter and select with tools"), 2000)] + ret),
        ("Tool maker", [(title_card("Case D", "The LLM as tool maker", "Reliability comes from the specification and its validation"), 2000)] + tm),
        ("Results", [(title_card("Frozen held-out evaluation", "24 unseen assets · 9,600 frames", "Independent projection oracle and pixel adjudication"), 2000),
                     (image_card(os.path.join(imgdir, "frozen_bench.png"), "Same precision as code generation, 17× fewer tokens",
                                 "Our allocation: precision 0.982 at 0.83 s and 101 tokens per request (Gemini 3.7)."), 6000),
                     (image_card(os.path.join(imgdir, "frozen_alloc.png"), "The local rule recovers a near-best complete design",
                                 "Cross-fitted loss 0.604 vs 0.594 for the best of all 16 allocations; worst is 2.523."), 6000),
                     (title_card("Takeaway", "Infer what is linguistic. Compute what is physical.",
                                 "Use independent ground truth to decide where the boundary lies."), 4000)]),
    ]
    ch = write_video(segments, os.path.join(OUT, "walkthrough.mp4"))
    with open(os.path.join(OUT, "chapters.txt"), "w") as f:
        for n, t in ch:
            f.write(f"{n}\t{t}\n")
    # posters
    dele[-1][0].save(os.path.join(OUT, "poster_delegation.jpg"), quality=88)
    segments[0][1][0][0].save(os.path.join(OUT, "poster_walkthrough.jpg"), quality=88)
