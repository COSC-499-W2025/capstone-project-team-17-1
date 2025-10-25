# Shuyu Yan– Project Log  46070686

## Week3 Personal Log [Sept 15 – Sept 21, 2025]
## Table of Contents
- [Week 3 Personal Log](#week-3-personal-log-sep-15-21-2025)

### 1. Type of Tasks Worked On

<img width="1047" height="598" alt="Screenshot 2025-09-20 at 4 50 39 PM" src="https://github.com/user-attachments/assets/0914c3cc-61b8-4ad5-b780-70656426e655" />


### 2. Weekly Goals Recap
- Worked on Project Requirements Documentation  
- Worked on Functional Requirements Part  
- Worked on Success Criteria Part  
- Edited document tabs and corrected grammar mistakes  

## WEEK 4 Personal LOG (SEP 22 - 28, 2025)

### 1. Type of Tasks Worked On

<img width="1061" height="605" alt="Screenshot 2025-09-27 at 4 27 43 PM" src="https://github.com/user-attachments/assets/1f5ebd75-d371-4324-989b-9ff1f1338819" />

### 2. Weekly Goals Recap
- Worked on Project Proposal
- Worked on Project Proposal requirement table
- Worked on System Architecture Design
- Worked on System Components in System Architecture Design
- Build the Kanban and complete kanban Automation
- Create tasks and assgin tasks to members
- Reviewed Nade's pull requests.
- Worked on Team log Week4

### Completed Tasks Week 4

[Architecture Design Diagram](https://docs.google.com/document/d/1fZNTCu4YO0CFwIvErlJ1agD4Zyxgh6q11CnjB686NzY/edit?usp=sharing)
[Project Proposal](https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/main/docs/Plan/Project%20Porposal.md)


## WEEK 5 Personal LOG (SEP 29 - Oct5, 2025)

### 1. Type of Tasks Worked On
<img width="1059" height="606" alt="Screenshot 2025-10-04 at 2 08 15 PM" src="https://github.com/user-attachments/assets/6d757bcb-51d6-4447-afe3-2b5b4ee07d23" />

### 2. Weekly Goals Recap
- discussed the basic construction of the app with team and completed the Level 0 and Level 1 DFD.
- Asssgin members to their tasks

This week, our team worked together to discuss the basic construction and overall design of the Data Mining App. We mainly focused on how the data flows between the user, system modules, and external APIs, and made sure everyone understood the boundaries and responsibilities of each part. Through the discussion, we reached a clear and shared understanding of how user input, data mining, analysis, and output generation will connect in the system.

During this process, we also completed both the Level 0 and Level 1 Data Flow Diagrams (DFDs) to better visualize how the system works.

The Level 0 DFD gives a simple, high-level view of the system. It shows how the User interacts with the Data Mining App and the System API, focusing on the main data exchanges like authentication, data mining requests, and output generation.

The Level 1 DFD goes deeper into the system’s internal logic. It breaks down the app into smaller processes such as Source Selection, Mining/Scan, Analytics & Metrics Generation, Visualization & Export, and Save Portfolio. It also includes data stores like the Artifact Database and Portfolio Database, showing how information is saved and used. Feedback loops such as Error Logs and Export Logs are also included to keep track of system performance and ensure accuracy.

These diagrams helped us clearly see how different parts of the app connect and will serve as a guide for the next development steps.

### Completed Tasks Week 5
[Data Flow Diagram](https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/main/docs/design/L0%26L1%20DFD.png)

## WEEK 6 Personal LOG (Oct6 - Oct12, 2025)

### 1. Type of Tasks Worked On
<img width="1068" height="596" alt="Screenshot 2025-10-11 at 11 50 36 AM" src="https://github.com/user-attachments/assets/919f3757-317a-4048-a17e-059427f3ccbd" />

### 2. Weekly Goals Recap
- complete 'Return an error if the specified file is in the wrong format' task #19
- discussed the set-up with members in meeting
- revise the README file
- Asssgin members to their tasks

During this week, I focused on improving the system’s reliability and completing the task “Return an error if the specified file is in the wrong format.” The parser now automatically detects non-ZIP inputs, returns a clear JSON error message, and logs each event to logs/error.log before safely stopping the process. This change makes the system more robust and user-friendly, ensuring that incorrect inputs are handled gracefully rather than breaking the workflow.

I also worked with the team to finalize our local environment setup, confirming that the app runs through an Electron shell, with a Node.js backend and a Docker-based database. I learned how these components connect together in a full-stack environment, especially how Docker provides consistency across different machines. After our setup meeting, I helped revise the README file to make it easier for teammates to run the project, adding clearer setup instructions, a quick-start guide, and troubleshooting notes.

Beyond coding, I contributed to planning discussions by reviewing our current Work Breakdown Structure and ensuring that all tasks and acceptance criteria align with the milestone requirements. We assigned ownership for each module to streamline collaboration and reduce overlap.

From this week’s work, I learned how to design defensive error-handling logic, use structured logging for debugging, and maintain documentation that supports a smooth developer experience. It also gave me a better sense of how planning, environment setup, and communication tie together to keep a project organized and moving forward.
### Completed Tasks Week 6
[All Diagram](https://docs.google.com/document/d/1ZnNXTiLX3bXALCe2Ug8rojZ3RkSmjPB-2_YgaCqQyPA/edit?tab=t.0)
[Project Proposal](https://docs.google.com/document/d/1yNkyeBqHvSgFAER2WQUW5GLdEmcIMknSAGh68UDHqCg/edit?tab=t.0)
[WBS](https://docs.google.com/document/d/1wPQgS1NMM9Jt1JUTCCPeJgyASQXQxxf_LkWZkoiAauA/edit?tab=t.0)
Return an error if the specified file is in the wrong format--task #19

## WEEK 7 Personal LOG (Oct13 - Oct19, 2025)
### 1. Type of Tasks Worked On
<img width="1064" height="558" alt="Screenshot 2025-10-18 at 1 34 14 PM" src="https://github.com/user-attachments/assets/a33a015c-4228-41b3-8ba1-063985706019" />

### 2. Weekly Goals Recap
- complete 'Distinguish Individual Projects from Collaborative Projects' task #38
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them
- upload the README file to canvas

During this week, I completed the task “Distinguish Individual Projects from Collaborative Projects” (#38) by analyzing contribution metadata and Git history patterns to classify repositories based on the number of unique contributors and commit ownership distribution. This enhanced our system’s ability to organize project data more meaningfully for users and supports future features like contribution analysis. I also discussed technical design details with team members to ensure the task aligned with our overall architecture and data pipeline.

In addition to development work, I helped organize the team by assigning tasks to members and creating new tasks for upcoming work. I also reviewed teammates’ pull requests, provided feedback to maintain code quality, and helped resolve issues to prevent conflicts during merging. Finally, I uploaded the updated README file to Canvas, ensuring it reflected our current project structure and setup instructions for both instructors and team members.

This week strengthened my understanding of team coordination in a collaborative software project. I learned how to design logic that handles multiple project types, manage task planning in a structured way, and support team progress through effective code reviews and communication.
### Completed Tasks Week 7
'Distinguish Individual Projects from Collaborative Projects' task #38

## WEEK 8 Personal LOG (Oct20 - Oct26, 2025)
### 1. Type of Tasks Worked On

### 2. Weekly Goals Recap
- complete 'Collaboration Analysis Module' task #42
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them

This week I completed the Collaboration Analysis Module (task #42), which is responsible for analyzing team contribution patterns in a project. To implement this, I parsed git log --numstat output to extract meaningful contribution metrics like commit count, lines added/removed, and review involvement. I also added logic to distinguish between real contributors, shared accounts, and bots, since many Git histories include dependabot or team accounts that can distort results. The module now stores contribution summaries in our database so they can be reused later for analytics and user portfolio generation.

After finishing the backend logic, I connected it to our application by updating the Electron IPC layer and preload bridge, and I built the frontend components to display collaboration summaries, contributor leaderboards, and export options (JSON/CSV). I also added refresh and export handlers in the UI. During development, I ran into compatibility issues with better-sqlite3 when running tests inside Electron, so I added an electron-rebuild script to solve native module loading problems.

Besides coding, I also helped organize the team by assigning some new tasks for the next phase and reviewing teammates’ pull requests. I discussed implementation details with others to make sure this module fits our data pipeline design and that future visualization features can build on top of it smoothly.

Overall, this week helped me improve both system design thinking and team coordination skills.
  
### Completed Tasks Week 7
'Collaboration Analysis Module' task #42
