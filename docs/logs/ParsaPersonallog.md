# COSC499 Team 127 Personal Log - Parsa Aminian (41202862)

## Week 3 Personal Log [Sept 15 – Sept 21, 2025]

This week I contributed to multiple parts of our project’s requirement specification document:

### Non-Functional Requirements
- Helped define performance expectations, such as efficiency and reliability of artifact mining.  
- Specified scalability goals (e.g., system should handle large catalogs and use CPU cores efficiently).  
- Contributed to usability requirements including accessibility, onboarding, and responsiveness.  
- Outlined key security measures (encryption, least-privilege access, secure deletion).  
- Added maintainability standards such as automated test coverage, documentation updates, and CI checks.  
- Ensured privacy considerations were included (local-only analysis, redaction of sensitive data, idle lock).  

### Data Requirements
- Specified supported file types (code, text, PDF, images, audio, video, design files).  
- Defined metadata fields to capture (path, name, size, timestamps, owner).  
- Added hashing/deduplication requirements using SHA-256 for integrity checks.  
- Defined storage formats (SQLite or JSON with indexing).  
- Included data quality checks and conflict reporting.  
- Outlined export formats (CSV/JSON) and data volume limits (≥5 million artifacts).  

### Technical Requirements
- Proposed use of SQLite or JSON with write-ahead logging for local storage.  
- Defined cross-platform build requirements (Windows, macOS, Linux).  
- Added support for Git repository metadata extraction.  
- Specified JSON API on localhost for modular design.  
- Required metadata extraction from media files (dimensions, duration, codec).  
- Defined Unicode/path handling requirements.  
- Proposed concurrency model using worker pools with back-pressure.  
- Specified configuration handling through user settings and environment variables.  

### Reflection
This week I gained a stronger understanding of how detailed requirements shape the foundation of a project. I learned the importance of balancing **functional scope with non-functional qualities**, and how technical and data requirements ensure the system is both practical and scalable. Writing these sections gave me experience in thinking not just about what the system should do, but how it should behave under real-world conditions. 

---

## Week 4 Personal Log [Sept 22 – Sept 28, 2025]

This week I focused on moving our project forward through early design and planning deliverables:

### Architecture Design Diagram
- Created the first draft of our system’s architecture design diagram.  
- Outlined the key components including data ingestion, metadata extraction, storage, and user interface.  
- Added communication flows between modules to show how data moves through the system.  
- Ensured the diagram reflected scalability and modularity by separating concerns into distinct layers.  
- Highlighted potential integration points for APIs and external tools.  

### Project Proposal
- Contributed to writing the project proposal document.  
- Drafted sections describing the project goals, motivation, and target user groups.  
- Wrote about the problem being solved and why artifact mining is valuable for grad students and early professionals.  
- Helped define the scope of the system and its expected impact.  
- Reviewed the draft with the team to align expectations and refine language.  

### Reflection
This week strengthened my skills in **high-level system thinking** and **project framing**. Building the architecture diagram helped me think about how the pieces of our project will work together in practice, while writing the proposal forced me to clearly articulate our objectives and the value of the system. Both tasks gave me insight into how design and documentation set the stage for smooth implementation in later phases.
