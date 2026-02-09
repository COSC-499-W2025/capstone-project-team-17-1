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
<img width="1084" height="557" alt="Screenshot 2025-10-25 at 2 13 59 PM" src="https://github.com/user-attachments/assets/16b9b472-78ef-4fb3-ac79-8ff41fdb9307" />

### 2. Weekly Goals Recap
- complete 'Collaboration Analysis Module' task #42
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them

This week I completed the Collaboration Analysis Module (task #42), which is responsible for analyzing team contribution patterns in a project. To implement this, I parsed git log --numstat output to extract meaningful contribution metrics like commit count, lines added/removed, and review involvement. I also added logic to distinguish between real contributors, shared accounts, and bots, since many Git histories include dependabot or team accounts that can distort results. The module now stores contribution summaries in our database so they can be reused later for analytics and user portfolio generation.

After finishing the backend logic, I connected it to our application by updating the Electron IPC layer and preload bridge, and I built the frontend components to display collaboration summaries, contributor leaderboards, and export options (JSON/CSV). I also added refresh and export handlers in the UI. During development, I ran into compatibility issues with better-sqlite3 when running tests inside Electron, so I added an electron-rebuild script to solve native module loading problems.

Besides coding, I also helped organize the team by assigning some new tasks for the next phase and reviewing teammates’ pull requests. I discussed implementation details with others to make sure this module fits our data pipeline design and that future visualization features can build on top of it smoothly.

Overall, this week helped me improve both system design thinking and team coordination skills.
  
### Completed Tasks Week 8
'Collaboration Analysis Module' task #42


## WEEK 9 Personal LOG (Oct27 - Nov2, 2025)
### 1. Type of Tasks Worked On
<img width="1067" height="553" alt="Screenshot 2025-11-01 at 1 33 56 PM" src="https://github.com/user-attachments/assets/41c9c7b7-5a4a-478f-8a4b-2727bd4a486d" />

### 2. Weekly Goals Recap
- complete 'Rank importance of each project based on user's contributions' task #64
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them
- transfer our electron code to python code
- fix syntax error of member's work (fix syntax error of cli.py #77)
  
This week, I completed the “Rank importance of each project based on user’s contributions” task (#64). I implemented a ranking algorithm that evaluates each project by multiple weighted factors, including artifact count, total bytes, recency, activity level, and contribution diversity. The system extracts these features, converts them into numeric weight values, and then computes a composite score to produce a ranked list with detailed breakdowns of the influencing factors.

To support this feature, I designed and implemented the weight calculation algorithm, feature extraction logic, and sorting pipeline. The ranked results are now output in a structured format for both display and further analysis.

Beyond coding, I also coordinated with team members to review pull requests, assign new tasks, and guide development for the next phase. I discussed code details with teammates to ensure consistent design and data handling across modules. Additionally, I worked on transferring our Electron codebase to Python, focusing on maintaining compatibility and preparing for future backend integration.

Overall, this week strengthened my understanding of algorithm design, feature engineering, and project management in a collaborative development environment.

### Completed Tasks Week 9
- 'Rank importance of each project based on user's contributions' task #64
- fix syntax error of cli.py #77

## WEEK 10 Personal LOG (Nov3 - Nov9, 2025)
### 1. Type of Tasks Worked On
<img width="1057" height="529" alt="Screenshot 2025-11-07 at 7 46 56 PM" src="https://github.com/user-attachments/assets/0d78fb71-7df1-47a1-934c-d32c8fb6a049" />

### 2. Weekly Goals Recap
- complete 'Top Project Summaries' task #65
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them
- cleaned the repository to make it fully Python-only

This week, I completed the “Top Project Summaries” feature set (#65), which implements a Python-only pipeline for automatically generating structured summaries of top-ranked projects. The system integrates multiple components, including summary templates, evidence gathering, an offline-first auto-writer, hallucination guardrails, and multi-format exporters. It collects data from stored snapshots and optional external sources such as pull requests, issues, and benchmark results, then generates concise yet traceable summaries with quoted evidence, confidence indicators, and reference links.

To support this functionality, I developed the generate_top_project_summaries orchestration module and implemented full unit coverage in tests/test_top_project_summaries.py to ensure reliability and reproducibility. I also cleaned the repository to make it fully Python-only by removing outdated Electron/JS assets, sample bundles, generated HTML, logs, and build artifacts.

Beyond implementation, I reviewed teammates’ pull requests, discussed integration details, and helped assign new development tasks for the next week. Overall, this week enhanced my experience in automated summarization design, factual verification, and collaborative backend development within a large-scale system.
  
  ### Completed Tasks Week 10
  'Top Project Summaries' task #65

  ## WEEK 12 Personal LOG (Nov17 - Nov23, 2025)
### 1. Type of Tasks Worked On
<img width="1056" height="596" alt="Screenshot 2025-11-21 at 6 00 05 PM" src="https://github.com/user-attachments/assets/d54808d7-f2c3-4f7e-84b0-5724be148923" />

### 2. Weekly Goals Recap
- complete 'Section 13.4 – Storage Validation and Backup' #87
- complete 'Section 9.1.1 + 17.2 – Pull-Request / Issue Evidence' #86
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them

This week, I completed the full-system verification task covering terminal output auditing and Milestone Demo readiness. I conducted an end-to-end pass across all implemented features to ensure every CLI command, analysis routine, and storage operation is producing correct, complete, and consistent terminal output. This work guarantees that the current build can reliably support the milestone demo scenario from ZIP ingestion to insight generation.

To achieve this, I reviewed the entire codebase, ran each pipeline component in isolation and in sequence, and validated all output formats against the expected behavior specified in our milestone documentation. Several modules received targeted fixes for missing messages, inconsistent formatting, and edge-case handling. The final demo path (upload → extract metadata → analyze repos → rank contributions → generate summaries → store insights) now runs smoothly without errors.

Beyond verification, I coordinated with team members to clarify responsibilities, helped them debug implementation issues, and ensured their new tasks align with the overall milestone plan. I also reviewed multiple PRs, provided feedback on integration points, and confirmed that storage validation, snapshot integrity, and external reference resolution behave correctly under the updated workflow.

Overall, this week strengthened the system’s reliability and ensured that our milestone demo operates cohesively across all modules. The work improved my familiarity with our CLI ecosystem, integration boundaries, and full-pipeline debugging, contributing to a more stable and demonstrable Python-only backend system.

 ### Completed Tasks Week 12
- 'Section 13.4 – Storage Validation and Backup' #87
- 'Section 9.1.1 + 17.2 – Pull-Request / Issue Evidence' #86

  ## WEEK 13 Personal LOG (Nov24 - Nov30, 2025)
### 1. Type of Tasks Worked On
<img width="1069" height="545" alt="Screenshot 2025-11-29 at 1 44 41 PM" src="https://github.com/user-attachments/assets/a2163a02-f2f1-4bc0-b7f2-10fbb8d7a0f4" />

### 2. Weekly Goals Recap
- complete 'Retrieve Previously Generated Résumé Item'#101
- discussed the code details with members
- Asssgin members to their tasks and create new tasks for picking up
- review member's PR and help them

This week, I completed the résumé-retrieval feature (Task #101) and integrated it into the full Python-only backend. The work introduced a complete storage and retrieval pipeline for résumé items, including new database tables for resume_entries and resume_entry_links, insertion utilities, and CLI commands for querying, filtering, previewing, and exporting résumé content. Users can now retrieve previously generated résumé components and export them in Markdown, JSON, or offline PDF through a lightweight integrated generator.

To support this new workflow, I extended the storage helpers with updated schema migrations, strengthened snapshot backup and export utilities, and refined the ranking CLI so it can consume the expanded snapshot format. I also added a dedicated test suite (tests/test_resume_retrieval.py) to validate schema introspection, filtering logic, preview formatting, and export correctness, ensuring the entire path from storage to output behaves predictably.

Beyond the feature implementation, I discussed code details with team members, clarified technical responsibilities, and assigned new tasks to maintain development momentum. I reviewed multiple PRs, provided feedback on integration boundaries, and helped resolve issues in modules that interact with the snapshot system.

Overall, this week strengthened our résumé-related tooling and improved backend consistency. The system now supports richer artifact retrieval, more robust export options, and a cleaner developer workflow for future milestone work.

### Completed Tasks Week 13
'Retrieve Previously Generated Résumé Item'#101

 ## WEEK 14 Personal LOG (Dec1 - Dec7, 2025)
### 1. Type of Tasks Worked On
<img width="1052" height="539" alt="Screenshot 2025-12-05 at 6 02 30 PM" src="https://github.com/user-attachments/assets/c4c471e9-a19d-40b8-af88-b8de4237686e" />

### 2. Weekly Goals Recap
- complete 'Enhance demo' #110
- complete team contract
- update DFD and system architecture diagrams
- complete demo video
- discussed the code details with members
- review member's PR and help them

This week, I completed the Enhance Demo task (#110), delivering an expanded and more coherent demo experience for Milestone #1. The updated demo surfaces all major WBS requirements in a single end-to-end flow, including improved consent handling, clearer logging, refined system outputs, and a more structured presentation of analysis results. These enhancements ensure that each subsystem appears visibly and consistently when running the demo, making it easier for both TAs and teammates to verify full-pipeline behavior.

I also completed the team contract together with the team and finalized the DFD and system architecture diagrams, aligning them with the latest backend structure and ensuring they accurately reflect our updated workflows and module responsibilities. To support our Milestone submission, I recorded the demo video and discussed code details with teammates so the presentation remains internally consistent.

In addition, I assigned tasks to team members, created new tasks to support workload distribution, and participated in several technical discussions. I reviewed PRs, provided integration feedback, and assisted with issues related to demo logic and system structure.

Overall, this week strengthened the clarity of our project narrative, improved the technical accuracy of our documentation and architecture, and ensured that our demo reliably reflects the full capabilities of the system for Milestone #1.

### Completed Tasks Week 14
- 'Enhance demo' #110
- team contract
- DFD and system architecture diagrams
- demo video

 ## WEEK 15 Personal LOG (Dec8 - Dec15, 2025)--extra
### 1. Weekly Goals Recap
- complete 'encapsulation for main feature'#128
  
This week I delivered the “encapsulation for main feature” milestone (#128) by carving the core logic into a reusable service layer and slimming the CLI to argument parsing and orchestration. The new services cover consent/config, archive validation+analysis, snapshot storage and
summaries, ranking, timelines, and top project outputs, while compatibility shims keep existing behaviors and tests intact. I verified the end-to-end flow with the full unit suite (python -m unittest discover -s tests -p 'test_*.py' -v), and coordinated with teammates on integration
details so downstream consumers can adopt the services without breaking changes. This work makes the system easier to test, mock, and extend, and keeps the demo and Milestone #1 flows consistent and transpare2-Jannt.

  
 ## Term2 week1 Personal LOG (Jan5-Jan11, 2026)
### 1. Type of Tasks Worked On
<img width="1085" height="626" alt="Screenshot 2026-01-09 at 8 21 50 PM" src="https://github.com/user-attachments/assets/b8d29095-ce6e-4d1e-94f2-4b74d526dac4" />

### 2. Weekly Goals Recap
- complete 'resume customization' #147
- complete 'Add error message for parsing and add nested demo' #145
- discussed the code details with members
- review member's PR and help them

This week, I completed the Resume Customization feature (#147), adding a persistent résumé-project description store with both API and CLI support. Users can now customize and save résumé-specific project wording without affecting portfolio text, and the résumé generator prioritizes this customized content. This directly supports the milestone’s human-in-the-loop requirement by allowing users to edit, persist, and retrieve concise résumé wording via CLI or HTTP API.

I also completed Add error message for parsing and add nested demo (#145), enhancing the robustness of zip analysis. The system now detects multiple error types—including corrupt entries, invalid JSON, non-UTF-8 files, empty files, unsupported extensions, and missing key files—while still producing a summary. Detected issues are emitted as warnings to stderr so users can see errors alongside analysis output. A new demo-4.zip with mixed error cases was added for CLI validation and demonstration.

In addition, I discussed code details with team members and reviewed teammates’ PRs, providing feedback and assistance to support integration and overall system consistency.

  ### Completed Tasks Week 1
  - 'resume customization' #147
- 'Add error message for parsing and add nested demo' #145

 ## Term2 week2 Personal LOG (Jan12-Jan18, 2026)
### 1. Type of Tasks Worked On
<img width="1080" height="625" alt="Screenshot 2026-01-16 at 8 39 30 PM" src="https://github.com/user-attachments/assets/0f10a068-1403-4516-9096-350dde897c51" />

### 2. Weekly Goals Recap
- complete 'Résumé Textual Display' #144
- Part of 'menu in terminal'#134
- discussed the code details with members
- review member's PR and help them
  
This week, I completed the Résumé Textual Display functionality by implementing a full, end-to-end résumé customization and display workflow across both the API and CLI. The system now supports résumé-specific project wording that is stored persistently and kept separate from portfolio descriptions. Multiple wording variants can be maintained, with an active version selected for résumé generation, and a clear priority rule is enforced during output (custom > generated > fallback). This ensures that résumé text is predictable, explainable, and does not get unintentionally overridden by automated generation.

To improve usability and transparency, the résumé preview output now explicitly indicates the source of the displayed text, making it easier to verify whether custom, generated, or fallback wording is being used. These behaviors are covered by HTTP-level tests to validate both error handling and priority enforcement, and the corresponding API endpoints are documented to support frontend integration.

In parallel, I contributed to part of the terminal main menu implementation, focusing on improving the user experience around résumé-related actions. The updated menu flow allows users to generate, preview, and customize résumé text more naturally within the CLI, reducing the need for manual commands and making the workflow easier to demonstrate and validate.

Beyond feature development, I spent time discussing implementation details and design decisions with team members to ensure consistency across modules. I also reviewed teammates’ pull requests, provided feedback on code structure and edge cases, and assisted with integration where needed to help keep the system stable and aligned with milestone requirements.

### Completed Tasks Week 2
- complete 'Résumé Textual Display' #144

 ## Term2 week3 Personal LOG (Jan19-Jan25, 2026)
### 1. Type of Tasks Worked On
<img width="1063" height="626" alt="Screenshot 2026-01-23 at 7 28 03 PM" src="https://github.com/user-attachments/assets/f6b33820-7116-486d-80c8-2f04160cdccd" />

### 2. Weekly Goals Recap
- complete [Enhance resume preview functionality and fix menu problem (#165)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/165)
- Add api documentation
- discussed the code details with members
- review member's PR and help them

This week, I completed the Enhance Resume Preview functionality and menu fixes by implementing a more detailed and structured résumé preview pipeline across both the CLI and API. The résumé preview now presents clearer, more readable output and supports fine-grained customization across multiple sections, including summary, body, skills, projects, and metadata. Users can add, edit, or delete résumé entries with duplicate prevention in place, and deletion behavior was refined to support both full removal and partial text updates, ensuring predictable and controllable résumé edits.

To improve reliability and maintainability, I fixed existing menu syntax and flow issues that affected the portfolio summary and timeline features, restoring stable end-to-end execution within the terminal interface. The résumé-related menu paths were aligned with the updated backend logic, making résumé generation, preview, and customization easier to access and demonstrate through the CLI.

In parallel, I added and updated API documentation for the new résumé routes and aliases, and introduced HTTP-style API tests that validate endpoint behavior without requiring a running server. This improves CI compatibility and makes it easier to verify correctness and error handling during development.

Beyond feature development, I discussed implementation details and design decisions with team members to ensure consistency across modules. I also reviewed teammates’ pull requests, provided feedback on edge cases and structure, and assisted with integration to help keep the system stable and aligned with milestone requirements.

### Completed Tasks Week 3
- complete [Enhance resume preview functionality and fix menu problem (#165)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/165)
- Add api documentation

 ## Term2 week4 Personal LOG (Jan26-Feb1, 2026)
 ### 1. Weekly Goals Recap
  - complete [Add portfolio textual display, improve menu usability and test stability (#184)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/184)
- edit api.md
- discussed the code details with members
- review member's PR and help them

This week, I completed the portfolio textual display and showcase functionality by extending both the CLI and API to support structured portfolio viewing, generation, and customization. I implemented full portfolio showcase editing under menu option 5, allowing users to modify Top Project content, highlights, references, or the entire markdown output in a controlled and user-friendly way. Corresponding API endpoints were added to support portfolio retrieval, generation, and editing, enabling consistent behavior across interfaces.

To improve usability and navigation, I enhanced the CLI menu flow by introducing global shortcuts and clearer prompts. Users can now press b to return to the previous level, m to jump directly back to the main menu, and use Enter to safely cancel actions. These changes resolve inconsistent navigation behavior across submenus and significantly improve the overall user experience when exploring portfolio and résumé features.

In parallel, I improved résumé preview customization flows and system stability. Résumé add/delete menus were refined to use snapshot-based defaults with clear save feedback, ensuring predictable behavior during customization. I also edited and updated API documentation to reflect the new portfolio and résumé routes.

Reliability was strengthened through comprehensive testing and fixes. I resolved existing test failures related to menu navigation and portfolio flows and added coverage for portfolio showcase preview, customization, and résumé preview paths. All tests now pass successfully (151 total), restoring full CI stability.

Beyond feature development, I discussed implementation details and design decisions with team members to align menu behavior and API structure, and I reviewed teammates’ pull requests, providing feedback and assisting with integration to keep the system consistent with milestone requirements.
  
 ### Completed Tasks Week 4
 - complete [Add portfolio textual display, improve menu usability and test stability (#184)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/184)


 ## Term2 week5 Personal LOG (Feb2-Feb8, 2026)
### 1. Type of Tasks Worked On
<img width="1073" height="616" alt="Screenshot 2026-02-06 at 6 14 36 PM" src="https://github.com/user-attachments/assets/e93c3441-bdef-441f-acfe-45deba9dab70" />

### 2. Weekly Goals Recap
- complete [portfolio showcase customizatio+ export pdf (#200)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/200)
- Make sure only use Fastapi
- discussed the code details with members
- review member's PR and help them

This week, I completed the portfolio showcase customization and PDF export functionality and prepared it for merging into the develop branch (#200).([portfolio showcase customizatio+ export pdf (#200)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/200))The work involved refactoring the backend from Flask to FastAPI to fully comply with project requirements and consolidating API routes to ensure consistency between the CLI workflow and future frontend integration. Portfolio-related endpoints were reorganized and extended to support stable portfolio summary retrieval, customization, and export.

To improve output quality and reliability, I enhanced the LaTeX-based PDF export pipeline, ensuring that customized portfolio showcases can be consistently generated as polished PDF documents. A setup script was added to streamline the installation of required PDF dependencies, making the export workflow reproducible across development environments.

Also, I updated and aligned tests to reflect the new FastAPI endpoints and revised CLI menu flow, resolving mismatches introduced by the backend refactor and maintaining system stability after the changes.

Beyond feature implementation, I discussed code-level details and design decisions with team members to align API structure and integration logic, and I reviewed teammates’ pull requests, providing feedback and technical assistance to help unblock issues and keep the project aligned with milestone requirements.

### Completed Tasks Week 5
- complete [portfolio showcase customizatio+ export pdf (#200)](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/200)
- Make sure only use Fastapi
