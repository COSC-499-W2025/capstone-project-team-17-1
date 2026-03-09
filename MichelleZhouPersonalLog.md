# COSC 499 TEAM 17 Personal Log - Michelle Zhou 27227602

## Table of Contents

- [T2 Week 1 Personal Log](#T2-week-1-personal-log)
- [T2 Week 2 Personal Log](#T2-week-2-personal-log)
- [T2 Week 3 Personal Log](#T2-week-3-personal-log)
- [T2 Week 5 Personal Log](#T2-week-5-personal-log)
- [T2 Week 8 Personal Log](#T2-week-8-personal-log)
- [T2 Week 9 Personal Log](#T2-week-9-personal-log)

- [Week 3 Personal Log](#week-3-personal-log)
- [Week 4 Personal Log](#week-4-personal-log)
- [Week 5 Personal Log](#week-5-personal-log)
- [Week 6 Personal Log](#week-6-personal-log)
- [Week 7 Personal Log](#week-7-personal-log)
- [Week 8 Personal Log](#week-8-personal-log)
- [Week 9 Personal Log](#week-9-personal-log)
- [Week 10 Personal Log](#week-10-personal-log)
- [Week 11 Personal Log](#week-11-personal-log)
- [Week 12 Personal Log](#week-12-personal-log)
- [Week 13 Personal Log](#week-13-personal-log)
- [Week 14 Personal Log](#week-14-personal-log)

## Week 3 Personal Log

- (Sep 15 - 21, 2025)<br />
  
<img width="1326" height="717" alt="image" src="https://github.com/user-attachments/assets/8cc396b5-06fb-48d6-9dc8-97adeb513648" /><br />


Week Recap: Collaborated with the team to flesh out project plan, usage scenarios, and desired features. Worked on defining project scope and data requirements, list of functional and non-functional requirements document, and printed them for Wednesday's class. Continued to modify and refine requirements throughout the week following group discussions. <br />

## Week 4 Personal Log

- (Sep 22 - 28, 2025)<br />

<img width="1326" height="717" alt="image" src="https://github.com/user-attachments/assets/47842e51-11a0-44d6-9d25-1dfe34a6cdb6" /><br />

Week Recap: Researched various development option for project tech stack. Focused on creating system architecture design models based on in-class slides. Collaborated with team on project proposal document. Expanded on the application process experienced by users and created the UML diagram and use cases accordingly. Attended group meetings, assigned tasks, and ensured clear communications between all members. <br />

## Week 5 Personal Log

- (Sep 29 - Oct 5, 2025)<br />

<img width="1326" height="717" alt="image" src="https://github.com/user-attachments/assets/18834751-87e4-44e0-b710-125409e666b1" /><br />

Week Recap: Researched various types of DFD and looked back on previous work to gather inspiration. Worked with team to create DFD level 0 and 1 during Monday class. Finalized application system by focusing on flushing out main process and data flow. Worked out specific databases and logs systems. Exchanged DFD with other teams during Wednesday class and discussed various differences/similarities.

## Week 6 Personal Log

- (Oct 6 - Oct 12, 2025)<br />

<img width="1326" height="717" alt="image" src="https://github.com/user-attachments/assets/f23b80f7-513c-4b62-96f5-712c2bf5ab10" />

Week Recap: Finalized system architecture design based on feedback, making sure to address all areas that were previously vague or overly general. Each system component and interaction was clarified to ensure alignment with our requirements. Worked with team to set up local environment using Docker and Electron. Updated the project README with essential links to diagrams and explanations. Worked on finalizing DFD Level 1 and diagram explanation.

Completed Work Breakdown Structure with team and delegated tasks to ensure that every member had clear actionable items and understood their responsibilities. Kept the group organized and focused by facilitating discussions, clarifying goals, and tracking action items.

## Week 7 Personal Log

- (Oct 13 - Oct 19, 2025)<br />

<img width="1326" height="717" alt="image" src="https://github.com/user-attachments/assets/e80297f2-5b2c-44df-b940-a689f61f24d7" />

Week Recap: Collaborated closely with the team to review one another's code and pull requests. Provided detailed feedback on functionality and any errors that arose during testing. There was noticeable improvement in team communication and organization. Everyone was proactive in updating task progress and offering assistance when needed. This level of collaboration helped us stay on top of our deliverables while ensuring steady progress. Worked on User Consent Feature and saving inputs in a database. 


## Week 8 Personal Log

- (Oct 20 - Oct 26, 2025)<br />

<img width="966" height="566" alt="image" src="https://github.com/user-attachments/assets/b127074f-4733-48f4-ba73-9ff5789437ad" />

### Week Recap: 
- Worked on 'Metrics Calculation Module' task #43
- Discussed new implementations with members
- Reviewed team member's PR and help test new features

This week i worked on implementing a unified metrics extraction module that ties together quantitative activity analysis and quantitative skill inferences. To start, I defined and formalized each core metric in order to identify the type of data the program should be looking for. Each metric type is then calculated alongside a contribution analysis to obtain an overview of the project activities/behaviour. The metrics:extract handler receives these details and passes them to analyzeMetrics() which returns with a summary of all key metrics. Lastly, I am working on outputting the metrics to the Electron UI. To do this, I am writing a renderer which will request the finalized data and present it as the corresponding activity patterns.

Aside from my own code, I assisted in troubleshooting pr's where feature/extract-key-skills resulted in many merge conflicts. My team and I also coordinated on new task assignments. We reviewed our progress thus far and are actively working towards milestone 1 completion.

### Next Week:
- Finish Metrics Calculation Module
- Start developing "Chronological List of Projects" task #67


## Week 9 Personal Log

- (Oct 27 - Nov 2, 2025)<br />

<img width="966" height="567" alt="image" src="https://github.com/user-attachments/assets/74837693-afd9-4c70-8351-38561a420fb0" />

### Week Recap: 
- Focused on converting codebase from javascript to python
- Started working on 'Chronologica List of Projects' task #67
- Discussed new feature implementations with team (outside of wbs)
- Reviewed team member's PR

This week, after our Wednesday check-in, my group and I prioritized converting our existing JavaScript codebase to Python. This transition took precedence over implementing any new features before any further development. In addition, I completed and refined the metrics calculation module feature. I added more comprehensive tests to cover edge cases such as empty contributors, invalid numeric entries, and mixed file types. The implementation was modified to accomodate these scenarios, and helper functions were added to ensure the code is maintainable. These improvements enture that the result outputted are accurate and reliable.

During our team check-in, we discussed exploring additional features outside of our current WBS. We are aiming to solidify enhancements that will make our application more appealing with real-world benefits for end users.

### Next Week:
- Finalize features to implement outside wbs and delegate tasks
- Continue working on "Chronological List of Projects" task #67
- Start "Outputting Key Information for Project" task #54

## Week 10 Personal Log

- (Nov 3 - Nov 9, 2025)<br />

<img width="969" height="566" alt="image" src="https://github.com/user-attachments/assets/5f6ae3a9-0c03-4205-9956-31dadbcc61e3" />

### Week Recap: 
- Worked on finishing 'Chronologica List of Projects' and 'Outputting Key Information for Project'
- Reviewed PR's
- Discussed with team more feature implementations and additional considerations for refinement
- Discussed future frontend implementations
- Flushed out my feature specifics and requirements to align more with instructor feedback (tailored for user resumes)

### Next Week:
- Finish and submit PR's for task #67 and #54
- Start new feature implementation
- Team check-in for milestone #1

## Week 11 Personal Log (Reading Week)

- (Nov 10 - Nov 16, 2025)<br />

## Week 12 Personal Log

- (Nov 17 - Nov 23, 2025)<br />

<img width="1006" height="706" alt="image" src="https://github.com/user-attachments/assets/f6478465-1457-4bfd-a1a4-9eb85735a17a" />

### Week Recap: 
- Finished and submitted task #67
- Reviewed PR's and assisted in debugging errors in team member's code
- Collaborated on step 1 + 2 of matching job description to user projects feature
- Started working on task #89 Step 3 Extract Company-Specific Qualities

### Next Week:
- Collaborate with team to finish job description matching feature (last feature)
- Finalize code for Milestone #1
- Convert outputs to match resume-style writing for M1 demo
- Prepare for M1 presentation

## Week 13 Personal Log

- (Nov 24 - Nov 30, 2025)<br />

<img width="1206" height="705" alt="image" src="https://github.com/user-attachments/assets/e9c43e78-53e1-413f-9fdd-eb7efc9df79e" />

### Week Recap: 
Worked on finishing our final feature implementation which extracts target company qualities and matches them with existing user projects skills. This moves from generic job skill matching to company specific matching, capturing not only technical skills but also values and work styles. It provides a concrete bridge from mined project skills to company aligned, resume ready bullet points.

System can now:
  - Parse public company text and infer what they value (technical skills, traits, culture, work style)
  - Cross reference inferred qualities against a user's extracted project skills
  - Generate taulored resume bullet points for a specific target company
      
Skill Matching and Extraction
- Reused existing extract_job_skills as the core building block
    - Scans raw text (job ad, careers page, company description)
    - Normalizes everything for consistent matching
- Maps high level traits to phrases commonly seen in job ads.
- Implemented helpers for safer string matching (as suggested in previous pr's)
    - Avoids false triggers on partial words
    - Uses word boundaries for single word terms
- Implemented extract_softskills() for each trait/phrase to return a sorted list

Building Company Profile
- Uses user input url to fetch data from company webpage
- Implemented simple HTTP helper to fetch page contents
- Makes sure the profile is intentionally minimal but compatible with downstream ranking and bullet generation logic

Resume Bullet Point Generation
- Uses matched skills and traits from user projects and target company specific skills to generate resume-style bullet points
    - Aggregates all matched skills
- Outputs a list of tailored resume strings that can later be directly pasted into targeted resume sections

Team Meetings
- Collaborated and finished Team Contract
- Discussed and collaborated on presentation slides
- Distributed tasks for presentation 

### Next Week:
- Finalize presentation slides + present
- Final revision/refractor of code and update ReadMe for demo
- Work on Milestone #1 video demo


## Week 14 Personal Log

- (Dec 1 - Dec 7, 2025)<br />

<img width="968" height="568" alt="image" src="https://github.com/user-attachments/assets/70d54d06-27e6-48c4-a095-fb1fd3a2cf4f" />

### Week Recap: 
Worked closely with the team to finalize, deliver and wrap up all major components required for Milestone #1. This included delivering our presentation, completing the full video demo, and refining all associated documentation. We also continued integrating and refractoring our system so each feature is cleanly accessible through the terminal and connected smoothly through our cli.py file.

Refractoring and Terminal-Based Feature Access
- Refractored code so each feature can be manually executed via terminal
    - Simplifies debugging and showcasing in video demo
  - Standardized function interactions across modules
  - Improved organization and readability to prepare for future development

Feature Integration Through cli.py
- Linked all primary features to a single CLI entrypoint
- Ensured consistent command structure and user output formatting
  
System Architecture and DFD
- Conducted team meetings to refine system architecture design and DFD based on new implementations/modifications
- Delegated work to efficiently complete all remaining Milestone #1 objectives

Milestone #1 Deliverables
- Delivered team presentation
- Finished Milestone #1 video demo
- Refined and updated README
- Updated all required documentation

### Next Week:
- Work on possible new features
- Further refractoring and cleanup based on milestone feedback

## T2 Week 1 Personal Log

- (Jan 5 - Jan 11, 2026)<br />

<img width="969" height="565" alt="image" src="https://github.com/user-attachments/assets/a84a3419-0b93-4039-9575-55973d83fe2c" />

### Week Recap: 
Worked on creating a start up menu for the user to navigate with upon running the program. Upon granting user consent, it enters a loop with all possible program options. This makes it easier to navigate and more user/testing friendly for future implementations. Additionally, it incorporates the functions from milestone #1 and creates a centralized point for all interactions.

- Created start up menu for application
- Integrated menu options with existing program functions
- Discussed milestone #2 implementation with team
- Reviewed and tested teammate's code and pr

### Next Week:
- Complete specific integrations for all menu options so that everything can be ran through it
- Wrok on new feature for milestone #2

## T2 Week 2 Personal Log

- (Jan 12 - Jan 18, 2025)<br />

<img width="967" height="566" alt="image" src="https://github.com/user-attachments/assets/42266e56-1b77-4700-aca2-324e76ea68eb" />

### Weekly Recap:
This week continued from last week's start up manu work by integrating all the underlying milestone features reliably. I focused on connecting the menu to existing modules, fixing integration issues caused by inconsistent snapshot data, and writing tests so future changes do not break basic navigation.

Coding tasks<br />
I expanded the startup menu so each option routes to the correct functionality. I also included normalization logic to bridge differences beteween database row fields and snapshot payload keys so the menu can work across multiple stored snapshot shapes without breaking the program. 

Testing or debugging tasks<br />
I debugged several runtime issues triggered by menu execution where functions expected dict maps but received lists. I added unittest coverage for the flow using mock data inputs and core helper calls. I also adjusted imports to avoid environment failures.

Reviewing or collaboration tasks<br />
I helped review teammate prs for milestone 2 changes which includes success endpoints and resume textual display logic. I helped test new implementations and worked on adding additional tests which achieved better coverage for niche scenarios such as more consistent outputs even when input parameters may be missing.

### Additionally:
The primary blocked for this week was inconsistent snapshot schemas across the pipeline. This caused issues in both ranking and timeline utilities when called through the menu. I addressed this with normalization and correct data shaping prior to passing inputs to shared functions. Next week I plan to fully finalize the start menu in preparation for peer testing. I will also work on implementing milestone 2 features with the rest of the team.


## T2 Week 3 Personal Log

- (Jan 19 - Jan 25, 2026)<br />

<img width="972" height="571" alt="image" src="https://github.com/user-attachments/assets/0c530656-2fa9-4d0c-b57b-f25d12c6f651" />

### Weekly Recap:
This week built directly on last week's integration work by flushing out user facing flows and improving reliability across multiple core features. The focus shifted from just connecting features to making them correct, explicit, and user friendly. Several edge cases surfaced once features were tested through the menu which let to massive refinements in both logic and test coverage. In parallel, the team and I were preparing for the upcoming peer testing by designing a clear evaluation flow and participant guidance.

Coding tasks<br />
I refractored the consent handling to ensure user permission is never implicitly granted. A unified method was introduced to only prompt when no prior consent decisions exists. This additionally supports session verses saved consent and correctly persists decisions to config. The consent flow now displays various messages for first time users vs returning users for imroved clarity. The application also exits cleanly without progressing further to the main menu when consent is denied. This structure was designed specifically to be compatible with future GUI frontend implementation by separating prompting logic from enforcement.

Testing or debugging tasks<br />
A significant portion of this week was spent debugging consent related edge cases. Early versions of the flow incorrectly auto granted consent, failed to reprompt after revocation, or existed prematurely after acceptance. These were traced to mismatches between prompt return values and decision handling. The updated unittests now cover all possible user behaviours. 

Reviewing or collaboration tasks<br />
I reviewed and tested teammate PRs by providing feedback on usability, code reuse, and test alignment. I helped validate that new features behaved correctly when invoked through the menu rather than in isolation. 

### Additionally:
This week's main blocker was the interaction between persisted configuration state and test isolation. This was resolved by redirecting congif and log paths to temporary directories during tests and avoiding implicit stdin reads. Next week, I will focus on implementing Resume Textual Display task #179. This will include generating resume ready project entries containing relevant details. The goal is to ensure the content is professionally formatted and suitable for direct inclusion in a resume while integrating cleanly with existing snapshot and resume pipelines.


## T2 Week 5 Personal Log

- (Jan 26 - Feb 08, 2026)<br />

<img width="971" height="570" alt="image" src="https://github.com/user-attachments/assets/780451ca-e297-4063-ab69-89a7da9e9348" />

### Weekly Recap:
The past two weeks continued from previous last week’s focus on stabilization and consent integration work by expanding the backend API surface and completing the job description matching feature from the end of Milestone 1. The focus shifted from purely internal CLI flows to designing, implementing, and validating a clean FastAPI interface for portfolio. Subsequently, I ensured these features remain fully aligned with existing menu-driven workflows. A significant portion of time was spent researching and learning how API endpoints, request validation, and response handling work in FastAPI, particularly in comparison to the earlier Flask-based retrieval layer. This effort resulted in clearer API contracts, stronger validation, more consistent behavior across entry points, and improved test coverage.

Coding tasks<br />
I fully completed the job description matching feature ([PR #207](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/207)), enabling users to input or load a job posting and compare it against analyzed project skills through a unified, menu-driven flow. This involved integrating skill extraction, project skill retrieval, and resume-friendly result formatting that clearly distinguishes matched and missing skills.

In parallel, I expanded and aligned the backend by adding new FastAPI portfolio endpoints ([PR #205](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/205)) for generating, retrieving, editing, and exporting portfolios. Export supports JSON, Markdown, and PDF formats, with proper binary handling and response headers for PDF downloads.

To ensure consistency across the system, I aligned CLI behavior with the new FastAPI routes so portfolio and job matching features follow the same logic regardless of access point. I also refactored shared logic into helper functions, introduced enum-based export validation, and spent time researching and applying FastAPI concepts such as routing, request validation, and dependency handling to improve reliability and extensibility.

Testing or Debugging Tasks<br />
I expanded unit test coverage for the job matching feature, validating skill extraction, overlap detection, partial matches, and resume snippet generation, and fixed edge cases such as case sensitivity and no-match scenarios. I added a FastAPI TestClient suite for portfolio endpoints, covering success paths, validation errors, and PDF responses, and resolved issues related to request schema mismatches, router registration, and FastAPI’s 422 validation behavior.

Minor refactor-related bugs were fixed, and the test suite now runs reliably without external dependencies or persistent storage.

Reviewing or collaboration tasks<br />
I reviewed and provided feedback on teammate pull requests related to backend storage improvements, including a content addressable file storage and deduplication layer. I also tested related changes locally to ensure compatibility with existing analysis and retrieval workflows. In parallel, I collaborated with teammates by aligning API design decisions with the broader project architecture and ensuring the new FastAPI endpoints fit cleanly alongside the existing APIs.

### Additionally:
Next week, I plan to focus on integrating portfolio and resume generation more tightly by implementing resume ready textual outputs derived from analyzed projects. The goal is to ensure generated content is professionally formatted, reusable across interfaces, and integrates cleanly with the existing snapshot, storage, and resume pipelines. I also plan to learn and experiment using Postman with the team to properly test api calls and endpoints.

## T2 Week 8 Personal Log

- (Feb 09 - Mar 01, 2026)<br />

<img width="971" height="571" alt="image" src="https://github.com/user-attachments/assets/9d0097a5-ca05-4f15-84b3-9db7e2e5277a" />

### Weekly Recap:
The past two weeks built on previous expansion of FastAPI endpoints, specifically stablizing ranking logic, strengthening endpoint reliability, and finalizing portfolio showcase endpoints. Portfolio, job matching, and frontend/backend integration are now functional and stable. This week marks the completion of Milestone #2.

Coding tasks<br />
I added and finalized the /job-matching endpoints ([PR #232](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/232)), ensuring it properly retrieves project snapshots, build a job profile, and compute dynamic weights to return deterministic project ranking results based on the imported job description. The logic was improved to handle different internal skill formats, and assumptions from attribute errors during matching were fixed and removed. A major improvement this week was fixing the overall weight calculation logic ([PR #230](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/230)). Previously the weights were inconsistently applied and resulted in unstable scoring behaviour. This refractor now dynamically distributes weights between required and preferred skills, and reserves consistent portions for keyword overlap and recency. Ranking is now more realistic and mathematically stable. I also worked with Raunak to expand and stablize the portfolio showcase endpoints ([PR #224](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/224)). Analyzed project data and portfolio summaries can now be reliably retrieved for future frontend rendering.

Testing or Debugging Tasks<br />
This week involved significant debugging and stabilization work. Issues included database misconfiguration during endpoint tests, integration mismatch between snapshot structure and skill extraction logic, inconsistent weight dictionary structure, and internal server errors from missing fields. These were resolved by refractoring weight merging logic to guarantee consistent keys, remove outdated references to payload-supplied weights, properly override db during tests, and aligning snapshot skill structure with ranking logic.

Both mocked endpoint tests and integration tests using isolated SQLite db were added to validate real system behaviour. All endpoints now return stable and predictable responses.

Reviewing or collaboration tasks<br />
I reviewed and provided feedback on teammate prs related to a deep ai analysis, which allows users to select specific files and request a targeted analysis. I evaluated the architectural flow to ensure it respects our external permission design and cleanly integrates with our snapshot system. I also provided feedback related to our github commit metadata capture feature, focused on improving consistency and resume generation reliability. I verifed that these changes maintain metric consistency and improve downstream behaviour in resume generation.

### Additionally:<br />
Moving forward my focus will shift towards refractoring complex or confusing backend logic and improving code clarity. I will also be supporting frontend development and improving data output presentation (final exports). The goal is to polish the system and making sure everything works together seamlessly for our target audience.

## T2 Week 9 Personal Log

- (Mar 02 - Mar 08, 2026)<br />

<img width="966" height="569" alt="image" src="https://github.com/user-attachments/assets/f45b6d22-0a1d-43e1-8ae9-99fbd673ab4c" />

### Weekly Recap:
This week focused on refractoring and stabilizing the cloud sync layer, specifically the authenticated cloud routes and Cloudflare R2 storage helpers. The main goal was to improve security, reliability, and maintainability without changing core cloud functionalities. A major portion of the work involved removing unsafe hardcoded materials and moving configuration into environment variables. This in turn improved authenticated route handling using bearer token session lookup. The other portion of work consisted of testing cloud sync routing and storage through automated tests.

Coding tasks<br />
I refractored cloud_storage.py ([PR #283](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/283)) to remove hardcoded credentials and replace them with environment variable based configuration. This was important security improvement because the previous implementation stored access keys directly in the source code. This was unsafe and difficult to manage across environments. The storage layer now validates required cloud configuration prior to creating a client. It also uses a shared cached client retriever to remove redundant operations. I also enhanced object_exists() so that it only returns False for real true missing object cases. It also reraises other cloud errors instead of stashing them. These changes ensure storage failures are easier to debug in the future and prevents permission/service errors from thrown as missing file errors.

cloud.py was improved for routing level authentication and error handling. Protected cloud routes now resolve the user through bearer token backed session lookup using the current auth session instead of a global user value. This change makes cloud operations much more reliable. I also implemented a shared cloud error handling for configuration issues and cloud failures. They now return simple, clean and predictable HTTP responses.

Testing or Debugging Tasks<br />
A large portion of work this week involved debugging encironment, authentication, and testing various issues ([PR #284](https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/284)). I implemented automated tests for cloud_storage.py using mocked tests to cover cloud configuration validation, object existence checks, db upload/download behaviour, project zip upload/download, and deletion handling.

I also implemented automated tests for cloud.py, focusing on authenticated route behaviour, bearer token session resolution, protected cloud route access, and cloud operation response handling. Much of the debugging involved aligning the tests with the refractored implementation (correct names, cached client behaviour, expected response formats). The addition of these tests provide stronger evidence that the refractored cloud sync layer behaves properly without relying on live Cloudflare R2 calls.

Reviewing or collaboration tasks<br />
This week involved reviewing and aligning cloud related implementation details with our backend. I verified that cloud routes fit properly with the existing auth flow and db storage design. I also checked that the cloud helper structure was compatible with the upload, download, and restore workflow. I coordinated the refractor work with parsa with the existing frontend and auth flow by making sure the cloud endpoints continued to behave correctly when called from the electron app following user login.

### Additionally:<br />
Moving forward my focus will continue on stabilizing and polishing the codebase. I will also shift towards connecting backend features with our electron dashboard and making sure the backend functionalities is surfaced clearly and reliably in the UI. I will also be helping with frontend development, specifically portfolio data and presentation.

