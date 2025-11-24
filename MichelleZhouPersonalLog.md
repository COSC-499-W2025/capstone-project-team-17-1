# COSC 499 TEAM 17 Personal Log - Michelle Zhou 27227602

## Table of Contents

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
- Met with team and collaborated on step 1 + 2 of matching job description to user projects feature
- Started working on task #89 Step 3 Extract Company-Specific Qualities

### Next Week:
- Collaborate with team to finish job description matching feature (last feature)
- Finalize code for Milestone #1
- Convert outputs to match resume-style writing for M1 demo
- Prepare for M1 presentation
