# DFD Level 1

<img width="1229" height="754" alt="image" src="https://github.com/user-attachments/assets/ee6a44e8-8e9b-46e8-8527-83f5b632fe49" /><br/>


The Level 1 DFD outlines how user-selected sources are processed to extract, analyze, and visualize digital artifacts.The process begins when a User selects sources, triggering the upload module to scan and detect files. These are processed by identifying file types, eliminating corrupt files, and extracting information. During this stage, the system will record an error log for any unreadable or corrupted files in the logs database for troubleshooting.

Processed files are categorized and metrics are derived. These metrics are saved in the database and then passed to the visualization module to create dashboard/portfolio reports for the user.

Additionally, users are able to search, filter, and save generated portfolios in the database. This allows them to retrieve/export for external use whenever they desire. All actions are tracked through logs. The data flow concludes with the final outputs returned to the user, completeing a clear and transparent user-controlled cycle.
