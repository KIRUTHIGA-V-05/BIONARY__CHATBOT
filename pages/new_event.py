import streamlit as st
import uuid
import traceback
from datetime import date, time

try:
    from frontend import add_new_event
except Exception:
    add_new_event = None

st.set_page_config(page_title="New Event", layout="wide")
st.title("Add New Event")
st.markdown("Fill the form below and click Submit. The event will be saved to Neon and indexed (embedding computed).")

if "submitting" not in st.session_state:
    st.session_state.submitting = False

with st.form("event_form", clear_on_submit=False):
    col1, col2 = st.columns([2, 1])

    with col1:
        title_display = st.text_input("Event Title", max_chars=300)
        event_domain = st.text_input("Domain (e.g., Workshops, Seminar, Competition)", max_chars=150)
        description_insights = st.text_area("Description (used for semantic embedding)", height=200, max_chars=50000)
        perks = st.text_input("Perks (comma separated, optional)", max_chars=500)

    with col2:
        date_of_event = st.date_input("Date (required)", value=date.today())
        time_of_event = st.time_input("Time (optional)", value=None)
        venue = st.text_input("Venue (or 'Online')", max_chars=200)
        mode_of_event = st.selectbox("Mode", ["Online", "Offline", "Hybrid", "Other"])
        if mode_of_event == "Other":
            mode_of_event = st.text_input("Specify mode", max_chars=100)
        registration_fee = st.text_input("Registration fee (0 if free)", value="0")
        speakers = st.text_input("Speakers (comma separated, optional)", max_chars=500)
        faculty_coordinators = st.text_input("Faculty coordinators (optional)", max_chars=300)
        student_coordinators = st.text_input("Student coordinators (optional)", max_chars=300)

    submit = st.form_submit_button("Submit Event")

def format_time(t):
    if t is None:
        return "N/A"
    try:
        return t.strftime("%I:%M %p")
    except Exception:
        return str(t)

if submit:
    if st.session_state.submitting:
        st.warning("Submission already in progress. Wait a moment.")
    else:
        if not title_display or not description_insights:
            st.error("Please provide event title and description.")
        else:
            st.session_state.submitting = True
            try:
                final_name = title_display.strip().replace(" ", "_")[:150]
                date_str = date_of_event.strftime("%Y-%m-%d")
                time_str = format_time(time_of_event)

                form_data = {
                    "name_of_event": final_name,
                    "event_domain": event_domain.strip(),
                    "date_of_event": date_str,
                    "time_of_event": time_str,
                    "faculty_coordinators": faculty_coordinators.strip() or None,
                    "student_coordinators": student_coordinators.strip() or None,
                    "venue": venue.strip() or None,
                    "mode_of_event": mode_of_event or None,
                    "registration_fee": registration_fee.strip() or "0",
                    "speakers": speakers.strip() or None,
                    "perks": perks.strip() or None,
                    "description_insights": description_insights.strip(),
                }

                st.info("Submitting event...")

                with st.spinner("Processing and saving event..."):
                    result = add_new_event(form_data)

                if isinstance(result, tuple) and result[0] is True:
                    st.success("Event added successfully.")
                else:
                    st.error("Ingestion failed.")
            except Exception:
                st.error("Unexpected error occurred.")
                st.text(traceback.format_exc())
            finally:
                st.session_state.submitting = False
