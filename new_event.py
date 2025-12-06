# pages/new_event.py
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
        name_of_event = st.text_input("Event ID / Name (optional — leave blank to auto-generate)", max_chars=150)
        title_display = st.text_input("Title (will be saved as name_of_event if left blank)", max_chars=300)
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
        if (not description_insights) or (not (name_of_event or title_display)):
            st.error("Please provide at least a title (or event id) and a description.")
        else:
            st.session_state.submitting = True
            try:
                final_name = (name_of_event.strip() or title_display.strip() or f"event_{uuid.uuid4().hex[:8]}")
                final_name = final_name.replace(" ", "_")[:150]

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

                st.info("Submitting event... (this may take a few seconds if the model is loading)")

                if add_new_event is None:
                    st.error("Ingestion function not available. Ensure 'frontend.py' exists and defines add_new_event(form_data).")
                else:
                    with st.spinner("Processing and saving event..."):
                        try:
                            result = add_new_event(form_data)
                        except Exception as e:
                            result = {"status": "error", "message": f"Ingestion function raised: {e}"}

                    if isinstance(result, dict):
                        status = result.get("status")
                        message = result.get("message", "")
                        event_id = result.get("event_id")
                        if status == "success":
                            st.success(f"Event saved and indexed: {event_id or final_name}")
                            st.write("Event ID:", event_id or final_name)
                            st.write("Submitted data preview:")
                            st.json(form_data)
                        elif status == "busy":
                            st.warning("Server busy. Try again in a few seconds.")
                            st.write(message)
                        elif status == "error":
                            st.error("Ingestion failed.")
                            st.write(message)
                        else:
                            st.error("Unexpected response from ingestion function.")
                            st.write(result)
                    else:
                        if isinstance(result, str) and result.lower().startswith("success"):
                            st.success(f"Event saved and indexed: {final_name}")
                            st.write("Event ID:", final_name)
                            st.write("Submitted data preview:")
                            st.json(form_data)
                        else:
                            st.error("Ingestion failed.")
                            st.write(result)
            except Exception:
                st.error("An unexpected error occurred while submitting. See logs for details.")
                st.text(traceback.format_exc())
            finally:
                st.session_state.submitting = False
