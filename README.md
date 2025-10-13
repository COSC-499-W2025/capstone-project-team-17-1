# Work Breakdown Structure
[Link to WBS](docs/Plan/wbs.md)


# DFD Level 1

<img width="1229" height="754" alt="image" src="https://github.com/user-attachments/assets/ee6a44e8-8e9b-46e8-8527-83f5b632fe49" /><br/>


The Level 1 DFD outlines how user-selected sources are processed to extract, analyze, and visualize digital artifacts.The process begins when a User selects sources, triggering the upload module to scan and detect files. These are processed by identifying file types, eliminating corrupt files, and extracting information. During this stage, the system will record an error log for any unreadable or corrupted files in the logs database for troubleshooting.

Processed files are categorized and metrics are derived. These metrics are saved in the database and then passed to the visualization module to create dashboard/portfolio reports for the user.

Additionally, users are able to search, filter, and save generated portfolios in the database. This allows them to retrieve/export for external use whenever they desire. All actions are tracked through logs. The data flow concludes with the final outputs returned to the user, completeing a clear and transparent user-controlled cycle.


# system_architecture_design
<img width="1617" height="1074" alt="image" src="https://github.com/user-attachments/assets/38a4aacd-d73c-4b7a-a808-a95611492823" /><br/>


The document proposes a local first app that mines a user’s own files to help them understand and showcase their work history. It targets students and early professionals who want clear timelines, trends, and portfolio style summaries without sending data off the device. In scope are scanning chosen folders, classifying common file types, deduplicating with strong hashes, storing results in a local data store, and presenting dashboards plus simple exports. Users control what is scanned, can pause or resume, and see transparent previews and progress with errors surfaced. Typical use cases include presentations, reviews, resumes, and quick retrospectives.

Functionally, the system lets a user pick sources, crawls and classifies artifacts, builds searchable indexes and filters by time, type, project, and path, and produces insights like activity timelines and type distributions. Non functional goals stress fast setup, efficient and resumable scans, responsiveness, accessibility, and strong privacy and security. Data stays local with least privilege, encrypted storage using the operating system keystore, a localhost only API with per session tokens, secure deletion, and redaction of sensitive patterns in cached snippets. Maintainability expectations include straightforward developer setup, high automated test coverage, pinned dependencies, signed releases, and clear documentation.

For an initial milestone, the team should ship source selection, common type detection, hashing into SQLite with indexes, a live progress bar with pause and resume, basic dashboards for timeline and type distribution, search and filters, delete from index, a minimal local API, and CSV or JSON export with a preview. Success looks like accurate classification for most common types, a medium scan that completes within minutes on a typical laptop, common interactions that respond within a couple of seconds, and users reporting that the visualizations improve their understanding of their work. Key risks are privacy leaks, interruptions, and performance slowdowns, addressed by on device processing with redaction, checkpoint and resume, and resource caps with a light scan mode.
