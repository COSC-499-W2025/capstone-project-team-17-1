# COSC 499 TEAM 17 Personal Log - Yuxuan Sun 27929934

## Table of Contents
- [Milestone 2 - Week 1 [Jan 5 – Jan 11, 2026]](#week-1-m2)
- [Milestone 2 - Week 2 [Jan 12 – Jan 18, 2026]](#week-2-m2)
- [Milestone 2 - Week 3 [Jan 19 – Jan 25, 2026]](#week-3-m2)
- [Milestone 2 - Week 4 [Jan 26 – Feb 1, 2026]](#week-4-m2)
- [Milestone 2 - Week 5 [Feb 2 – Feb 8, 2026]](#week-5-m2)
- [Milestone 2 - Week 6 [Feb 9 – Feb 15, 2026]](#week-6-m2)
- [Milestone 2 - Week 7 [Feb 16 – Feb 22, 2026]](#week-7-m2)
- 
- [Week 3 [Sep 15 – Sep 21, 2025]](#week-3)
- [Week 4 [Sep 22 – Sep 28, 2025]](#week-4)
- [Week 5 [Sep 29 – Oct 5, 2025]](#week-5)
- [Week 6 [Oct 6 – Oct 12, 2025]](#week-6)
- [Week 7 [Oct 13 – Oct 19, 2025]](#week-7)
- [Week 8 [Oct 20 – Oct 26, 2025]](#week-8)
- [Week 9 [Oct 27 – Nov 2, 2025]](#week-9)
- [Week 10 [Nov 3 – Nov 9, 2025]](#week-10)
- [Week 12 [Nov 17 – Nov 23, 2025]](#week-12)
- [Week 13 [Nov 24 – Nov 30, 2025]](#week-13)
- [Week 14 [Dec 1 – Dec 7, 2025]](#week-14)


## Week 3
[Sep 15 – Sep 21, 2025]
- Worked on Project Requirements Documentation
- Worked on Functional Requirements Part
- Worked on Non-Functional Requirements Part
- Edited document tabs and corrected grammar mistakes 

![Yuxuan Sun Week 3 Personal Log](https://github.com/ErenSun408/COSC499-Team17/blob/main/personal_log_img/YuxuanSun_COSC499_WEEK3_PEER-EVAL.png)

[Back](#table-of-contents)

## Week 4
[Sep 22 – Sep 28, 2025]
- Worked on [System Architecture Design](https://docs.google.com/document/d/1fZNTCu4YO0CFwIvErlJ1agD4Zyxgh6q11CnjB686NzY/edit?tab=t.0) (Deployment and Infrastructure; Cross-Cutting Concerns)
- Worked on [Project Proposal](https://docs.google.com/document/d/1yNkyeBqHvSgFAER2WQUW5GLdEmcIMknSAGh68UDHqCg/edit?tab=t.0) (Tech Stack)

<img width="1560" height="916" alt="image" src="https://github.com/user-attachments/assets/3f2ff4b4-7ef8-48ba-9c9b-c82961d0180e" />

[Back](#table-of-contents)

## Week 5
[Sep 29 – Oct 5, 2025]
- Worked on [Data Flow Diagram](https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/main/docs/design/L0%26L1%20DFD.png) (Level 1)

<img width="1549" height="905" alt="493a325c89dbbce60a655c17c204dd28" src="https://github.com/user-attachments/assets/749bbf1b-bc70-4f2a-8b14-5af394c8e6f3" />

[Back](#table-of-contents)

## Week 6
[Oct 6 – Oct 12, 2025]
- Wrote brief explanation for the [DFD Level 1](https://docs.google.com/document/d/1ZnNXTiLX3bXALCe2Ug8rojZ3RkSmjPB-2_YgaCqQyPA/edit?tab=t.0) (Page 3)
- Worked on [WBS](https://docs.google.com/document/d/1wPQgS1NMM9Jt1JUTCCPeJgyASQXQxxf_LkWZkoiAauA/edit?tab=t.0#heading=h.g6wbaqojg4lv) (2, 3, 12, 16)
- Learned Electron fundamentals
- Set up local Electron development environment
- Builded initial database schema
- Generated sample test data
- Reviewed PRs

<img width="1560" height="914" alt="4f852e3502eb5090a2cf0682501fcb45" src="https://github.com/user-attachments/assets/e3476168-756d-4b00-8c00-24c690b0018d" />

[Back](#table-of-contents)

## Week 7
[Oct 13 – Oct 19, 2025]
- Learned Electron fundamentals
- Fixed User File Upload (Issue #50)
- Reviewed PRs

<img width="1550" height="909" alt="60e39d7e1610d92e70b1879fedade30d" src="https://github.com/user-attachments/assets/c1e81205-cca3-430d-8943-19ed510e767b" />

[Back](#table-of-contents)

## Week 8
[Oct 20 – Oct 26, 2025]
- Completed zip parse function (Issue #62)
- Fixed existed bugs
- Reviewed PRs

<img width="1559" height="914" alt="506411721a7d673d8b1cf8572f6f0d18" src="https://github.com/user-attachments/assets/e2bd4959-d041-494f-af1c-7e7a16ab4236" />

[Back](#table-of-contents)

## Week 9
[Oct 27 – Nov 2, 2025]
- Completed user permission request module (Issue #22)
- Helped converting lauguage to Python
- Reviewed PRs

<img width="1558" height="914" alt="bd94c866cf799deb01f35359ab5a54ad" src="https://github.com/user-attachments/assets/6cd1f6a1-eac7-4a0b-9ff1-19f540dd202d" />

[Back](#table-of-contents)

## Week 10
[Nov 3 – Nov 9, 2025]
Last week, I implemented basic external module user permissions. When external support is enabled, users can choose whether to allow external modules to analyze their data or use it for other purposes(in future). Their selection is recorded in the config. However, since the previous default analysis mode was set to auto, this caused the system to always execute external module and request user permission when external support = true. This impacted convenience during development and polluted the config. Therefore, I set external support to false and plan to enable it only when testing external modules. This week, I discovered this approach still generated unnecessary operations. I realized I could set the default analysis mode to `local`, allowing `external support` to remain enabled by default while enabling explicit entry into external analysis via command-line instructions. I made this modification and added corresponding usage instructions to the README. Additionally, I observed that `_store_permission` previously read the config file each time, then read/wrote again within `update_preferences`. This meant users' decisions triggered redundant I/O operations. I addressed this by passing the existing Config directly into `_store_permission`. After modifying `external_permissions` internally, it now calls `save_config` once, reducing system read/write operations to a single pass. Next week, I plan to continue refining the external module. The current CLI lacks substantive endpoint detection, making it impossible to verify the feasibility of external target endpoints. I'm planning to complete this feature next week.

<img width="1550" height="910" alt="1b7b3c6db90ddd3cf4d90a0f3907d5ec" src="https://github.com/user-attachments/assets/fdc6fad6-da5f-4e55-9548-12ff01a68dbe" />

[Back](#table-of-contents)

## Week 12
[Nov 17 – Nov 23, 2025]
In Week 10, I improved system performance by refactoring the user config read/write and updating the external functionality. I originally planned to continully complete the external module this week, but I may not have enough time. Instead, I focused on revising and optimizing the existing database structure. During the migration from the old Electron codebase to Python, some functionality had been unintentionally forgot, such as file format validation and proper feedback for unsupported uploads, so I restored those missing features and fixed several scattered bugs and inconsistencies. I also refactored the storage module to improve it's structure and maintainability. Next week, I plan to continue reviewing the overall integrity of the project, and if time allows, I will aim to finish the complete external module implementation.

<img width="1553" height="910" alt="080647a95a177212c360942e8d74cc16" src="https://github.com/user-attachments/assets/9ec84235-d6ae-42ab-914c-b17a8d8228a8" />

[Back](#table-of-contents)

## Week 13
[Nov 24 – Nov 30, 2025]
Last week, I refactored some database related parts of the system, but the column name changes caused a few side effects, so I reverted them. This week, I implemented a previously forgotten WBS feature: chronological skills. It collects and organizes the skills that appear in projects, then outputs a summary and a timeline. With this, all 20 WBS features should now be implemented. I also reviewed the demo workflow and outputs, and I plan to make some refinements next week in preparation for recording the demo video.

<img width="1549" height="906" alt="a503080e56676a2cd653b71f8b47fbb8" src="https://github.com/user-attachments/assets/d993a031-f2a5-4209-8c47-f799094f1ba2" />

[Back](#table-of-contents)

## Week 14
[Dec 1 – Dec 7, 2025]
This week, as the final week of Term 1 and the end of Milestone 1, I first made thorough preparations for our presentation and demo recording. I then did some final optimizations to our project and added simple commands for some features to make it easier for my teammates to present them. The project is in good shape now, and we’ll keep working hard next term and for the upcoming Milestone 2.

<img width="1558" height="910" alt="55e9d0c3d05f48dc9c18d1025670ba2f" src="https://github.com/user-attachments/assets/29040154-6464-4653-8f1c-b5da3c7dffdc" />

[Back](#table-of-contents)


## Week 1 (M2)
[Jan 5 – Jan 11, 2026]
This week, I focused on fixing unclear and inaccurate contributor rankings within the same project. Previously, contributor rankings relied solely on commit counts, which lacked robustness and determinism. To address this, I decided to incorporate additional signals such as code reviews and lines changed, and to define a scoring formula to compute a contribution score. I introduced a new CLI command, capstone import-repo <url>, to connect to a GitHub repository and collect data for analysis. At present, this command simply packages the GitHub repository as a ZIP archive and reuses the existing ZIP analysis pipeline. As a result, it can theoretically also be used to import local file paths. However, this approach cannot capture GitHub-specific data such as reviews, line changes, pull requests, or issues. In future work, I plan to connect directly to GitHub using the GitHub API or access tokens instead of relying on ZIP-based local analysis. The implementation also merges commits made under different email addresses and usernames (including GitHub private emails) by matching on email, significantly improving the accuracy of contributor records. Next week, I will focus on resolving the remaining limitations, including fetching review, pull request, and issue data, as well as developing new features based on the updated WBS.

<img width="1551" height="910" alt="d099a90066b32f397ff91aa1f85a6442" src="https://github.com/user-attachments/assets/946121dc-d3fd-4e0a-846a-d8a06a087f08" />

[Back](#table-of-contents)


## Week 2 (M2)
[Jan 12 – Jan 18, 2026]
This week, I continued to build on last week’s work, focusing on fixing and improving the contributor ranking functionality. Last week, I attempted to package GitHub projects as ZIP files and reuse the original analysis pipeline, but I quickly identified several issues. First, the same contributors appeared under different email addresses, for reasons that were unclear, which significantly complicated contribution analysis. In addition, ZIP-packaged repositories do not include pull request, issue, or review data, making the contribution analysis incomplete and less reliable.

To address these problems, I switched to connecting directly to GitHub via APIs, retrieving project data using repository URLs and tokens. I initially used the REST/Search APIs and later introduced GraphQL to obtain merged pull request counts and completed issue counts for each contributor. The database schema was updated to add url and token fields to the project table; these fields are populated when a project is imported via URL and left empty for ZIP uploads. A new routing mechanism was implemented so that, during analysis, projects are processed differently depending on whether they were imported via ZIP or URL. URL-based projects use a separate weighting scheme and contributor workflow.

During this process, I found that extracting accurate line-change metrics was overly complex. Since it was not possible to reliably detect blank lines and dependency-related changes, even a very small weight could disproportionately affect contribution scores. As a result, I decided to remove this metric, reflecting a necessary trade-off in development. I also added a weight hash to detect changes before data loading, reducing redundant read/write operations, and improved the menu display and logic to make it more user-friendly.

Next week, I plan to fully finalize this contributor workflow and begin developing new features. Currently, URL-imported projects are not yet integrated with the original ZIP-based analysis pipeline. Aside from contribution analysis, both pipelines should share the same analysis flow, and I plan to complete this integration next week.

<img width="1556" height="910" alt="b453e044d181d21d9bc27701a5393547" src="https://github.com/user-attachments/assets/2210aff4-4031-474b-8eea-eb77dea48075" />

[Back](#table-of-contents)


## Week 3 (M2)
[Jan 19 – Jan 25, 2026]
This week, I completed the final phase of the contributor ranking work, bringing the feature to a fully polished state. When users upload a GitHub project via URL, the system now downloads the repository ZIP using the GitHub API, stores it as a temporary file, and then invokes the existing ZIP analysis pipeline. At the same time, the URL-specific contributor analysis is preserved and overrides the contribution component of the ZIP-based analysis. This approach does not rely on Git, significantly improving execution speed.

I also optimized the menu logic by reusing main menu logic within certain submenus and adding cancel and back-navigation options, making the interface more user-friendly. In addition, some summary output formats were adjusted accordingly. At this point, the contributor ranking functionality is considered complete.

Beyond this, I further refined the chronological skill timeline feature. The output display was significantly improved, and project selection was added for users. Previously, this feature analyzed all projects in the database by default, which was super limiting. It now returns a list of available projects for users to choose from, along with corresponding menu logic improvements and new tests.

Next week, I plan to refactor the database design. Currently, ZIP uploads and analysis are tightly coupled, meaning analysis starts immediately upon upload. I intend to separate these concerns by introducing a new table to store uploaded source information (ZIP or URL) independently, with analysis becoming an explicit, optional step. I will also begin developing new features next week.

<img width="1559" height="914" alt="e8da96c504674bc25c8c8e6e463453bd" src="https://github.com/user-attachments/assets/767342f6-0bde-4035-b5f1-5d0558a0bc70" />

[Back](#table-of-contents)


## Week 4 (M2)
[Jan 26 – Feb 1, 2026]
This week, I focused on improving file storage and deduplication in the system. I added two new database tables, files and uploads, to store file hashes, paths, and reference counts. On top of this schema, I implemented a file store that hashes each uploaded file, keeps a single canonical copy, restores the file if it is missing, and cleans up unreferenced (orphaned) files when they are no longer needed.

I then integrated this file store with both the ZIP analyzer and the API upload and skill routes. These components now record file_id and hash values instead of storing duplicate files, which reduces redundant storage and improves consistency across the system. To ensure correctness, I added unit tests covering schema creation, file deduplication, restoration of missing files, and orphan cleanup behavior.

During this work, I also identified an issue in the current database workflow where some data appears to be inserted multiple times. It seems that data may be written once in the zipAnalyzer and then written again when storing snapshots, resulting in duplicate records. Next week, I plan to investigate and fix this bug, and then begin development on new features.

<img width="1550" height="906" alt="52df745191a1b8479f91131401628d59" src="https://github.com/user-attachments/assets/7e8a0bce-496a-47fb-9e98-748e1b6a0eb9" />

[Back](#table-of-contents)

## Week 5 (M2)
[Feb 2 – Feb 8, 2026]
Last week, I implemented duplicate file detection by assigning hash values to each file and added an uploads table to record upload logs. This week, I made a major update to the resume module, changing the analysis from all projects in the database to a user-specific flow that analyzes a selected set of projects. To support this change, I introduced new users and user_projects tables in the database. However, due to an existing bug in the local ZIP analysis collaboration module that prevents correct collaboration analysis, these tables are currently intentionally limited to retrieving data only from GitHub URL–imported projects.

As a result, a new workflow was introduced. In the “Generate Resume Preview” process, the system first outputs a list of users, then the projects associated with the selected user, and finally a basic resume preview. However, several issues remain. Some users’ email addresses cannot be correctly retrieved from GitHub, so a feature allowing users to manually supplement their information needs to be added. In addition, PDF generation is currently not working due to unresolved dependency and engine issues, both on the API client side and the host environment. The current resume content and styling are also very minimal.

Finally, database tables such as resume_entry and resume_section may no longer be necessary, since resume generation no longer relies on stored resume content but is instead generated dynamically based on the user and their associated projects. The final result should be stored in a resumes table linked to user IDs and project IDs, and the resume customization feature will be redesigned accordingly. My goal for next week is to deliver a complete and functional resume module.

<img width="1550" height="906" alt="52df745191a1b8479f91131401628d59" src="https://github.com/user-attachments/assets/664a4ce0-ef0a-419d-99ef-336363362a97" />

[Back](#table-of-contents)

## Week 6 (M2)
[Feb 9 – Feb 15, 2026]
This week, I completed the core implementation of the resume generation and customization system at the CLI level. The system now supports reading users and their associated projects from the database and automatically generating an initial resume template using LaTeX. I expanded the users table to include additional fields such as full_name, phone_number, and city, and extended the “Manage user profile” submenu to allow users to edit and update personal information. The system also detects missing user data during resume generation and prompts for immediate completion.

In addition, I designed and implemented the resumes, resume_sections, and resume_items tables to establish a structured resume data model. Full customization is now supported, including add/edit/delete operations for sections and items, automatic PDF rebuilding after changes, and proper handling of sort order updates. Due to the deeply nested CLI menus, extensive testing was required to ensure stability. Next week, I aim to further refine usability and improve the overall workflow.

[Back](#table-of-contents)


