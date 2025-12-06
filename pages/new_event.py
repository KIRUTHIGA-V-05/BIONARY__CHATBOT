import streamlit as st
import frontend as FE

st.title("Add New Event")

with st.form("event_form"):
    name_of_event = st.text_input("Title (saved as name_of_event if blank)", "").strip() or None
    event_domain = st.text_input("Domain (e.g., Workshops, Seminar, Competition)")
    description_insights = st.text_area("Description (used for semantic embedding)")
    date_of_event = st.date_input("Date of Event")
    time_of_event = st.text_input("Time (optional)", "N/A")
    venue = st.text_input("Venue (or 'Online')")
    mode_of_event = st.selectbox("Mode", ["Online", "Offline"])
    registration_fee = st.text_input("Registration fee (0 if free)", "0")
    speakers = st.text_input("Speakers (comma separated, optional)", "N/A")
    perks = st.text_input("Perks (comma separated, optional)", "N/A")
    faculty_coordinators = st.text_input("Faculty coordinators (optional)", "N/A")
    student_coordinators = st.text_input("Student coordinators (optional)", "N/A")

    submit = st.form_submit_button("Submit Event")

if submit:
    form_data = {
        "name_of_event": name_of_event,
        "event_domain": event_domain,
        "description_insights": description_insights,
        "date_of_event": str(date_of_event),
        "time_of_event": time_of_event,
        "venue": venue,
        "mode_of_event": mode_of_event,
        "registration_fee": registration_fee,
        "speakers": speakers,
        "perks": perks,
        "faculty_coordinators": faculty_coordinators,
        "student_coordinators": student_coordinators
    }

    status = st.info("Submitting event...")

    result = FE.ingest_event(form_data)

    status.empty()

    if isinstance(result, tuple) and result[0] is True:
        st.success("Event added successfully! ")
    else:
        st.error("Ingestion failed ")
