# pages/student.py
import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import re

# ── Helper Functions ──────────────────────────────────────────

def get_chat_history(supabase, student_id):
    """Supabase se permanent history load karo"""
    res = supabase.table("conversations")\
        .select("*")\
        .eq("student_id", student_id)\
        .order("created_at")\
        .execute()
    return res.data if res.data else []

def save_message(supabase, student_id, role, message):
    """Har message Supabase mein save karo"""
    supabase.table("conversations").insert({
        "student_id": student_id,
        "role": role,
        "message": message,
        "created_at": datetime.now().isoformat()
    }).execute()

def extract_weak_topics(supabase, model, student_id, conversation):
    """Gemini se weak topics extract karo accurately"""
    if len(conversation) < 4:
        return

    convo_text = "\n".join([
        f"{m['role']}: {m['message']}"
        for m in conversation[-10:]
    ])

    prompt = f"""
    Analyze this student-AI conversation carefully.
    Extract topics where student showed confusion,
    made mistakes, or asked repeated questions.

    Return ONLY valid JSON, nothing else:
    {{
        "weak_topics": [
            {{"topic": "topic name", "subject": "subject name"}}
        ],
        "summary": "2 line conversation summary"
    }}

    If no weak topics found, return:
    {{"weak_topics": [], "summary": "summary here"}}

    Conversation:
    {convo_text}
    """

    try:
        res = model.generate_content(prompt)
        text = res.text.strip()
        # JSON extract karo
        import json
        start = text.find("{")
        end   = text.rfind("}") + 1
        data  = json.loads(text[start:end])

        # Weak topics save karo
        for topic in data.get("weak_topics", []):
            # Check karo already exists toh frequency badha
            existing = supabase.table("weak_topics")\
                .select("*")\
                .eq("student_id", student_id)\
                .eq("topic_name", topic["topic"])\
                .execute()

            if existing.data:
                supabase.table("weak_topics")\
                    .update({"frequency":
                        existing.data[0]["frequency"] + 1})\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
            else:
                supabase.table("weak_topics").insert({
                    "student_id": student_id,
                    "topic_name": topic["topic"],
                    "subject":    topic.get("subject", "General"),
                    "frequency":  1
                }).execute()

    except Exception as e:
        pass  # Silent fail — UX break nahi hogi

def extract_pdf_text(pdf_file):
    """PDF se text extract karo"""
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def get_yt_transcript(url):
    """YouTube transcript extract karo"""
    video_id_match = re.search(
        r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    if not video_id_match:
        return None, "Invalid YouTube URL"
    video_id = video_id_match.group(1)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=['en', 'hi'])
        text = " ".join([t['text'] for t in transcript])
        return text, None
    except Exception as e:
        return None, f"Transcript nahi mila: {str(e)}"

def get_announcements(supabase, student_id):
    """Student ki class ki announcements"""
    try:
        # Student ki class dhundo
        sc = supabase.table("student_classes")\
            .select("class_id")\
            .eq("student_id", student_id)\
            .execute()
        if not sc.data:
            return []
        class_ids = [s["class_id"] for s in sc.data]
        # Announcements fetch karo
        ann = supabase.table("announcements")\
            .select("*, users(name)")\
            .in_("class_id", class_ids)\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        return ann.data if ann.data else []
    except:
        return []

def get_teacher_notes(supabase, student_id):
    """Teacher uploaded notes fetch karo"""
    try:
        sc = supabase.table("student_classes")\
            .select("class_id")\
            .eq("student_id", student_id)\
            .execute()
        if not sc.data:
            return []
        class_ids = [s["class_id"] for s in sc.data]
        notes = supabase.table("notes")\
            .select("*")\
            .in_("class_id", class_ids)\
            .order("created_at", desc=True)\
            .execute()
        return notes.data if notes.data else []
    except:
        return []

# ── Main Student Page ─────────────────────────────────────────

def show_student(supabase, model):
    student    = st.session_state.user
    student_id = student["id"]

    # Load history once
    if not st.session_state.chat_history:
        history = get_chat_history(supabase, student_id)
        st.session_state.chat_history = history

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#667eea,#764ba2);
    padding:1.5rem;border-radius:12px;color:white;margin-bottom:1rem'>
        <h2>👋 Welcome, {student['name']}!</h2>
        <p>Kya seekhna hai aaj?</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Announcements ─────────────────────────────────────────
    announcements = get_announcements(supabase, student_id)
    if announcements:
        with st.expander("📢 Announcements", expanded=True):
            for ann in announcements:
                st.info(f"**{ann['title']}** — {ann['content']}")

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 AI Chatbot",
        "📄 PDF Notes",
        "🎥 YouTube Notes",
        "📚 Teacher Notes"
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1 — AI CHATBOT
    # ════════════════════════════════════════════════════════
    with tab1:
        st.subheader("EduBot — Tera AI Teacher 🤖")

        # Chat display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                role = msg["role"]
                with st.chat_message(role):
                    st.write(msg["message"])

        # Input
        user_input = st.chat_input(
            "Apna doubt poochho... koi bhi topic! 😊")

        if user_input:
            # User message save + display
            save_message(
                supabase, student_id, "user", user_input)
            st.session_state.chat_history.append({
                "role": "user", "message": user_input})

            with st.chat_message("user"):
                st.write(user_input)

            # AI response
            with st.chat_message("assistant"):
                with st.spinner("Soch raha hoon... 🤔"):

                    # History context build karo
                    history_context = "\n".join([
                        f"{m['role'].upper()}: {m['message']}"
                        for m in
                        st.session_state.chat_history[-20:]
                    ])

                    system_prompt = f"""
Tu EduBot hai — ek friendly, encouraging AI teacher.
Tujhe students ke doubts clear karne hain simple
language mein (Hinglish ya English — student jo use
kare).

Rules:
- Galti pe kabhi judge mat kar — encourage kar
- Simple examples de
- Agar concept samajh nahi aya toh alag tarike se explain
- Student ki progress celebrate kar
- Short aur clear reh — 3-4 lines max per point

Previous conversation context:
{history_context}

Student ka naya sawaal: {user_input}
"""
                    response = model.generate_content(
                        system_prompt)
                    ai_reply = response.text

                    st.write(ai_reply)

                    # Save AI response
                    save_message(
                        supabase, student_id,
                        "assistant", ai_reply)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "message": ai_reply
                    })

            # Weak topics extract (har 6 messages pe)
            if len(st.session_state.chat_history) % 6 == 0:
                extract_weak_topics(
                    supabase, model,
                    student_id,
                    st.session_state.chat_history
                )

    # ════════════════════════════════════════════════════════
    # TAB 2 — PDF NOTES
    # ════════════════════════════════════════════════════════
    with tab2:
        st.subheader("📄 PDF Upload — AI Summary + Q&A")

        pdf_file = st.file_uploader(
            "PDF upload karo", type=["pdf"])

        if pdf_file:
            pdf_text = extract_pdf_text(pdf_file)

            if "pdf_text" not in st.session_state:
                st.session_state.pdf_text = ""
            st.session_state.pdf_text = pdf_text

            # Auto summary
            if st.button("📝 AI Summary Generate Karo"):
                with st.spinner("Padh raha hoon... 📖"):
                    summary_prompt = f"""
                    Yeh PDF content ka clear, structured
                    summary banao:
                    - Key points bullet mein
                    - Simple language
                    - Important terms bold karo

                    Content: {pdf_text[:4000]}
                    """
                    summary = model.generate_content(
                        summary_prompt)
                    st.markdown(summary.text)

                    # Notes table mein save karo
                    supabase.table("notes").insert({
                        "uploaded_by": student_id,
                        "file_name":   pdf_file.name,
                        "file_url":    "student_upload",
                        "ai_summary":  summary.text
                    }).execute()
                    st.success("Summary saved ✅")

            # PDF pe Q&A
            st.divider()
            st.write("**PDF se koi bhi question poochho:**")
            pdf_question = st.text_input(
                "Question", key="pdf_q")

            if pdf_question and st.button("Answer Do"):
                with st.spinner("Dhundh raha hoon... 🔍"):
                    qa_prompt = f"""
                    Sirf is PDF content ke basis pe
                    answer do. Agar answer nahi hai
                    toh clearly bolo.

                    PDF Content: {pdf_text[:4000]}
                    Question: {pdf_question}
                    """
                    ans = model.generate_content(qa_prompt)
                    st.info(ans.text)

    # ════════════════════════════════════════════════════════
    # TAB 3 — YOUTUBE NOTES
    # ════════════════════════════════════════════════════════
    # Tab 3 — YOUTUBE NOTES (Gemini Native)
with tab3:
    st.subheader("🎥 YouTube Lecture → Notes")

    yt_url = st.text_input("YouTube URL paste karo")

    if yt_url and st.button("Notes Banao 📝"):
        with st.spinner("Lecture dekh raha hoon... 🎧"):
            try:
                # Gemini 2.5 Flash — native YT support
                yt_model = genai.GenerativeModel(
                    'gemini-2.5-flash')

                response = yt_model.generate_content([
                    {
                        "file_data": {
                            "file_uri": yt_url
                        }
                    },
                    """Is YouTube lecture ka structured
                    notes banao Hindi/English mein:

                    ## Main Topics
                    ## Key Concepts  
                    ## Important Points
                    ## Quick Summary

                    Simple aur clear rakho."""
                ])

                notes_text = response.text
                st.markdown(notes_text)

                # Session mein save karo Q&A ke liye
                st.session_state.yt_notes = notes_text
                st.session_state.yt_url   = yt_url

                # Supabase mein save
                supabase.table("notes").insert({
                    "uploaded_by": student_id,
                    "file_name":   f"YT: {yt_url}",
                    "file_url":    yt_url,
                    "ai_summary":  notes_text
                }).execute()
                st.success("Notes saved ✅")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    # YT Notes pe Q&A
    if st.session_state.get("yt_notes"):
        st.divider()
        st.write("**Lecture se question poochho:**")
        yt_q = st.text_input(
            "Question likho", key="yt_question")

        if yt_q and st.button("Answer Do", key="yt_ans"):
            with st.spinner("Soch raha hoon..."):
                try:
                    yt_model = genai.GenerativeModel(
                        'gemini-2.5-flash')

                    ans = yt_model.generate_content([
                        {
                            "file_data": {
                                "file_uri":
                                st.session_state.yt_url
                            }
                        },
                        f"Sirf is video ke basis pe "
                        f"answer do: {yt_q}"
                    ])
                    st.info(ans.text)

                except Exception as e:
                    st.error(f"Error: {str(e)}")
    # ════════════════════════════════════════════════════════
    # TAB 4 — TEACHER NOTES
    # ════════════════════════════════════════════════════════
    with tab4:
        st.subheader("📚 Teacher ke Notes")

        teacher_notes = get_teacher_notes(
            supabase, student_id)

        if not teacher_notes:
            st.info(
                "Abhi koi notes nahi hain — "
                "teacher upload karenge toh yahan dikhenge")
        else:
            for note in teacher_notes:
                with st.expander(
                    f"📄 {note['file_name']}"):

                    if note.get("ai_summary"):
                        st.markdown(note["ai_summary"])

                    # Notes pe question
                    q = st.text_input(
                        "Is note se question poochho",
                        key=f"note_q_{note['id']}")
                    if q and st.button(
                        "Answer", key=f"note_btn_{note['id']}"):
                        ans = model.generate_content(
                            f"Notes: {note['ai_summary']}"
                            f"\nQuestion: {q}")
                        st.info(ans.text)