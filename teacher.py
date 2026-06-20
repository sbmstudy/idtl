# pages/teacher.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import io
import PyPDF2

# ── Helper Functions ──────────────────────────────────────────

def get_teacher_classes(supabase, teacher_id):
    res = supabase.table("classes")\
        .select("*")\
        .eq("teacher_id", teacher_id)\
        .execute()
    return res.data if res.data else []

def get_class_students(supabase, class_id):
    res = supabase.table("student_classes")\
        .select("*, users(id, name, email)")\
        .eq("class_id", class_id)\
        .execute()
    return res.data if res.data else []

def get_weak_topics(supabase, student_ids):
    if not student_ids:
        return []
    res = supabase.table("weak_topics")\
        .select("*")\
        .in_("student_id", student_ids)\
        .execute()
    return res.data if res.data else []

def get_all_students(supabase):
    res = supabase.table("users")\
        .select("*")\
        .eq("role", "student")\
        .execute()
    return res.data if res.data else []

def upload_notes(supabase, teacher_id,
                 class_id, file, summary):
    supabase.table("notes").insert({
        "uploaded_by": teacher_id,
        "class_id":    class_id,
        "file_name":   file.name,
        "file_url":    "teacher_upload",
        "ai_summary":  summary
    }).execute()

# ── Main Teacher Page ─────────────────────────────────────────

def show_teacher(supabase, model):
    teacher    = st.session_state.user
    teacher_id = teacher["id"]

    st.markdown(f"""
    <div style='background:linear-gradient(
        135deg,#11998e,#38ef7d);
        padding:1.5rem;border-radius:12px;
        color:white;margin-bottom:1rem'>
        <h2>👨‍🏫 Teacher Dashboard</h2>
        <p>Welcome, {teacher['name']}!</p>
    </div>
    """, unsafe_allow_html=True)

    classes = get_teacher_classes(supabase, teacher_id)

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Analytics",
        "📢 Announcements",
        "📄 Upload Notes",
        "🎥 YT Research",
        "🤖 AI Research"
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1 — ANALYTICS
    # ════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Class Analytics")

        if not classes:
            st.info("Koi class nahi hai abhi.")
        else:
            # Class selector
            class_names = {
                c["class_name"]: c["id"] for c in classes}
            selected = st.selectbox(
                "Class select karo",
                list(class_names.keys()))
            class_id = class_names[selected]

            students = get_class_students(
                supabase, class_id)
            student_ids = [
                s["users"]["id"] for s in students
                if s.get("users")]

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Students",
                        len(students))

            weak_topics = get_weak_topics(
                supabase, student_ids)
            col2.metric("Weak Topics Detected",
                        len(weak_topics))

            unique_topics = len(set(
                w["topic_name"] for w in weak_topics))
            col3.metric("Unique Topics", unique_topics)

            st.divider()

            # Weak topics chart
            if weak_topics:
                df = pd.DataFrame(weak_topics)

                # Topic frequency bar chart
                topic_freq = df.groupby(
                    "topic_name")["frequency"]\
                    .sum().reset_index()
                topic_freq.columns = ["Topic", "Frequency"]
                topic_freq = topic_freq.sort_values(
                    "Frequency", ascending=False)

                fig1 = px.bar(
                    topic_freq,
                    x="Topic",
                    y="Frequency",
                    title="Most Struggled Topics",
                    color="Frequency",
                    color_continuous_scale="Reds"
                )
                st.plotly_chart(
                    fig1, use_container_width=True)

                # Subject wise pie chart
                if "subject" in df.columns:
                    subj = df.groupby(
                        "subject").size().reset_index()
                    subj.columns = ["Subject", "Count"]
                    fig2 = px.pie(
                        subj,
                        values="Count",
                        names="Subject",
                        title="Subject wise Weak Areas"
                    )
                    st.plotly_chart(
                        fig2, use_container_width=True)

                # Student wise weak topics
                st.subheader("Student wise Analysis")
                for s in students:
                    if not s.get("users"):
                        continue
                    sid  = s["users"]["id"]
                    name = s["users"]["name"]
                    student_weak = [
                        w for w in weak_topics
                        if w["student_id"] == sid]

                    if student_weak:
                        with st.expander(
                            f"👤 {name} — "
                            f"{len(student_weak)} weak topics"):
                            for w in student_weak:
                                st.write(
                                    f"• **{w['topic_name']}**"
                                    f" ({w['subject']}) — "
                                    f"frequency: {w['frequency']}")
            else:
                st.info("Abhi koi weak topics detect "
                        "nahi hue hain.")

    # ════════════════════════════════════════════════════════
    # TAB 2 — ANNOUNCEMENTS
    # ════════════════════════════════════════════════════════
    with tab2:
        st.subheader("📢 Announcement Post Karo")

        if not classes:
            st.info("Pehle class banao.")
        else:
            class_names = {
                c["class_name"]: c["id"]
                for c in classes}
            sel_class = st.selectbox(
                "Class", list(class_names.keys()),
                key="ann_class")
            class_id = class_names[sel_class]

            title   = st.text_input("Title")
            content = st.text_area("Content", height=120)

            if st.button("Post Karo 📢"):
                if title and content:
                    supabase.table("announcements").insert({
                        "teacher_id": teacher_id,
                        "class_id":   class_id,
                        "title":      title,
                        "content":    content
                    }).execute()
                    st.success("Announcement posted ✅")
                else:
                    st.warning("Title aur content dono do")

            # Previous announcements
            st.divider()
            st.subheader("Previous Announcements")
            ann = supabase.table("announcements")\
                .select("*")\
                .eq("teacher_id", teacher_id)\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()

            if ann.data:
                for a in ann.data:
                    with st.expander(f"📌 {a['title']}"):
                        st.write(a["content"])
                        st.caption(a["created_at"])
            else:
                st.info("Koi announcement nahi hai abhi.")

    # ════════════════════════════════════════════════════════
    # TAB 3 — UPLOAD NOTES
    # ════════════════════════════════════════════════════════
    with tab3:
        st.subheader("📄 Notes Upload Karo")

        if not classes:
            st.info("Pehle class banao.")
        else:
            class_names = {
                c["class_name"]: c["id"]
                for c in classes}
            sel_class = st.selectbox(
                "Class", list(class_names.keys()),
                key="notes_class")
            class_id = class_names[sel_class]

            pdf_file = st.file_uploader(
                "PDF upload karo", type=["pdf"])

            if pdf_file:
                # PDF text extract
                reader = PyPDF2.PdfReader(
                    io.BytesIO(pdf_file.read()))
                pdf_text = ""
                for page in reader.pages:
                    pdf_text += page.extract_text()

                if st.button("Upload + AI Summary Banao"):
                    with st.spinner("Process ho raha hai..."):
                        # AI summary
                        summary_prompt = f"""
                        Teacher ke PDF notes ka
                        structured summary banao:
                        
                        ## Key Topics
                        ## Important Concepts
                        ## Student ke liye Notes
                        
                        Content: {pdf_text[:4000]}
                        """
                        summary = model.generate_content(
                            summary_prompt)

                        upload_notes(
                            supabase, teacher_id,
                            class_id, pdf_file,
                            summary.text)

                        st.success("Notes uploaded ✅")
                        st.markdown(summary.text)

    # ════════════════════════════════════════════════════════
    # TAB 4 — YOUTUBE RESEARCH
    # ════════════════════════════════════════════════════════
    with tab4:
        st.subheader("🎥 YouTube — Research Notes")

        yt_url = st.text_input("YouTube URL paste karo")

        if yt_url and st.button("Research Notes Banao"):
            with st.spinner("Video analyze ho raha hai..."):
                try:
                    yt_model = genai.GenerativeModel(
                        'gemini-2.5-flash')

                    response = yt_model.generate_content([
                        {"file_data": {
                            "file_uri": yt_url}},
                        """Is video ka deep research
                        analysis banao teacher ke liye:

                        ## Core Concepts
                        ## Teaching Points
                        ## Student Misconceptions
                        ## Discussion Questions
                        ## Further Research Areas

                        Academic aur detailed rakho."""
                    ])

                    st.markdown(response.text)
                    st.session_state.teacher_yt = \
                        response.text

                    # Save
                    supabase.table("notes").insert({
                        "uploaded_by": teacher_id,
                        "file_name":   f"Research: {yt_url}",
                        "file_url":    yt_url,
                        "ai_summary":  response.text
                    }).execute()
                    st.success("Research saved ✅")

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # ════════════════════════════════════════════════════════
    # TAB 5 — AI RESEARCH ASSISTANT
    # ════════════════════════════════════════════════════════
    with tab5:
        st.subheader("🤖 AI Research Assistant")
        st.caption(
            "Apni research aur teaching ke liye "
            "Gemini se deep insights lo")

        # Class weak topics context
        if classes:
            class_names = {
                c["class_name"]: c["id"]
                for c in classes}
            sel = st.selectbox(
                "Class context lo",
                ["None"] + list(class_names.keys()),
                key="ai_class")

            context = ""
            if sel != "None":
                cid      = class_names[sel]
                students = get_class_students(
                    supabase, cid)
                sids     = [
                    s["users"]["id"] for s in students
                    if s.get("users")]
                weak     = get_weak_topics(supabase, sids)
                if weak:
                    topics_list = ", ".join(set(
                        w["topic_name"] for w in weak))
                    context = (
                        f"Class weak topics: {topics_list}")

        research_q = st.text_area(
            "Research question ya teaching problem likho",
            height=100)

        if st.button("Deep Analysis Karo 🔬"):
            if research_q:
                with st.spinner("Research ho rahi hai..."):
                    prompt = f"""
                    Tu ek expert educational researcher hai.
                    Teacher ke liye deep analysis kar.

                    {context}

                    Teacher ka question: {research_q}

                    Provide:
                    ## Research Insights
                    ## Teaching Strategies
                    ## Student Engagement Tips
                    ## Common Misconceptions
                    ## Recommended Resources
                    """
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
            else:
                st.warning("Question likho pehle")