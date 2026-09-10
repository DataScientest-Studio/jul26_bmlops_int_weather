Sep 10, 2026

## **jul26\_bmlops\_int\_weather- Internal**

Invited [Gabriel Marchesan Almeida](mailto:gabriel@marchesan.me) [jonathanvints@gmail.com](mailto:jonathanvints@gmail.com) [ziad.hemidi94@gmail.com](mailto:ziad.hemidi94@gmail.com) [thomas.maisch1996@web.de](mailto:thomas.maisch1996@web.de)

Attachments [jul26\_bmlops\_int\_weather- Internal](https://calendar.google.com/calendar/event?eid=XzZ0Mmo4Y2kxOGwxM2ViYTQ4ZDFqYWI5azY1MjM4YjlwNzRvM2ViYTY3MHE0NmM5ZzZoMTNhaDltNmMgZ2FicmllbEBtYXJjaGVzYW4ubWU)

Meeting records [Transcript](https://docs.google.com/document/d/17-D3ctuqSvCZ570JhlnMc3fMX58p4-gdmygnDogM76w/edit?usp=drive_web&tab=t.uhntbsvqct29) 

### **Summary**

Training updates and Docker automation and workflow planning

**Training and Docker Automation**  
Participants discussed training module progress and Docker configuration improvements. Agreement reached on moving trainer functionality to an API endpoint.

**Pipelines and Security Strategy**  
Teams reviewed Airflow orchestration and data versioning plans. Focus shifted to securing APIs and expanding unit tests.

**Documentation and Presentation Plans**  
Groups evaluated documentation methods and streamlined presentation strategies. Decision made to prioritize a live demo using Streamlit.

### **Decisions**

## Needs Further Discussion

* **Airflow trainer invocation mechanism** The team discussed whether Airflow should trigger training via API calls or direct code execution and deferred final implementation pending further investigation and mentor feedback.

## Aligned

* **API-only model training execution** The team aligned to remove offline training from the makefile and execute model training exclusively via API calls rather than automatically on Docker container startup.

* **Container-specific dependency requirements files** The team aligned to maintain dedicated requirements files for each Docker container rather than a single root requirements file to keep images slim and maintainable.

### **Next steps**

- [ ] \[Gabriel Marchesan Almeida\] Split Trainer: Split the trainer component into multiple separate containers to improve modularity. Execute this change to simplify the connection process.

- [ ] \[Gabriel Marchesan Almeida\] Update Makefile: Update the Makefile to disable standalone training and ensure the trainer only operates via API calls. Remove any manual execution paths.

- [ ] \[Thomas\] Develop Airflow: Develop the Airflow DAG to orchestrate training phases. Create an initial draft to establish the primary workflow.

- [ ] \[Ziad Hemidi\] Research Versioning: Research open source tools for data versioning with MLflow. Identify the best method to track datasets and models effectively.

- [ ] \[Gabriel Marchesan Almeida\] Add Docker Workflow: Add a Docker build workflow to the GitHub repository. Ensure the CI process verifies image builds automatically.

- [ ] \[Gabriel Marchesan Almeida\] Investigate Docker Hub: Investigate Docker Hub for registry and private team space functionality. Determine if the platform supports internal team sharing.

- [ ] \[Gabriel Marchesan Almeida, Thomas\] Implement Security Tests: Implement security tests for authentication and authorization. Review existing test code and incorporate additional validation scenarios.

- [ ] \[Gabriel Marchesan Almeida\] Prepare Documentation: Prepare a first draft of the technical documentation. Include the project architecture and phase descriptions in the README or wiki.

- [ ] \[Ziad Hemidi\] Implement NGINX: Configure NGINX to handle API requests. Enable features such as load balancing and request rate limiting.

- [ ] \[Jonathan\] Track Reports: Track generated reports and datasets using MLflow. Maintain versioning and initiate model retraining when data requirements change.

- [ ] \[Gabriel Marchesan Almeida\] Share Email: Share the email from Ha in the chat or provide a screenshot for reference.

- [ ] \[Gabriel Marchesan Almeida\] Report Progress: Finish the training modules and send a message with the achievements by early next week.

- [ ] \[Gabriel Marchesan Almeida\] Share Script: Create a GitHub repository for the script that downloads training materials and share the link with the team.

- [ ] \[Ziad Hemidi\] Configure Vault: Research the Supabase vault to store API keys and credentials, then implement this setup for security.

- [ ] \[Jonathan, Ziad Hemidi\] Configure Containers: Review course files to identify and implement the necessary initialization containers for services like MLflow and MinIO.

- [ ] \[Jonathan\] Optimize Docker: Refactor Docker requirements files to ensure each image remains lightweight by including only necessary dependencies.

### **Details**

* **Personal Updates and Training Status**: The team held an informal check-in where Jonathan shared an update regarding their travels in Faro, Portugal ([00:01:14](?tab=t.uhntbsvqct29#heading=h.vowxoh9xtbsq)). Participants discussed their progress through the training modules, noting that the "Data Scientist" path exams were significantly more time-consuming than the two-hour estimates suggested in the course material ([00:03:11](?tab=t.uhntbsvqct29#heading=h.sjz59642gus4)).

* **Docker and Trainer Automation**: Ziad expressed concerns regarding the current Docker configuration, which forces the trainer to ingest data and train every time the container starts. Ziad proposed moving the trainer functionality to an API endpoint, allowing it to be triggered by Airflow rather than running automatically upon startup ([00:08:21](?tab=t.uhntbsvqct29#heading=h.3tw3f1apr32e)). Gabriel agreed to modify the configuration to enable API-based training and to split the trainer into multiple containers for different phases ([00:10:27](?tab=t.uhntbsvqct29#heading=h.emkt2fvf574r)).

* **Airflow Implementation**: The team discussed the orchestration of the project phases using Airflow. Thomas committed to starting the drafting of the Directed Acyclic Graph (DAG) to define the workflow, with plans to brainstorm the initial entry points and overall structure with the rest of the team ([00:13:30](?tab=t.uhntbsvqct29#heading=h.9r39oudtc3ry)).

* **Data Versioning Strategy**: Ziad requested clarity on data versioning after receiving conflicting guidance regarding DVC (Data Version Control). Ziad plans to research using MLflow for model registry and tracking to ensure proper versioning ([00:14:30](?tab=t.uhntbsvqct29#heading=h.bqy1gv9bv06d)). Gabriel mentioned the potential use of minio as a local, open-source alternative to S3 bucket storage, which was suggested during previous training discussions ([00:15:24](?tab=t.uhntbsvqct29#heading=h.jbpp0iv8tqly)).

* **CI/CD and Optional Pipeline Components**: Ziad confirmed that linter and unit test workflows are already configured in GitHub for merges to the main branch. Gabriel took responsibility for adding the Docker image build workflows, noting that they would explore deployment to Docker Hub to showcase the project to the jury if time permits, taking advantage of the available free tier ([00:16:19](?tab=t.uhntbsvqct29#heading=h.ehtrvyjsugxn)).

* **Security and Load Balancing**: The team discussed implementing Nginx to handle HTTPS routing and load balancing ([00:20:00](?tab=t.uhntbsvqct29#heading=h.howsknvvjjmj)). Ziad and Thomas discussed the need for API authentication and IP rate limiters to prevent security issues such as DDoS attacks ([00:20:58](?tab=t.uhntbsvqct29#heading=h.atq421oq0ohz)). Thomas will look into the API authentication, while the team will collectively integrate Nginx configurations ([00:20:00](?tab=t.uhntbsvqct29#heading=h.howsknvvjjmj)).

* **Unit Testing and Optional Tasks**: Gabriel and Thomas agreed to expand upon the existing unit tests, focusing on validating security, authorization, and handling of incorrect inputs ([00:21:57](?tab=t.uhntbsvqct29#heading=h.ic4r3ozea9az)). The team decided to prioritize mandatory project requirements before addressing optional tasks like Kubernetes, which they currently have no experience with and will defer to a later date ([00:23:06](?tab=t.uhntbsvqct29#heading=h.xgq2piceeye5)).

* **Phase 3 Documentation**: Gabriel highlighted the requirement for a README file for Phase 3 ([00:27:34](?tab=t.uhntbsvqct29#heading=h.rdq10hx524ie)). Ziad suggested using a GitHub Wiki for more structured, in-depth documentation, while the group considered incorporating technical documentation directly into the Streamlit presentation to maintain a cohesive demonstration ([00:28:26](?tab=t.uhntbsvqct29#heading=h.fpwwyae0bbj7)).

* **Presentation Strategy**: To avoid the time overruns experienced in previous presentations, the team agreed to streamline their approach. They plan to focus the presentation on a live demo using Streamlit, supplemented by a brief architecture overview, with plans to conduct a dry run to ensure they remain within time constraints ([00:30:25](?tab=t.uhntbsvqct29#heading=h.563rjofxjv0c)).

* **AWS Training and Certification**: Participants discussed the AWS training modules, with Gabriel noting their plan to focus on mandatory training first before registering for future AWS certification courses ([00:33:16](?tab=t.uhntbsvqct29#heading=h.owrygm4jw9su)) ([00:34:57](?tab=t.uhntbsvqct29#heading=h.5kgczjzyusk)). Thomas clarified that the four-day AWS training program includes courses for both the Certified Solutions Architect and Certified Cloud Practitioner certifications ([00:34:08](?tab=t.uhntbsvqct29#heading=h.ubfsxcbl85mi)) ([00:36:48](?tab=t.uhntbsvqct29#heading=h.9iv01zdx6otw)).

* **Training Automation Script**: Gabriel is developing a script using Playwright to download training materials for offline access ([00:37:38](?tab=t.uhntbsvqct29#heading=h.y64k55qki6mu)). Gabriel plans to create a GitHub repository for this script, allowing the team to collaborate and utilize the resource, which will help them manage information more efficiently ([00:38:22](?tab=t.uhntbsvqct29#heading=h.r1pa9rvhvlan)).

* **Supabase Vault and Security Credentials**: Ziad proposed utilizing the Supabase Vault to manage and store API keys and credentials securely ([00:42:08](?tab=t.uhntbsvqct29#heading=h.q4am6044bd5m)). The team discussed using temporary, rotating tokens instead of permanent credentials to adhere to security best practices, and Ziad plans to investigate the integration of the Vault into the project workflow ([00:43:05](?tab=t.uhntbsvqct29#heading=h.vj50xgllx6ze)).

* **Docker Infrastructure and Requirements**: Jonathan asked about the presence of multiple requirements files for different Docker images ([00:44:52](?tab=t.uhntbsvqct29#heading=h.3fvplamkz7q4)). The team agreed that maintaining separate, minimal requirements files is a best practice to ensure Docker images remain lean, portable, and easier to maintain ([00:45:47](?tab=t.uhntbsvqct29#heading=h.fnc443vh2qzb)).

* **MLflow Architecture**: Ziad clarified that the MLflow infrastructure should include specific containers for the server and an initialization process to set up experiments and structures efficiently ([00:47:40](?tab=t.uhntbsvqct29#heading=h.b6hgafk2pqyg)). The team agreed to reference the course materials to adopt standard practices for these initialization containers ([00:48:33](?tab=t.uhntbsvqct29#heading=h.rghr1m262t2n)).

*You should review Gemini's notes to make sure they're accurate. [Get tips and learn how Gemini takes notes](https://support.google.com/meet/answer/14754931)*

*How is the quality of **these specific notes?** [Take a short survey](https://google.qualtrics.com/jfe/form/SV_5bXzKQfylMIhSXc?confid=GbOLBRjqy1zg-rTxwG7gDxITOBEBMgUIigIgABgDCA&detailLevel=standard&hasImages=False&entryPoint=footerMain&isGoogler=False) to let us know your feedback, including how helpful the notes were for your needs.*