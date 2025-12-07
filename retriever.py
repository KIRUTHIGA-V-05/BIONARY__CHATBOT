def add_new_event(form_data):
    conn = _connect_to_db()
    if not conn:
        return False, "Database connection error."

    try:
        desc = (form_data.get("description_insights", "") or "").strip()
        perks = (form_data.get("perks", "") or "").strip()

        search_text = (
            f"Event: {form_data.get('name_of_event', '')}\n"
            f"Domain: {form_data.get('event_domain', '')}\n"
            f"Details: {desc}\n"
            f"Perks: {perks}"
        )

        emb = model.encode(search_text)
        if isinstance(emb, np.ndarray):
            emb = emb.tolist()

        parms = (
            form_data.get("name_of_event"),
            0,
            form_data.get("name_of_event"),
            form_data.get("event_domain"),
            form_data.get("date_of_event"),
            form_data.get("time_of_event", "N/A"),
            form_data.get("faculty_coordinators", "N/A"),
            form_data.get("student_coordinators", "N/A"),
            form_data.get("venue", "N/A"),
            form_data.get("mode_of_event", "N/A"),
            form_data.get("registration_fee", "0"),
            form_data.get("speakers", "N/A"),
            form_data.get("perks", "N/A"),
            desc,
            search_text,
            emb,
        )

        with conn.cursor() as cur:
            register_vector(cur)
            cur.execute(
                """
                INSERT INTO events (
                    event_id, serial_no, name_of_event, event_domain,
                    date_of_event, time_of_event, faculty_coordinators,
                    student_coordinators, venue, mode_of_event,
                    registration_fee, speakers, perks,
                    description_insights, search_text, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                parms,
            )

        conn.commit()
        conn.close()
        return True, "Event added successfully."

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)
