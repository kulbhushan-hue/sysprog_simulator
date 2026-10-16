import html, random
import streamlit as st
from course_data import MODULES, PHASES, ROADMAP, NEXT_STEPS, QUIZ
from simulator import SysState, execute, HELP
from concept_search import Index

st.set_page_config(page_title="z/OS Sysprog Lab", page_icon="🖥️", layout="wide")
st.markdown("""<style>
.term{background:#000;border:2px solid #1c3b1c;border-radius:8px;padding:12px 16px;min-height:300px;max-height:460px;overflow:auto}
.term pre{color:#33ff33;font-family:'Courier New',monospace;font-size:14px;margin:0;white-space:pre-wrap}
.term .p{color:#4fd8ff}.term .hdr{color:#6c8cff}
</style>""", unsafe_allow_html=True)

SCREENS = [(mi, si) for mi, m in enumerate(MODULES) for si in range(len(m["steps"]))]
ss = st.session_state
for k, v in dict(sys=SysState(), screen=0, hist={}, done=set(), quiz_result=None).items():
    ss.setdefault(k, v)

@st.cache_resource
def get_index():
    return Index([(m["title"], m["concept"] + " " + " ".join(s["text"] + " " + " ".join(s["try"]) for s in m["steps"])) for m in MODULES])

def norm(c): return " ".join(c.upper().split())

def run(cmd):
    cmd = cmd.strip()
    if not cmd: return
    ss.hist.setdefault(ss.screen, []).append((cmd, execute(ss.sys, cmd)))
    mi, si = SCREENS[ss.screen]
    if any(norm(cmd).startswith(norm(t)) for t in MODULES[mi]["steps"][si]["try"]): ss.done.add(ss.screen)

def submit(key): run(ss.get(key, ""))
def go(d): ss.screen = max(0, min(len(SCREENS) - 1, ss.screen + d))
def jump(mi):
    ss.page = "Course"; ss.screen = next(i for i, (m, _) in enumerate(SCREENS) if m == mi)
def clear(): ss.hist[ss.screen] = []
def reset_sys(): ss.sys.reset(); ss.hist = {}

# ---------------- sidebar
st.sidebar.title("🖥️ z/OS Sysprog Lab")
page = st.sidebar.radio("Go to", ["Course", "Roadmap", "Quiz", "Ask the course", "About"], key="page")
st.sidebar.progress(len(ss.done) / len(SCREENS), text=f"{len(ss.done)}/{len(SCREENS)} screens completed")
st.sidebar.button("Reset simulated system", on_click=reset_sys)

if page == "Roadmap":
    st.title("🗺️ Sysprog roadmap")
    for title, mods, goal in ROADMAP:
        with st.expander(title, expanded=True):
            st.write(goal)
            for mi in mods:
                done = sum(1 for i, (m, _) in enumerate(SCREENS) if m == mi - 1 and i in ss.done)
                tot = sum(1 for m, _ in SCREENS if m == mi - 1)
                st.write(f"- Module {mi}: {MODULES[mi-1]['title']}  ({done}/{tot} done)")
                st.button(f"Open module {mi}", key=f"r{mi}", on_click=jump, args=(mi - 1,))
    st.subheader("After this course")
    for n in NEXT_STEPS: st.write("- " + n)

elif page == "Quiz":
    st.title("📝 Self-test (15 questions)")
    rnd = random.Random(7)
    with st.form("quiz"):
        ans = {}
        for i, q in enumerate(QUIZ):
            o = q["opts"][:]; rnd.shuffle(o)
            ans[i] = st.radio(f"{i+1}. {q['q']}", o, index=None, key=f"q{i}")
        ok = st.form_submit_button("Submit")
    if ok:
        wrong = [QUIZ[i] for i in ans if ans[i] != QUIZ[i]["a"]]
        st.success(f"Score: {len(QUIZ) - len(wrong)}/{len(QUIZ)}")
        weak = {}
        for q in wrong: weak[q["m"]] = weak.get(q["m"], 0) + 1
        if weak:
            st.subheader("Recommended revision (weakest first)")
            for m, n in sorted(weak.items(), key=lambda x: -x[1]):
                st.write(f"- Module {m}: {MODULES[m-1]['title']} ({n} missed)")
            with st.expander("Correct answers for missed questions"):
                for q in wrong: st.write(f"**{q['q']}** -> {q['a']}")

elif page == "Ask the course":
    st.title("🔎 Ask the course")
    st.caption("TF-IDF + cosine similarity over the lessons (pure Python, no external API).")
    q = st.text_input("e.g. 'how do I add a library to APF' or 'job will not start'")
    if q:
        hits = get_index().search(q)
        if not hits: st.info("No match. Try other keywords.")
        for (title, _), sc in hits:
            mi = next(i for i, m in enumerate(MODULES) if m["title"] == title)
            st.write(f"**Module {mi+1}: {title}** (match {sc:.2f})")
            st.button(f"Open module {mi+1}", key=f"s{mi}", on_click=jump, args=(mi,))

elif page == "About":
    st.title("About")
    st.write("A simulator built from the *MVS / z/OS Sysprog Concepts* course notes. Output is **simulated**: names, volsers, job numbers and message text are illustrative and will differ on a real LPAR. Check IBM documentation for your release.")
    st.write("Commands that behave statefully: SETPROG APF/LNKLST, S/P/C, V, $-JES2 job/initiator commands, SMP/E RECEIVE/APPLY/ACCEPT/RESTORE.")
    st.code(HELP)

else:
    mi, si = SCREENS[ss.screen]; m = MODULES[mi]
    st.sidebar.selectbox("Jump to module", range(len(MODULES)), index=mi, format_func=lambda i: f"{i+1}. {MODULES[i]['title']}",
                         key="jumpsel", on_change=lambda: jump(ss.jumpsel))
    st.caption(f"Phase {m['phase']}: {PHASES[m['phase']]}  |  Module {m['id']} of {len(MODULES)}  |  Screen {ss.screen+1}/{len(SCREENS)}")
    st.title(f"Module {m['id']}: {m['title']}")
    with st.expander("📖 Concept", expanded=(si == 0)): st.markdown(m["concept"])
    step = m["steps"][si]
    st.markdown(f"**Step {si+1}/{len(m['steps'])}:** {step['text']}")
    cols = st.columns(min(len(step["try"]), 4) or 1)
    for i, t in enumerate(step["try"]):
        cols[i % len(cols)].button(t, key=f"chip{ss.screen}_{i}", on_click=run, args=(t,), use_container_width=True)
    lines = []
    for c, o in ss.hist.get(ss.screen, [])[-6:]:
        lines.append(f'<span class="p">===&gt; {html.escape(c)}</span>\n{html.escape(o)}\n')
    body = "\n".join(lines) or '<span class="hdr">SYSA  READY. Type a command below, or click a suggestion.</span>'
    st.markdown(f'<div class="term"><pre>{body}</pre></div>', unsafe_allow_html=True)
    key = f"cmd_{ss.screen}"
    with st.form(f"f{ss.screen}", clear_on_submit=True):
        c1, c2 = st.columns([6, 1])
        c1.text_input("Command ===>", key=key, label_visibility="collapsed", placeholder="Command ===>  (type HELP for ideas)")
        c2.form_submit_button("Enter", on_click=submit, args=(key,))
    b1, b2, b3, b4 = st.columns([1, 1, 1, 3])
    b1.button("⬅ Back", on_click=go, args=(-1,), disabled=ss.screen == 0)
    b2.button("Clear", on_click=clear)
    b3.button("Next ➡", on_click=go, args=(1,), disabled=ss.screen == len(SCREENS) - 1, type="primary")
    if ss.screen in ss.done: b4.success("Step completed ✔")
    else: b4.info("Run one of the suggested commands to complete this step.")
