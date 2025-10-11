# Team-17 (COSC499 CAPSTONE SOFTWARE ENGINEERING PROJECT)

## Team Log Table of Content

- [Week 3 Team Log](#week-3-team-log)
- [Week 4 Team Log](#week-4-team-log)
- [Week 5 Team Log](#week-5-team-log)
- [Week 6 Team Log](#week-6-team-log)
- [Week 7 Team Log](#week-7-team-log)
- [Week 8 Team Log](#week-8-team-log)
- [Week 9 Team Log](#week-9-team-log)
- [Week 10 Team Log](#week-10-team-log)
- [Week 11 Team Log](#week-11-team-log)
- [Week 12 Team Log](#week-12-team-log)
- [Week 13 Team Log](#week-13-team-log)
- [Week 14 Team Log](#week-14-team-log)

## WEEK 3 TEAM LOG
(SEP 15 - 21, 2025)

### Recap of Milestone Goal - Week 3

In Week 3, the team has performed brainstorming on the requirements of the project, and consolidated them into the Project Requirements Report, which will be uploaded to the Canvas.

### Username and Student Name for Team 17

| Student Name | Github Username |
| ------------ | --------------- |
| Yuxuan Sun | ErenSun408 |
| Parsa Aminian | Pmoney1383 |
| Raunak Khanna | ronziekhanna |
| Shuyu Yan | yanshuyu280042 |
| Michelle Zhou | mltzhou |
| Nade Kang | kangnade |

### Completed Tasks Week 3

[Project Requirements Report](https://docs.google.com/document/d/1ZpG3Qs_pn9l6rbohNV1cGoopClzvmiS5qVH1lqKooFY/edit?tab=t.0)

### In Progress Tasks Week 3

Not Available for Week 3

### Test Report Week 3

Not Available for Week 3


## WEEK 4 TEAM LOG
(SEP 22 - 28, 2025)

### Recap of Milestone Goal - Week 4

In Week 4, the team has performed brainstorming on the Architucture Design Diagram, and Finished the Project Proposal, which will be uploaded to the Canvas.

### Username and Student Name for Team 17

| Student Name | Github Username |
| ------------ | --------------- |
| Yuxuan Sun | ErenSun408 |
| Parsa Aminian | Pmoney1383 |
| Raunak Khanna | ronziekhanna |
| Shuyu Yan | yanshuyu280042 |
| Michelle Zhou | mltzhou |

### Completed Tasks Week 4

[Architecture Design Diagram](https://docs.google.com/document/d/1fZNTCu4YO0CFwIvErlJ1agD4Zyxgh6q11CnjB686NzY/edit?usp=sharing)
[Project Proposal](https://docs.google.com/document/d/1yNkyeBqHvSgFAER2WQUW5GLdEmcIMknSAGh68UDHqCg/edit?tab=t.0)

### In Progress Tasks Week 4

Not Available for Week 4

### Test Report Week 4

Not Available for Week 4


## WEEK 5 TEAM LOG
(SEP 29 - Oct 5, 2025)

### Recap of Milestone Goal - Week 5

In Week 5, the team has discussed the basic construction of the app and completed the Level 0 and Level 1 DFD.

### Username and Student Name for Team 17

| Student Name | Github Username |
| ------------ | --------------- |
| Yuxuan Sun | ErenSun408 |
| Parsa Aminian | Pmoney1383 |
| Raunak Khanna | ronziekhanna |
| Shuyu Yan | yanshuyu280042 |
| Michelle Zhou | mltzhou |

### Completed Tasks Week 5

[Data Flow Diagram](https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/main/docs/design/L0%26L1%20DFD.png)

### In Progress Tasks Week 5

Not Available for Week 5

### Test Report Week 5

Not Available for Week 5


## WEEK 6 TEAM LOG
(Oct 6 - Oct 12, 2025)

### Recap of Milestone Goal - Week 6

In Week 6, our team reviewed all project artifacts, including every diagram, the requirements document, the Project Proposal, and the WBS, to ensure consistency and completeness. We finished setting up the local development environment and configured Docker for a reproducible build and run process. We also initialized the repository structure, documented setup steps, and agreed on coding conventions. Development began with the core logic: we wrote the initial, non-GUI modules and command line entry points, added basic tests to verify functionality, and confirmed that everything builds and runs successfully in Docker.

### Username and Student Name for Team 17

| Student Name | Github Username |
| ------------ | --------------- |
| Yuxuan Sun | ErenSun408 |
| Parsa Aminian | Pmoney1383 |
| Raunak Khanna | ronziekhanna |
| Shuyu Yan | yanshuyu280042 |
| Michelle Zhou | mltzhou |

### Completed Tasks Week 6

[All Diagram](https://docs.google.com/document/d/1ZnNXTiLX3bXALCe2Ug8rojZ3RkSmjPB-2_YgaCqQyPA/edit?tab=t.0)


[Requirements](https://docs.google.com/document/d/1ZpG3Qs_pn9l6rbohNV1cGoopClzvmiS5qVH1lqKooFY/edit?tab=t.0)

# explanation 

The document proposes a local first app that mines a user’s own files to help them understand and showcase their work history. It targets students and early professionals who want clear timelines, trends, and portfolio style summaries without sending data off the device. In scope are scanning chosen folders, classifying common file types, deduplicating with strong hashes, storing results in a local data store, and presenting dashboards plus simple exports. Users control what is scanned, can pause or resume, and see transparent previews and progress with errors surfaced. Typical use cases include presentations, reviews, resumes, and quick retrospectives.

Functionally, the system lets a user pick sources, crawls and classifies artifacts, builds searchable indexes and filters by time, type, project, and path, and produces insights like activity timelines and type distributions. Non functional goals stress fast setup, efficient and resumable scans, responsiveness, accessibility, and strong privacy and security. Data stays local with least privilege, encrypted storage using the operating system keystore, a localhost only API with per session tokens, secure deletion, and redaction of sensitive patterns in cached snippets. Maintainability expectations include straightforward developer setup, high automated test coverage, pinned dependencies, signed releases, and clear documentation.

For an initial milestone, the team should ship source selection, common type detection, hashing into SQLite with indexes, a live progress bar with pause and resume, basic dashboards for timeline and type distribution, search and filters, delete from index, a minimal local API, and CSV or JSON export with a preview. Success looks like accurate classification for most common types, a medium scan that completes within minutes on a typical laptop, common interactions that respond within a couple of seconds, and users reporting that the visualizations improve their understanding of their work. Key risks are privacy leaks, interruptions, and performance slowdowns, addressed by on device processing with redaction, checkpoint and resume, and resource caps with a light scan mode.

[Project Proposal](https://docs.google.com/document/d/1yNkyeBqHvSgFAER2WQUW5GLdEmcIMknSAGh68UDHqCg/edit?tab=t.0)
[System Architucture](https://docs.google.com/document/d/1fZNTCu4YO0CFwIvErlJ1agD4Zyxgh6q11CnjB686NzY/edit?tab=t.0)
WBS included in Project Proposal Section 5
### In Progress Tasks Week 6

Not Available for Week 6

### Test Report Week 6

Not Available for Week 6

## WEEK 7 TEAM LOG

## WEEK 8 TEAM LOG

## WEEK 9 TEAM LOG

## WEEK 10 TEAM LOG

## WEEK 11 TEAM LOG

## WEEK 12 TEAM LOG

## WEEK 13 TEAM LOG

## WEEK 14 TEAM LOG
