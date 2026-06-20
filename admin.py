# pages/admin.py
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
import uuid

# ── Helper Functions ──────────────────────────────────────────

def get_all_users(supabase, role):
    res = supabase.table("users")\
        .select("*")\
        .eq("role", role)\
        .execute()
    return res.data if res.data else []

def get_all_classes(supabase):
    res = supabase.table("classes")\
        .select("*, users(name)")\
        .execute()
    return res.data if res.data else []

def create_class(supabase, class_name, teacher_id):
    join_code = str(uuid.uuid4())[:6].upper()
    supabase.table("classes").insert({
        "class_name": class_name,
        "teacher_id": teacher_id,
        "join_code":  join_code
    }).execute()
    return join_code

def assign_student(supabase, student_id, class_id):
    # Already assigned check
    existing = supabase.table("student_classes")\
        .select("*")\
        .eq("student_id", student_id)\
        .eq("class_id", class_id)\
        .execute()
    if existing.data:
        return False, "Already assigned"
    supabase.table("student_classes").insert({
        "student_id": student_id,
        "class_id":   class_id
    }).execute()
    return True, "Assigned"

def delete_user(supabase, user_id):
    supabase.table("users")\
        .delete()\
        .eq("id", user_id)\
        .execute()

def create_user(supabase, name, email, password, role):
    try:
        supabase.table("users").insert({
            "name":     name,
            "email":    email,
            "password": password,
            "role":     role
        }).execute()
        return True, "User created"
    except:
        return False, "Email already exists"

# ── Main Admin Page ───────────────────────────────────────────

def show_admin(supabase):
    st.markdown("""
    <div style='background:linear-gradient(
        135deg,#f093fb,#f5576c);
        padding:1.5rem;border-radius:12px;
        color:white;margin-bottom:1rem'>
        <h2>⚙️ Admin Panel</h2>
        <p>Full system control</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Overview Metrics ──────────────────────────────────────
    students = get_all_users(supabase, "student")
    teachers = get_all_users(supabase, "teacher")
    classes  = get_all_classes(supabase)

    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍🎓 Total Students", len(students))
    col2.metric("👨‍🏫 Total Teachers", len(teachers))
    col3.metric("🏫 Total Classes",  len(classes))

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏫 Class Management",
        "👤 User Management",
        "📊 System Overview",
        "➕ Create Users"
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1 — CLASS MANAGEMENT
    # ════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Class Banao + Students Assign Karo")

        # ── Create Class ──────────────────────────────────
        with st.expander("➕ Nayi Class Banao", expanded=True):
            class_name = st.text_input("Class Name")

            teacher_options = {
                t["name"]: t["id"] for t in teachers}

            if teacher_options:
                sel_teacher = st.selectbox(
                    "Teacher Assign Karo",
                    list(teacher_options.keys()))
                teacher_id = teacher_options[sel_teacher]

                if st.button("Class Banao 🏫"):
                    if class_name:
                        code = create_class(
                            supabase,
                            class_name,
                            teacher_id)
                        st.success(
                            f"Class bani ✅ | "
                            f"Join Code: **{code}**")
                        st.rerun()
                    else:
                        st.warning("Class name do")
            else:
                st.warning(
                    "Pehle teacher create karo")

        # ── Assign Students ───────────────────────────────
        with st.expander("👨‍🎓 Student → Class Assign Karo"):
            if not classes:
                st.info("Pehle class banao")
            else:
                class_options = {
                    c["class_name"]: c["id"]
                    for c in classes}
                student_options = {
                    s["name"]: s["id"]
                    for s in students}

                sel_class = st.selectbox(
                    "Class", list(class_options.keys()),
                    key="assign_class")
                sel_student = st.selectbox(
                    "Student", list(student_options.keys()),
                    key="assign_student")

                if st.button("Assign Karo ✅"):
                    ok, msg = assign_student(
                        supabase,
                        student_options[sel_student],
                        class_options[sel_class])
                    if ok:
                        st.success(
                            f"{sel_student} → "
                            f"{sel_class} assigned ✅")
                    else:
                        st.warning(msg)

        # ── Class Overview ────────────────────────────────
        st.subheader("All Classes")
        if classes:
            for c in classes:
                teacher_name = c.get("users", {})
                if isinstance(teacher_name, dict):
                    teacher_name = teacher_name.get(
                        "name", "Unknown")

                with st.expander(
                    f"🏫 {c['class_name']} — "
                    f"Teacher: {teacher_name}"):

                    # Students in class
                    enrolled = supabase\
                        .table("student_classes")\
                        .select("*, users(name, email)")\
                        .eq("class_id", c["id"])\
                        .execute()

                    if enrolled.data:
                        st.write(
                            f"**{len(enrolled.data)}"
                            f" Students enrolled:**")
                        for e in enrolled.data:
                            if e.get("users"):
                                col1, col2 = st.columns(
                                    [3, 1])
                                col1.write(
                                    f"• {e['users']['name']}"
                                    f" ({e['users']['email']})")
                                if col2.button(
                                    "Remove",
                                    key=f"rem_{e['id']}"):
                                    supabase\
                                        .table("student_classes")\
                                        .delete()\
                                        .eq("id", e["id"])\
                                        .execute()
                                    st.rerun()
                    else:
                        st.info("Koi student enrolled nahi")

                    # Delete class
                    if st.button(
                        "🗑️ Class Delete Karo",
                        key=f"del_class_{c['id']}"):
                        supabase.table("classes")\
                            .delete()\
                            .eq("id", c["id"])\
                            .execute()
                        st.rerun()
        else:
            st.info("Koi class nahi hai abhi")

    # ════════════════════════════════════════════════════════
    # TAB 2 — USER MANAGEMENT
    # ════════════════════════════════════════════════════════
    with tab2:
        st.subheader("User Management")

        role_filter = st.radio(
            "Role filter karo",
            ["student", "teacher"],
            horizontal=True)

        users = get_all_users(supabase, role_filter)

        if users:
            for u in users:
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{u['name']}**")
                col2.write(u["email"])
                if col3.button(
                    "🗑️ Delete",
                    key=f"del_{u['id']}"):
                    delete_user(supabase, u["id"])
                    st.success(f"{u['name']} deleted")
                    st.rerun()
        else:
            st.info(f"Koi {role_filter} nahi hai")

    # ════════════════════════════════════════════════════════
    # TAB 3 — SYSTEM OVERVIEW
    # ════════════════════════════════════════════════════════
    with tab3:
        st.subheader("System Overview")

        # Weak topics system wide
        all_student_ids = [s["id"] for s in students]

        if all_student_ids:
            weak = supabase.table("weak_topics")\
                .select("*")\
                .in_("student_id", all_student_ids)\
                .execute()

            if weak.data:
                df = pd.DataFrame(weak.data)

                # Top weak topics
                topic_freq = df.groupby(
                    "topic_name")["frequency"]\
                    .sum().reset_index()
                topic_freq.columns = ["Topic", "Count"]
                topic_freq = topic_freq\
                    .sort_values("Count", ascending=False)\
                    .head(10)

                fig = px.bar(
                    topic_freq,
                    x="Topic",
                    y="Count",
                    title="System-wide Top Weak Topics",
                    color="Count",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(
                    fig, use_container_width=True)

                # Subject distribution
                if "subject" in df.columns:
                    subj = df.groupby(
                        "subject").size().reset_index()
                    subj.columns = ["Subject", "Count"]
                    fig2 = px.pie(
                        subj,
                        values="Count",
                        names="Subject",
                        title="Subject wise Distribution"
                    )
                    st.plotly_chart(
                        fig2, use_container_width=True)
            else:
                st.info("Abhi koi weak topics nahi hain")

        # Conversation stats
        conv = supabase.table("conversations")\
            .select("student_id")\
            .execute()
        if conv.data:
            st.metric(
                "Total Conversations",
                len(conv.data))

    # ════════════════════════════════════════════════════════
    # TAB 4 — CREATE USERS
    # ════════════════════════════════════════════════════════
    with tab4:
        st.subheader("➕ Naya User Create Karo")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Student Create Karo**")
            s_name  = st.text_input(
                "Name", key="s_name")
            s_email = st.text_input(
                "Email", key="s_email")
            s_pwd   = st.text_input(
                "Password",
                type="password", key="s_pwd")

            if st.button(
                "Student Banao 👨‍🎓",
                use_container_width=True):
                if s_name and s_email and s_pwd:
                    ok, msg = create_user(
                        supabase, s_name,
                        s_email, s_pwd, "student")
                    if ok:
                        st.success(f"{msg} ✅")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Sab fields bharo")

        with col2:
            st.write("**Teacher Create Karo**")
            t_name  = st.text_input(
                "Name", key="t_name")
            t_email = st.text_input(
                "Email", key="t_email")
            t_pwd   = st.text_input(
                "Password",
                type="password", key="t_pwd")

            if st.button(
                "Teacher Banao 👨‍🏫",
                use_container_width=True):
                if t_name and t_email and t_pwd:
                    ok, msg = create_user(
                        supabase, t_name,
                        t_email, t_pwd, "teacher")
                    if ok:
                        st.success(f"{msg} ✅")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Sab fields bharo")