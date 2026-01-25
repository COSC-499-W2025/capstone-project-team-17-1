from capstone.ai_insights import ask_project_question

answer = ask_project_question(
    project_id="demo",
    question="What are the strengths of this project and what could be improved?"
)

print(answer)
