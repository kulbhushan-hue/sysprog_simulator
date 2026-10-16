# z/OS Sysprog Lab (Streamlit)

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Deploy: push this folder to GitHub and create a Streamlit Community Cloud app with `app.py` as the entry point
(or run on any server with `streamlit run app.py --server.port 8501`).

Files: app.py (UI) | simulator.py (command engine) | course_data.py (lessons, roadmap, quiz) | concept_search.py (TF-IDF search)
To add a command: add a regex branch in `simulator.execute`. To add a lesson: add a dict in `course_data.MODULES`.
