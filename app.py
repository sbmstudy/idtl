import streamlit as st
from supabase import create_client
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEAL — Smart Educational Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Clients ───────────────────────────────────────────────────
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

@st.cache_resource
def init_gemini():
    genai.configure(
        api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel('gemini-2.5-flash')

supabase = init_supabase()
model    = init_gemini()

# ── Session State ─────────────────────────────────────────────
for key, val in {
    "user":         None,
    "role":         None,
    "chat_history": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(
            135deg, #667eea, #764ba2);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Auth Functions ────────────────────────────────────────────
def login(email, password, role):
    try:
        res = supabase.table("users")\
            .select("*")\
            .eq("email",    email)\
            .eq("password", password)\
            .eq("role",     role)\
            .single()\
            .execute()
        if res.data:
            st.session_state.user = res.data
            st.session_state.role = role
            return True, "Login successful"
        return False, "Invalid credentials"
    except Exception as e:
        return False, "Invalid credentials"

def signup(name, email, password, role):
    try:
        supabase.table("users").insert({
            "name":     name,
            "email":    email,
            "password": password,
            "role":     role
        }).execute()
        return True, "Account created"
    except:
        return False, "Email already exists"

def logout():
    st.session_state.user         = None
    st.session_state.role         = None
    st.session_state.chat_history = []
    st.rerun()

# ── Login Page ────────────────────────────────────────────────
def show_login():
    st.markdown("""
    <div class='main-header'>
        <h1>🎓 SEAL</h1>
        <p>Smart Educational Assistant for Learning</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            role  = st.selectbox(
                "Role",
                ["student", "teacher", "admin"])
            email = st.text_input(
                "Email", key="login_email")
            pwd   = st.text_input(
                "Password",
                type="password", key="login_pwd")

            if st.button(
                "Login",
                use_container_width=True):
                if email and pwd:
                    ok, msg = login(email, pwd, role)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Sab fields bharo")

        with tab2:
            name  = st.text_input(
                "Full Name", key="su_name")
            role  = st.selectbox(
                "Role ",
                ["student", "teacher"])
            email = st.text_input(
                "Email", key="su_email")
            pwd   = st.text_input(
                "Password",
                type="password", key="su_pwd")

            if st.button(
                "Sign Up",
                use_container_width=True):
                if name and email and pwd:
                    ok, msg = signup(
                        name, email, pwd, role)
                    if ok:
                        st.success(
                            f"{msg} — ab login karo")
                    else:
                        st.error(msg)
                else:
                    st.warning("Sab fields bharo")

# ── Router ────────────────────────────────────────────────────
if not st.session_state.user:
    show_login()
else:
    role = st.session_state.role

    with st.sidebar:
        st.write(
            f"👤 {st.session_state.user['name']}")
        st.write(f"🏷️ {role.capitalize()}")
        st.divider()
        if st.button("Logout 🚪"):
            logout()

    if role == "student":
        from student import show_student
        show_student(supabase, model)
    elif role == "teacher":
        from teacher import show_teacher
        show_teacher(supabase, model)
    elif role == "admin":
        from admin import show_admin
        show_admin(supabase)