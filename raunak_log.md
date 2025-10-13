# COSC 499 TEAM 17 Personal Log - Raunak Khanna

## Table of Contents
- [Week 3 Personal Log](#week-3-personal-log)
- [Week 4 Personal Log](#week-4-personal-log)
- [Week 5 Personal Log](#week-5-personal-log)
- [Week 6 Personal Log](#week-6-personal-log)

---

### WEEK 3 PERSONAL LOG
(Sep 15–21, 2025)
- Drafted **User Requirements (UR-01 to UR-08)** focusing on usability, privacy, insights, and accessibility.  
- Co-authored **Technical Requirements** (cross-platform compatibility, data store, API, Git reader, concurrency).  
- Contributed to **Risk Analysis** with Yuxuan on privacy, interruptions, and performance bottlenecks.  
- Set up **Discord and GitHub** on my system to support team communication and track project progress.  

![Screenshot 2025-09-20 at 7 28 06 PM](https://github.com/user-attachments/assets/2a1c5ed8-0c39-4186-97e2-e381dbe3fc3c)

---

### WEEK 4 PERSONAL LOG 
(Sep 22–28, 2025)
- Helped teammates **Nade** and **Shuyu** with GitHub Kanban setup, including the pull request “**Create Project Directory Structure #15.**”  
- Initiated the Group Project Proposal document by referencing the sample template provided on Canvas. Made progress on the "COSC 499 Week 4 Project Proposal" with **Michelle**, making sure that we both followed the slides.  
- While drafting the Project Scope and Usage Scenario, I introduced the idea of comparing our dashboard’s progress indicators to Workday’s percentage tracker for degree completion. This analogy made the concept easier to understand and gave the team a clear, relatable way to explain how our system shows progress toward goals.  
- Worked with **Michelle** on the System Architecture Diagram Document along with the designs following the templates on the weekly slides.  
- Reviewed **Nade**'s pull requests.  

<img width="888" height="623" alt="Week4PersonalLog" src="https://github.com/user-attachments/assets/4d183521-853a-43fe-979c-dc21d235640b" />


### WEEK 5 PERSONAL LOG 
(Sep 29-Oct 05, 2025)
- Worked with **Michelle** and **Parsa** to understand the Data Flow Diagram (DFD) requirements as outlined in Dr. Hui’s lecture slides. (They helped me understand what is expected on the dfd diagram in more detail.)
  - Reviewed examples of Level 0 (Context Diagram) and Level 1 (System Diagram) to learn how to properly represent processes, data stores, and external entities.
  - Collaboratively designed the Level 0 and Level 1 DFD for our Mining Digital Work Artifacts system using Google Drawings, ensuring consistency between both levels.
  - Defined the key entities (User, System API) and internal processes (Source Selection, Mining/Scan, Analytics & Generation, Visualization & Export, Save Portfolio).
  - Mapped each process to its corresponding requirement:
     - UR-01 (Source Selection) = Source Selection process
     - UR-02 (Transparency) and UR-03 (Progress & Feedback) = feedback flows within Mining/Scan
     - UR-04 (Control) and UR-05 (Privacy) = user interactions that manage or limit scanning
     - UR-06 (Insights) = Analytics & Generation
     - UR-07 (Export) = Visualization & Export
     - UR-08 (Accessibility) = consistent flow design and labeling for screen-reader compatibility
- ***(I had previously worked on the user requirements section on the **Project Requirements** document)***
- Feedback emphasized improving clarity within labels and showing how progress updates (UR-03) interact with the user interface and error logs.
- No unresolved problems this week — most questions were clarified during in-class discussions by reviewing other teams’ DFD diagrams. Our group was able to solve the remaining issues collaboratively during team meetings, which helped us further polish our DFD diagram.
- Further steps I participated in: polishing flow labels, incorporate progress-feedback details (from in class discussions) into the final DFD, and prepare for the DFD quiz.

<img width="1075" height="625" alt="WEEK5EVAL" src="https://github.com/user-attachments/assets/8c1024b7-c908-42d1-bb4d-f4e285e972c9" />

### WEEK 6 PERSONAL LOG 

 Work Completed This Week:
- Collaborated with Parsa and Michelle on environment setup
- Successfully configured Docker and Electron on my system to begin our local development environment.
- **Parsa** and **Michelle** guided me through the setup and explained key dependencies and configuration files.
- I actively contributed by helping identify and fix minor bugs and configuration errors that appeared during setup.
- This collaboration ensured all team members are now on the same technical baseline, reducing future compatibility issues and enabling smoother integration across systems.
- Improved and aligned project diagrams
- Made refinements to the system diagrams based on the feedback received from our last review session.
- Focused on improving clarity of data flow and inter-module communication to ensure the diagrams reflected our updated design.
- These improvements directly shaped our Work Breakdown Structure (WBS) by clarifying task dependencies and priorities.
- The updated visuals have made it easier for the team to identify responsibilities and maintain consistency between documentation and implementation.
- Documented Sections 4.0 – 7.0 of the WBS Document
- Authored detailed write-ups for future system components, including:
  - 4.0 User Permission Management – ensuring user consent and transparency for any external service use.
  - 5.0 Offline Functionality – outlining fallback mechanisms for full offline operation.
  - 6.0 User Configuration Storage – describing how user preferences will persist securely.
  - 7.0 Project Classification – defining fair distinction between individual and collaborative projects.
- My writing focused on clarity, transparency, and privacy-first design principles.
- This documentation lays the foundation for ethical, privacy-aware development, helping future milestones maintain compliance and user trust.
- Including the purpose, implementation plan, and expected outcomes for each section ensures that the next development phase has clear technical direction and avoids ambiguity.

  
- Assigned and managed Kanban task:
  - Took ownership of the task — “Parse a specified zipped folder containing nested folders and files.”
  - The goal is to implement metadata extraction (file path, size, and last modified date) for organized and automated file handling.
  - Even though implementation will occur later, pre-planning the task ensures that parsing and indexing mechanisms are well-defined, modular, and aligned with our architecture.
  - This will help streamline local scanning processes, contributing to higher system efficiency.
  - Supported team organization and sprint management
  - Helped other team members identify, define, and assign their tasks on the Kanban sprint board.
  - Ensured a balanced workload and logical sequencing of activities based on dependencies.
  - Improved team communication and accountability by making task ownership explicit.
  - This structured approach supports better sprint visibility and progress tracking, which will be valuable for both reporting and evaluation.
 
OVERALL: My work this week strengthened both the technical foundation and documentation quality of the project.
Setting up Docker and Electron ensures smooth cross-team development.
Refining diagrams and WBS documentation provides a clear roadmap for upcoming milestones.
The privacy-centric sections I authored establish trust and compliance standards early in development.
Active contribution to Kanban planning and task alignment has improved workflow clarity and collaboration across the team.

<img width="1026" height="485" alt="WEEK6PERSONALLOG" src="https://github.com/user-attachments/assets/2f581570-c6b8-40c6-af8b-a108720c9a9a" />

