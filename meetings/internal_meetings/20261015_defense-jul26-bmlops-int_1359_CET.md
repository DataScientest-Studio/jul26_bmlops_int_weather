2026-10-15

## **defense-jul26-bmlops-int**

**Attendees:** Gabriel Almeida, Liora NoReply

### Transcript

Meeting: Defense - JUL26 BMLOPS INT
Date: 2026-10-15 13:59 - 2026-10-15 15:51
Participants: Gabriel Almeida <gabrielmarchesan@gmail.com>, Liora NoReply <noreply@datascientest.fr>
Link: https://sparkmailapp.com/dpl/bl?token=QTpwZXJzb25hbC10ZWFtO0lEOjBmOGYzMjY5LTg4ZTAtNDVlMC1iNTJlLWY3Zjdi%0D%0AZmNmMmUzN0BTcGFyazsyOTI3Mzc1MzYy

── Summary ─────────────────────────────────────────────────────────────
  Three teams demonstrated end-to-end MLOps prototypes; their strongest outcomes were controlled model promotion, monitoring, and clear production-readiness gaps.
  
  ### Key Points
  
  #### Industrial Anomaly Detection
  
  The team delivered a complete prototype for automated visual quality inspection.
  
  * Ayub, Mohammad, and Pavel built an unsupervised convolutional autoencoder for bottle, wood, and pill images, training only on normal examples.
  * Their seven-service Docker Compose system linked PostgreSQL metadata, FastAPI, Airflow, MLflow, Streamlit, Prometheus, and Grafana; Airflow simulated new data by releasing three batches hourly.
  * The team set the anomaly threshold at the 95th percentile and promoted a champion model only when its ROC AUC strictly exceeded the current champion.
  * The jury praised the project’s completeness and demo, but advised shortening the presentation and reducing repetition between slides and Streamlit.
  * The presenters acknowledged that the prototype lacked production-ready security and data versioning; DVC had been considered but was not completed.
  * The jury recommended investigating drift before retraining, then evaluating model performance on fresh data and retraining only when evidence warrants it.
  
  #### Rakuten Product Classification
  
  The team prioritized reproducible training, guarded promotion, and operational monitoring.
  
  * Benjamin, Christopher, Romil, and Sandeep built a multimodal classifier for 27 product categories using 84,916 products, titles, descriptions, and images.
  * They versioned the raw CSVs and image folder with DVC, tracked model runs and data hashes through MLflow, and stored metadata and predictions in PostgreSQL.
  * Training processed 3,000-row batches, with 2,400 training rows and 600 test rows; each CPU run took 141–167 seconds.
  * Airflow scheduled training every two days; a new model had to beat the incumbent on the same 600-row comparison set before promotion.
  * The team used Evidently to flag text-classifier drift above 0.55 and numeric-column Wasserstein distance above 0.1; it acknowledged that the comparison used slices of a static corpus, not live traffic.
  * The demo showed a low-confidence misclassification flagged below 0.6, while a newly trained model was rejected because it did not outperform production.
  
  #### Weather Prediction Pipeline
  
  The team connected delayed outcome evaluation to selective retraining and deployment safeguards.
  
  * Gabriel, Thomas, Jonathan, and Ziad predicted next-day rain in Australian stations using Kaggle history (145,000 rows, 2007–2017) supplemented by Open-Meteo data.
  * Because only 23% of Australian observations showed rain, the team rejected accuracy as its principal measure and required recall of at least 0.75 plus improved ROC AUC for champion promotion.
  * A daily Airflow pipeline fetched and evaluated data, while a separate unscheduled pipeline retrained only when monitoring requested it; at least 30 labeled predictions were required to calculate real recall.
  * Evidently treated feature drift as a warning and triggered retraining when actual recall fell below 0.75; the team used a five-year training window and 90-day evaluation period.
  * The Singapore test exposed geographic sensitivity: ROC AUC fell from approximately 0.87 to 0.70, and retraining on Singapore data recovered performance only to 0.70.
  * The team demonstrated HTTPS, authentication, per-IP limits of 10 requests, training limits of one request per second, CI tests, and monitoring; the jury recommended clearer privacy and GDPR disclosures before public deployment.
  
  #### Program Completion Guidance
  
  The organizer closed the defenses and redirected participants toward certification requirements.
  
  * The organizer congratulated all three teams and invited participants to contact the organizer or their program manager through Slack for support.
  * Participants must complete at least seven of the ten mandatory exams to finish the training; the organizer expected to check completion around the following week.
  * Participants who complete the requirement retain access to the learning platform for revisiting courses and optional material.
  
  ### Action Items
  
  #### All participants
  
  * Complete at least seven of the ten mandatory exams.

── Transcript ──────────────────────────────────────────────────────────
  00:09 Recording in progress.
  
  00:09 And hello everyone.
  
  00:13 Hi, Kaelan.
  
  00:14 Hello.
  
  00:15 Hello.
  
  00:16 Hi.
  
  00:19 Hello.
  
  00:21 Hi, everyone. Welcome to your defense.
  
  00:24 As you probably already saw in the description of this invitation, there is three groups that are going to present their project today.
  
  00:35 So we do have a specific order. We can also adjust if there is any constraint, but we'll try to stick with the order that were given in the description of this meeting, which was, for the first group, the anomaly detection group.
  
  00:35 Then the Rakuten e-commerce platform group and then the last group will be the weather prediction group.
  
  00:35 So, I'm not sure why I can see the list of people that should be part of each group, but I will try to find it.
  
  01:31 But let me just, for the first group, is everyone already in the meeting? I don't see anyone in the Yes, we are here.
  
  01:31 We are here.
  
  01:43 Hello.
  
  01:43 Great.
  
  01:44 Hello, and how much people are you?
  
  01:44 We are three.
  
  01:44 Three.
  
  01:51 So Pavel is here and also Mohammad is here.
  
  01:51 Okay, great.
  
  01:55 Well, you can try start by setting up everything, starting sharing your screen and when you're ready, we are going to listen to you.
  
  01:55 Well, for the first group, the jury will be composed of Killfen who is already there, and myself.
  
  02:20 And for the last two groups, Sebastian will actually join us later to be part of the jury for the last two groups.
  
  02:31 And well, great.
  
  02:31 If three of you are ready, you can start whenever you want.
  
  02:40 I will just set up a small timer, it will be showed on my in my camera, but just not put any pressure on you, just to have an idea of how much time you take for the presentation.
  
  02:55 Let me just set up the timer.
  
  02:55 Okay, so you already know the rules, 20 minutes of presentation then 10 minutes of questions from the jury.
  
  02:55 Well, great.
  
  03:09 I'm ready.
  
  03:09 I don't know if you all three are ready, but if you are, you can start presenting and we are listening.
  
  03:14 If Mohammad and Pavel give me the green light, then I will start immediately.
  
  03:14 Mohammad, Pavel, are you ready also?
  
  03:14 Yes, we are.
  
  03:28 Start.
  
  03:29 Yes.
  
  03:34 So hello everyone.
  
  03:34 Today we will present to you the result of our project, namely industrial image anomaly detection.
  
  03:34 So here we use the convolutional autoencoder and the machine learning operation pipeline.
  
  03:52 So the members of the our team is Mohammad, Pavel, and me, Ayub.
  
  03:52 So we start with the agenda of our presentation.
  
  03:52 So here I will present first of all, team contribution, system architecture, anomaly detection problem, and the architecture of the convolution convolutional autoencoder, and then how we split the data set and batches, and how we use tensor flow trading, machine ml flow for tracking and then for evaluation.
  
  05:09 Mohammad will present Docker Compose, post PostGRE SQL, batch release, airflow orchestration, and fast API and interface inference, and Pavel will present how we select selected the machine the MLflow champion models, Streamlits, and Spotlight.
  
  05:09 He will do a with Streamlit a demo, and then he will present the data drifting and monitoring with the Prometius and Grafna.
  
  05:30 So here, I will present the team contribution.
  
  05:30 So me, I am Ayub Hamdoun.
  
  05:30 So, this is my contribution to the project.
  
  05:30 So I created the convolutional neural network, the convolutional autoencoder, the model.
  
  05:55 So it is stored in the training points by files.
  
  05:55 And then I did the model training and MLflow experiment tracking.
  
  05:55 So we did several training and we saved the metrics and the artifacts.
  
  05:55 And then I did also the data splitting and incremental batch automation, because in airflow, we want to orchestrate that simulate that's every time a new data is coming.
  
  06:45 So we splitted the whole data sets in three batches and every time a new data is coming.
  
  06:59 So we retrain the model, and then after that we select the model champion.
  
  06:59 And then I did also MLflow and Airflow integration and workflow documentation.
  
  07:16 Mohammad did the project initiation and core structure of the project.
  
  07:16 And then also the database import and pipeline, training prediction API and basics test.
  
  07:16 And then he created also the structure of the Docker microservice and schedule the Airflow training.
  
  07:16 And Path, he did the MLflow model registry and champion selection and Prometheus and Grafana monitoring, and then he creates also the demo with Streamlits.
  
  07:16 And then also data set gave provence and read me updates.
  
  08:07 So I will start with the data for this project.
  
  08:07 We have a huge data set, but we restrict ourselves only for on three categories, namely the bottles, and then the pills, and those.
  
  08:07 The aim of the project is the quality insurance before so we have to detect the anomalies within the products using the convolutional autoencoder.
  
  08:59 So before shipping, so the of the project of the product, so we have to analyze the images for bottle, pills, tablets, and also we'd, and then detect the anomalies.
  
  08:59 So here the system architecture.
  
  08:59 So we use Docker Compose to deploy and manage all our microservice in separate containers, allowing them to communicate with each others, and also and for this PostgresSQL, it stores image data, and Airflow automates the training process, so it triggers the training process.
  
  10:00 Fast API connects the different components, Tensorflow, so our CAE model, it trains the model and the data while MLflow track
  
  10:00 Experiments and also make model registry and champion selection. And for data drift and monitoring, we used Grafana and Prometheus and for the demo, we use Streamlit.
  
  10:26 So, here the This is the structure of our program. As input, we have the data set, we have only three categories, bottle, wood, and pills.
  
  10:42 In process, we separate normal and defective image, and copy data in project structure, and outputs training only normal images, and for tests, normal and defective images.
  
  10:55 It's our model, it's unsupervised learning, it's training only on good data.
  
  11:06 But it must classify the defect and non defect parts, and I will come later how we do it.
  
  11:16 So as input, we have images with this dimension, and then it goes through to encoder faces for each layer for each encoder layer, we have a convolutional layer and then and max pooling layer.
  
  11:31 We do it twice, and then in the latent space, we have compressed image size, and in the decoder, we have the reconstruction, and then the output is the same size and as the inputs.
  
  11:47 And how we score the anomaly.
  
  11:51 So, after the reconstruction, we calculate a reconstruction score, and then if this score is below a threshold, then the image is classified as anomaly.
  
  12:10 It's if above, then it's a normal image.
  
  12:16 So, here for the data preparation and incremental batches, as I said, so we split the data to three batches, and every time we train the we simulate in airflow that with the tags that's the data is every hour is a new data is coming.
  
  12:38 So for the first run, it will train the model.
  
  12:42 So I will specify something for the model. It's trained only on one category.
  
  12:49 So here we have three categories. That means we have three models.
  
  12:54 And for each category, we split the data to three batches, and for each run, it's for example, first run, the model is trained only on the first batch.
  
  13:08 Second run on the first and the second batches, and in the last run, on all batches.
  
  13:18 So, here during the training,
  
  13:23 So the in the training face, we have inputs only normal images.
  
  13:30 So for the splits, we have 80% training, 80% validation, and then here, it goes through the convolutional auto encoder, and then we calculate the threshold with choose upper percentile of 95%.
  
  13:46 And then the output we have the test metrics and airflow run.
  
  13:55 So for log parameters and the metrics, we have category, epox, available batches, training and validation loss, and then we have as metrics, we have Roc and F1 metric.
  
  14:13 So, those are the results of the training.
  
  14:19 So for each category, we have the Roc, area under the Roc, curve, and then also the F1 score.
  
  14:37 Now, Muhammad will continue presentation with the docker compose parts.
  
  14:45 I will stop the sharing and Muhammad will continue.
  
  14:46 Thank you. Are you ready for your presentation? One second, please.
  
  15:32 Can you see the slides? Yes.
  
  15:38 Okay. Now I will explain how we deploy our AML ops system using Docker compose.
  
  15:47 Our project consists of seven services: Postgres SQL, AML flow, FAST API, Airflow, Streamlit, Prometheus, and Grafana.
  
  15:56 We use Docker compose to build, start, and manage these services together on our machine.
  
  16:04 Each service runs in its own container and has specific responsibility.
  
  16:10 So, the services communicate through an internal docker network using service names.
  
  16:16 We also use persistent storage to keep our database and experiment data even when containers are restarted.
  
  16:26 The main advantage of this approach is that we can deploy our complete ML ops system in consistent and reproducible way.
  
  16:36 Now, let's look. The next slide is about Postgres SQL.
  
  16:50 The Postgres SQL acts as the central database for image metadata and batch management.
  
  17:00 An important point is that PostgreSQL does not store the actual image pixels.
  
  17:08 The images are stored as files on our local machines.
  
  17:13 Instead, PostgreSQL store information, metadata, such as the image path, category, data set, split, batch ID, and availability status.
  
  17:26 One important field is the is available flag.
  
  17:31 It tells our system whether a training batch has been released.
  
  17:36 FAST API uses Postgres SQL to manage batch releases, while the training process queries the database to find the available training image.
  
  17:53 And we also use Postgres SQL to store prediction logs and data drift reports.
  
  18:02 Next, I will explain how we simulate the arrival of new data.
  
  18:13 In a real industrial environment, new images arrive over time.
  
  18:20 Since our data set is already stored on our machine, we simulate this process using incremental batch releases.
  
  18:29 Initially, all three training batches are marked as unavailable in Postgres SQL, and Airflow send a request and the FAST API then finds the next local batch and changes its flag, the is available flag to true.
  
  18:54 The API returns a released batch ID and the number of images.
  
  19:01 After a successful release, the training workflow can continue using the all available training data as Ayub explained.
  
  19:12 When all three batches have been released, there is no new batch to process, so the training workflow is skipped.
  
  19:21 This prevents unnecessary re-training.
  
  19:27 Now let's look at Airflow, how we orchestrate and automate our training.
  
  19:37 Our training tag is scheduled to run every hour.
  
  19:41 It starts with as mentioned with task release next batch, which follows the process I explained.
  
  19:52 If a batch is successfully released, Airflow trigger the training task for Battle, Wood, and Pill in a sequence.
  
  20:00 Airflow manages to execute
  
  20:00 Execution order while Fast API performed the model training.
  
  20:10 So, if, for example, no new batch is available, Airflow skips the downstream training tasks.
  
  20:10 This gives us a controlled and automated training process and next step, Batcher.
  
  20:51 Next, I jump maybe.
  
  20:55 Fast API.
  
  20:55 Sorry.
  
  20:55 So the next step is Fast API.
  
  20:55 Fast API acts as a central communication layer between all services.
  
  21:15 So instead of allowing airflow of streaming to execute internal python functions directly, we expose HTTP requests.
  
  21:32 For example, airflow use endpoint to manage data release and trigger model training.
  
  21:36 Streaming to use, for example, the predict and predict upload to request prediction for an image.
  
  21:56 We also provide endpoints to check in, patch, status, generating data, drift reports, and exposing monitoring metrics.
  
  21:56 So this separation makes our architecture more modular, maintainable, and resilient.
  
  21:56 Now let's follow.
  
  22:20 So, finally, I will explain how our system
  
  22:20 Sorry, I have a problem with it.
  
  22:31 I will explain how our system performs anomaly detection during inference.
  
  22:31 First, the user selects a category such as puzzle, wood or pill and provide an image through Streamlit.
  
  22:31 Fast API receive the request and load the corresponding champion model from the MLflow model registry. [2:50:5] So as explained, the image is resized and normalized using the same processing as during training,
  
  23:10 And our CIA reconstruct the image and calculate the anomaly score based on the reconstruction difference.
  
  23:10 So we compare this score with a predefined threshold, if the score is greater than the threshold, the image is classified as anomalous.
  
  23:35 Otherwise, the image is classified as normal.
  
  23:41 So and the Fast API returned the decision, normally anomaly score, threshold, and model version.
  
  23:41 So this approach provide traceability while model caching improve inference efficiency.
  
  23:41 This completes my parts of the MLOps architecture.
  
  24:06 Pavel will continue with the next part of our presentation.
  
  24:06 Hello. I will continue the presentation.
  
  24:06 I see that we don't have too much time and we must do the presentation, show some streamlit parts, so I will try to rush a little bit, so please forgive me for the rushing.
  
  24:42 You must make all of your presentation, so I can make on mine part.
  
  24:42 Now, me, bla, bla, bla.
  
  24:42 Presentation, presentation.
  
  24:42 Do you see my presentation, is the question now?
  
  24:42 Yes.
  
  24:42 From current slide.
  
  24:42 And that's the presentation and I will show how it works from this moment then, a new model version becomes a candidate with its test, a Aurok, then the first registered model becomes champion, and the champion alias moves only in Aurok when it's strictly higher, a tie keeps the current champion.
  
  25:45 Registers bottle wood and pill as statistics and then model and category threshold are stored, and the best statistic are stored in the parameters and then the models circulate in the pipeline till there are better statistics, and we have built a streamlit to show it and a new model version becomes a candidate within the test. Aurok, the first registered model becomes a champion. The champion alias moves when the Aurok is higher, and that's so,
  
  26:33 And the next slide. Why it's not going forward?
  
  26:33 So, spotlight, I have created a spotlight for streamlit, so it's easier to see how it works and easier to explain how it works.
  
  26:33 Then evidently checks the drift about the data because the project works so that there are sent multiple pictures, photos, images, pixel collections from perspective of the TensorFlow and this are categorized into normality, and when something have 5% and not normality, because the threshold is 95% and the percentage is counted from the pictures that are given, then it's decided that it's an anomaly that will be visible on the streamlit.
  
  27:23 And then the Prometheus and Grafana APIs are checking if the whole pipeline is working as an ML machine learning operations systems correctly.
  
  27:36 Then let's go to Streamlit.
  
  27:36 Because listening, light on the stations, keep quiet.
  
  27:36 It's one chart, ML for flow, for three anomalies, so like was said before that are one more thing that are three separated models that work as one pipeline in this project.
  
  28:01 But if it would be specialized, it would be one pipeline for specific use case, like bottle, like pills, recognition of the defects, bottled defects or the wood quality based on the
  
  28:01 I don't know how it's called, but the design of the wood, how it was growing.
  
  28:26 And thank you for your attention on the presentation. Now, let's go to the streamlit part.
  
  28:38 How to make it all?
  
  28:42 Now, the streamlit part.
  
  28:44 What? [8:21:6] So.
  
  28:50 So, again, present stream part, where is this?
  
  28:56 Here.
  
  28:58 I hope that you see the Streamlit part and the Streamlit part looks so.
  
  29:06 And that's a flow of the application, how it's in the application and in the full pipeline is moved, the data is moved, here is a architecture, how it works from more technical perspective.
  
  29:06 And here are always tables that show the data, and I have created a spotlight that explains that, and the purpose is we demonstrate as MLOps workflow, for automated visual inspections.
  
  29:06 Our prototype uses MV tech adding images of bottles, wood, and pills.
  
  29:06 Front-end here is always a information where the source of this green is and where comes the data from why it's so made.
  
  29:54 Follow and I will follow the tabs throughout and
  
  30:00 Data, we separate training, serving, and monitoring to make its responsibility clear.
  
  30:00 Airflow and Streamlit reaches the data at the models only through the API and trace one image through prediction, then follow its logic into monitoring.
  
  30:00 Seven services, one comment, like we have created an API, that's Fast API, and this API it's communicating all the services in the application.
  
  30:00 Then one database holds the three models in our case, three recognition models.
  
  30:11 And statistically how many times that images photos pictures pixel collections for the tensorflow will come in,
  
  30:20 It would make in our case it's one time per hour, but it could be different.
  
  30:28 Of course.
  
  30:29 I spoke about it that faster, picking connecting all the data in this app and I would call them normal images,
  
  30:40 It's trained on normal images, and when some picture it's not normal, because usually on production very picture is
  
  30:47 A heavy product is quite the same, but then when there is five percent not normality, and then not normality five percent is described about the
  
  30:55 Spectrum that's the train that's the model was trained on.
  
  31:01 And no champion yet.
  
  31:06 When the data quality is also Holden and to don't make the drift of data too much too big, because when
  
  31:14 Something on productions happened and there are coming only false not enough quality products, then
  
  31:22 The model could learn that the not quality product is a standard, but we want to avoid it, and then it's a quality check
  
  31:31 Always on the base photos.
  
  31:31 And it looks something like that.
  
  31:31 I will stop for a second, and for example, "that's a insight of a good bottle", "that's a insight of a broken bottle", "that's a if insight of a small small part broken bottle", and "that's a contamination".
  
  31:31 And like this, it's normal from perspective of the model.
  
  31:31 That's a anomaly.
  
  31:59 That's normal, but it shouldn't be normal, but the quality it's other subject.
  
  31:59 And the machine learning operations pipeline is working correctly, but to host such solution, it's not easy it's not a simple hardware solution ability.
  
  32:16 Or how to call it and that's a anomaly.
  
  32:20 This case, I don't there is something, the picture is not enough quality.
  
  32:25 And then presentation, I a loop client.
  
  32:30 That's how the stream it works, then stream it is this presentation, this app, here we have some this.
  
  32:30 And then Prometheus monitors the airflow and elflow,
  
  32:30 Stream and
  
  32:47 Like all pipeline and all stress and monitors this, and Grafana also receives the healthiness of the
  
  32:55 Of the dashboard.
  
  32:58 And we hold the quality, so like broken images cannot manipulate the model and
  
  33:05 It's evidently and there are four drift parameters and that's brightness, contrast, sharpness,
  
  33:15 Saturation, and on these values, they cannot go too much far away from the main examples of
  
  33:22 Picture collections that are for the models, as the standard chosen on begin of the implementation.
  
  33:30 And that's Grafana, and Grafana is taking the API health and helping to monitor and make dashboards that are useful and we can like my Grafana on we can make on the on show that, but I see that the time is her gone.
  
  33:51 So.
  
  33:53 Thank you for your attention and where is the stop it.
  
  33:59 Yes.
  
  33:59 Thank you.
  
  34:01 Well, I almost stopped to but, but you were until the end because you well, a little bit over over the time that were that were given.
  
  34:11 I think like eight or nine minutes too much, but the thing is like the presentation that you did at the end.
  
  34:11 So the front end is like the front end web page.
  
  34:11 I don't know if it's that streamlit or something else.
  
  34:11 It is really well done.
  
  34:11 But maybe it repeats a little bit the presentation that you did in the in the slide.
  
  34:25 So maybe you could have presented that earlier and I don't know maybe adding information to the slide or anything.
  
  34:31 But but yeah.
  
  34:31 It was pretty clear.
  
  34:37 A little bit too long, as I mentioned.
  
  34:37 So, congrats anyway for this project that seems pretty much cover everything.
  
  34:37 It took a little bit of time to start at the beginning where we were.
  
  34:54 So where is the retraining strategies and the drift monitoring thing and then it came after at the end.
  
  34:54 So, I just do have a few questions.
  
  34:54 So, we won't take too much time because we already over the schedule and also we let after that ask theirs if they have some.
  
  35:17 So my first question would be like you showed us at the beginning the data ingestion by batches, where the model it is trained on one, then two, then three batches.
  
  35:26 So, that's just for the demo, right?
  
  35:29 In real life, you would keep incrementing the data set with new batches frequently.
  
  35:34 How would it work?
  
  35:34 Would you have to trigger manually airflow or the ingestion DAG, for example, every time there is new data?
  
  35:45 Or does the airflow keeps checking the database every, I don't know, every X hour to check if new data comes in?
  
  35:53 We split it before the data in three batches, because we don't have new data coming.
  
  35:59 We have a fixed amount of data, and then we treat it.
  
  36:01 We will treat it once, and then for example, every hour, he will call a new batch, and then he will start.
  
  36:08 Okay, but in real life, we have new data that comes in the database, will it trigger automatically the data ingestion, or will we have to re-trigger the airflow like automation to ask to call the database?
  
  36:21 Like, if we have new data that comes in the database frequently, for example?
  
  36:25 It must be checked automatically.
  
  36:28 We have any in real life new data coming, it must be checked automatically.
  
  36:33 And do you have a way to version every variation of the data set?
  
  36:38 Like, every time a new data set is created because at some point, it's like composed of two batches, then at some point it will be composed of I don't know, 10 batches.
  
  36:44 Is there a way to version to have a history of every version of the data set and maybe retrieve a previous one if you want to redo a specific training, for example?
  
  36:44 Is there a way to version like a versioning thing to data set?
  
  36:44 Yes, there is a way to version the data, for example, using DVC.
  
  37:08 So, that you implement it in your project or is it just something that you considered?
  
  37:08 To be honest, I started this task, but I am not finished this.
  
  37:20 But DVC all right, data version is a very important for our task.
  
  37:20 Maybe we have to implement this task in parallel with the database.
  
  37:39 We have to put our images in a database, for example.
  
  37:39 I think email, email is a free so, a cloud.
  
  37:56 So, a free cloud provider, I think.
  
  38:00 Email.
  
  38:01 Email.
  
  38:01 Email.
  
  38:02 I forgot the name.
  
  38:05 So, you have considered like adding versioning for the data set.
  
  38:13 And at the moment and also what is like the strategy behind that, like, does your model re trains every time there is new data, or only when do you detect some drift or when the evaluation metrics of the model are going down, or is it only every time the new data comes in, you retrain the model automatically, or?
  
  38:13 Yes.
  
  38:28 Yes, every time a new batch is coming, the model is trained.
  
  38:36 And then he will compare and then select a champion.
  
  38:41 And have you considered doing it the other way around?
  
  38:45 Evaluating the model with the new data and comparing if it's loses some performances on the data.
  
  38:53 And then if needed, we train the model instead of retraining it every time you have new data?
  
  38:53 And also the data drifts detection which evidently, what does it causes?
  
  38:53 If you detect drift, what happens?
  
  39:09 Do you train the model or what do you do if you see that there is some drift that has been detected?
  
  39:14 The model standard counted every hour and when the drift is too high, then the models try to recreate itself.
  
  39:24 And the best choice for this presentation would be probably to loop the pictures that are coming and they coming on production line.
  
  39:34 Then it will 200 times, it comes one header or so, then that will be the best loop for pixel.
  
  39:34 But there are variables that can be changed like now it's 1 hour and 24 hours in this.
  
  39:52 But there are configurables that are easy to change for this case.
  
  40:00 So I think the first step is.
  
  40:01 To investigate why.
  
  40:03 Why there is that drift.
  
  40:05 I think we could have done something like, drift it has been detected, maybe we could evaluate the model first with new data and see if new data, if the model works, still works fine on new data, and then if needed, we retrain the model, because of course, the thing that you were missing were like constant live data.
  
  40:21 I'm not saying that it should be implemented in your project, but that it could answer your question, because if we have constant new, fresh data, then maybe we can fix some data drift that has been detected or performance losses from the model or anything, but maybe something to research a little more and train a little more is, how would I, what would I do if I see that there is either some drift or that the model is not as good as before, and considering what can be done at this point, so, but the project was still well done.
  
  41:01 And I think I will let Kilfan as their question, because we are still over schedule, so Kilfan, I don't know if you have a question or any review or anything to send to the project.
  
  41:12 So far thanks for your presentation.
  
  41:16 It was a bit too long, but at least it was complete.
  
  41:20 So, congrats for that.
  
  41:22 I will try to ask an easy question, because we are a bit late.
  
  41:28 If you have tomorrow to put your project into production, for example, would you change something to your project or will you keep it like that?
  
  41:40 No, the implementation is not complete.
  
  41:44 So we have to add some future as Kelian mentioned.
  
  41:50 For example, the security of the application, authorization and authentication is also a very important future, I think, for example.
  
  42:06 So it wouldn't be made for production because it's made for presentation, it will be sure made for strict engineering purposes, and not to explain how it works, it will be different.
  
  43:17 Thanks.
  
  43:19 I'll let maybe Kelian conclude.
  
  43:21 Well, thank you for the presentation, it was really clear, even if again, it was a little bit too long, so, maybe if you have another presentation to do at some points, because it will happen in your career.
  
  43:34 Well, I don't know, maybe we should have train together a little more, or I don't know what exactly was the problem, but you were a little bit over the schedule, but other than that, the project was still well done and well presented, and the little presentation at the end on the streamlit or the front end was also well directed with the spotlight thing explaining everything, but maybe it's a repetition of what you already said in this state.
  
  43:57 So that could be the problem of why it was too long.
  
  44:01 But congrats anyway for the project for the next steps, just to again be short on that.
  
  44:07 Again, if you have any question, don't say that to ask directly in your coho channel or via DM directly, you can DM me or your program manager, but consider that now the project is done and focus on the last monetary exam that you still have to do, if you still have some, because then I will have to check, probably, around next week, everyone that has rated the exam and then validate and send the certification and stuff.
  
  44:35 So, focus on finishing the monetary exams that you need, and just a reminder for the part, you have to complete at least seven out of the 10 and after that you still have the possibility of coming back to the learn platform, you still have access to the learn platform, to redo some of the courses, or, for example, train on the optional courses, also, if you want to.
  
  44:54 But again, thank you and congrats for this project and the training.
  
  45:01 And again, if you have any question, you can DM me, your program manager, or directly ask me on your cohorts channel.
  
  45:06 I think we're going to go now with the next group. Thank you.
  
  45:12 No problem, thank you.
  
  45:13 Before going, before losing too much time.
  
  45:19 So, the next group should be the group.
  
  45:22 Are you still four members, or I think? We are four.
  
  45:27 Okay, great.
  
  45:29 Everyone is already in the meeting, so we're Christopher, Sandeep, and Benjamin.
  
  45:33 And the slides are visible, right?
  
  45:35 Yes.
  
  45:37 Okay.
  
  45:38 So, hello, everyone.
  
  45:40 We are Benjamin, Christopher, Romil and Sandeep, and our ML ops project is "Rakuten France product classification".
  
  45:48 So, the seller lists a product with a title, a description and a photo.
  
  45:54 Our classifier is a multi-model.
  
  45:57 It reads the text and looks at the image.
  
  46:01 Every product has to land in one of the 27 categories, for example, "collectible cards" or "pool and spa".
  
  46:05 The focus of this project is not the model itself, but everything around it.
  
  46:07 Data ingested once and versioned, every training tracked, only better models promoted, served through an API, retrained on schedule, checked for drift and monitored.
  
  46:15 So, our data is a rektra training set, 84,916 products, each with a title, a description and one image.
  
  46:24 A one-shot script loads all of them into a postgress table, in about 19 seconds, and every image was matched to its product.
  
  46:31 Each row holds one product, its title, description, the path to its image and the category code as a target.
  
  46:37 The load is saved to rerun, if the table already has rows, a second run does nothing.
  
  46:44 Training them reads the table, 3,000 rows at a time, and remembers where it stopped with a cursor in the table.
  
  46:49 So, Propostgress is our single source, training, drift checks, store predictions, all read from or write to it.
  
  46:56 The image themselves stay on the disk, the table only holds their paths.
  
  47:00 So, the raw data is versioned with DVC, Git keeps only a small pointer files.
  
  47:04 The data sits on Tags hub.
  
  47:06 A hash is a fingerprint of the content.
  
  47:08 The same content always gives the same hash.
  
  47:10 DVC writes a pointer, DVT, sorry, I'm sorry.
  
  47:18 DVC add writes a pointer file, with the MD5 hash, DVC push, uploads the data, DVC pull, brings it back.
  
  47:24 The table shows three hashes, two CSC files and the image folder.
  
  47:27 Each training tags them in MLflow as tags plus versions and batches.
  
  47:30 So, each model records the data hashes in which it was trained on in a postgress table.
  
  47:37 Our model is deliberately a simple multi-model baseline.
  
  47:40 Text site, TFIDF on the title and on the description, 5,000 terms each.
  
  47:45 Image site, frozen ResNet 18, gives a 512-dimensional embedding.
  
  47:50 All of it feeds a logistic regression with balanced class weight.
  
  47:53 And our main metric is the weighted F1.
  
  47:55 Each training takes one new batch of 3,000 rows, 2,400 to train and 600 to test.
  
  48:01 In our last run, yesterday, which I ran, the first model scored .4280 and the version four in the production that after run, scored .4262.
  
  48:11 Each score has its own batch, and so versions are not directly comparable.
  
  48:18 Promotion, therefore, scores both the models on the same 600 rows.
  
  48:22 Now, this card shows a runtime of 141 to 167 seconds on a CPU, about 2.5 minutes each.
  
  48:26 Every way of starting a training works, and retaining is cheap.
  
  48:30 We choose a speed over accuracy on purpose.
  
  48:34 The raw CSV file and the product images, versioned with DVC are loaded into postgress table.
  
  48:40 Training runs in continuous mode, each scheduled or triggered calls the next 3,000 rows after a cursor.
  
  48:45 Trains and logs the runs into MLflow.
  
  48:47 MLflow also holds the model registry and it's with its own web interface.
  
  48:51 The fast API service runs as two copies behind an NGINX gateway, each copy loads the model and registry.
  
  48:58 Makes as production, and our streamlit app calls the gateway.
  
  49:02 Airflow ties it together, every two days, the DAG calls the training endpoint and then the drift endpoint.
  
  49:08 Evidently compares the next 3,000 row batch with the training baseline, the first 3,000 rows and writes the scores.
  
  49:14 Prometheus scraps the API metrics every 15 second.
  
  49:19 Grafana shows three dashboards and four alert rules.
  
  49:24 And reads drift_metrics from Postgress.
  
  49:26 Each service runs in its own Docker container, started with Docker compose.
  
  49:32 Training and drift check runs inside the API container.
  
  49:35 Now, I will hand over the next part to my teammate Romiel.
  
  49:38 We need not switch the screen, because I will be doing the browsing part.
  
  49:46 Hello, everyone.
  
  49:49 And now let us look at how we track register and automate every model return.
  
  49:56 Every training run is packed in MLflow.
  
  50:00 We log the parameters.
  
  50:00 Name, the model name, the classifier, the text I test, size of 0.2, the size of the batch and the random speed for 2 for the 3.
  
  50:13 Here you can see a few training run. Each with its own version day and time was recorded.
  
  50:23 Finally, the train model is logged with its classification report and confusion matrix and registered.
  
  50:32 Each version is targeted with its score and the basis of its comparison.
  
  50:40 So, tracking tell us that what happened and in each run the register decide what happened next.
  
  50:48 Let's the next slide.
  
  50:53 Every training run is registered as a new version.
  
  50:59 Every training is registered as a new version.
  
  51:00 Here are five version from our home.
  
  51:04 We can see the version three is the one on production.
  
  51:09 But first, the model's score, and we can see that the first version is 0.4218 and after this training, it went straight to production because there was nothing to compare it with.
  
  51:30 And from then on, the promotion rule is strict.
  
  51:34 A new model must be production on the same test how.
  
  51:38 And we can easily see that the version 3, as I said now, is the one in production because it beat the others.
  
  51:46 And the version 1, 2 4 and 5 go in staging.
  
  51:54 At any point exactly, one version at time is in production.
  
  52:00 The API reload the production version after every training, it's run itself.
  
  52:07 So a promotion goes live without any restart at all.
  
  52:13 Now, let us move on the API.
  
  52:18 The model is served by a fast API service with six documented endpoint.
  
  52:24 The health to check that the service is up.
  
  52:28 The model for the serving model, credit for the category and probability, training which train the model, compare and promote to compare and promote to and the model we did.
  
  52:44 And training trigger which run that same training in the background.
  
  52:50 And rift compute for the rift report.
  
  52:54 And every call is stored in the prediction table.
  
  52:59 But something has to decide when the hunt happen in the first place.
  
  53:04 And that is the whole of airflow in the next slide.
  
  53:13 The airflow the continues training, the driver the pipeline.
  
  53:20 It has two task.
  
  53:22 First is higher a continuous training, then it's higher the drift computation.
  
  53:30 Every 2 day one run take the next 3,000 row with 2,400 for the training and 600 for the test.
  
  53:40 It train log to ML flow, promote the new model or keep it in staging.
  
  53:49 And then try get the drift computation with compare and training baseline with the newest pitch.
  
  53:57 As we can see here the model in production is the version the dead version, the version 3.
  
  54:06 And the version online, the current version online in production is the version 3.
  
  54:14 Thank you.
  
  54:16 The next person.
  
  54:19 I think that it's for me to take over here.
  
  54:22 I need to stop sharing now.
  
  54:24 One second.
  
  54:27 Share.
  
  54:29 Send request.
  
  54:36 You can try now.
  
  54:37 It's stopped.
  
  54:59 Hope that you can see my screen now.
  
  55:03 So after every training, the directed cyclique graph, the second task, compute the data drift with the service evidently.
  
  55:11 It compares fixed reference that are the first 3,000 rows with the first model was train on against the newest 3,000 row window.
  
  55:24 The one cursor has you switch.
  
  55:26 So for the two text columns, so the title and the description, it train a small classifier to tell the two sets apart and a score above 0.55 counts as a drift.
  
  55:37 For the three numeric columns including the category, it uses the norm Wasserstein distance with the threshold of 0.1.
  
  55:44 The images are not compared if more than half of the columns drift for 10 minutes, that important graph and call the retraining web hook.
  
  55:53 We have one limit to be aware of, both sides of this comparison come from the same data set, so what we detect is the drift between slices of a static corpus not between training data and live traffic.
  
  56:05 Comparing the store predict request instead is implemented in our airflow branch and it would be next improvement step.
  
  56:14 So for monitoring the API exposes matrix endpoints and Prometheus scrapes it every 15 seconds.
  
  56:29 The target is up.
  
  56:31 Grafana has three dashboards that I will just show you briefly later.
  
  56:37 Model which shows the serve version, training a status and prediction confidence, then we have API health with request, latency and errors.
  
  56:47 And for the last data drift with the scores from evidently and easy chart on top.
  
  56:54 And also Grafana what it serves is there are four alert rules.
  
  57:00 And all four were normal at the end of the room.
  
  57:04 The drift alert calls.
  
  57:08 The drift alert calls the retraining web hook, racuten retrain that it's an endpoint in our APA service run.
  
  57:16 And I would like to share now live version of our service that I'm here live serving, if you allow me.
  
  57:30 Out of the presentation, that it's not my conversation.
  
  57:43 I think that I have to do that again.
  
  57:44 You see anything?
  
  57:46 Yes.
  
  57:50 Yes, we see Grafana.
  
  57:52 So, that's the health dashboard monitoring.
  
  57:57 I have to move.
  
  57:59 Okay.
  
  58:00 Yes.
  
  58:02 This is the health Grafana monitoring where we have for example the request per second.
  
  58:04 I have a silly dot but a script that sends request of really easy only with data that is a title and a description really dump.
  
  58:18 And therefore you see all these requests and the predict is going up every 15 seconds.
  
  58:26 Of course, we have scratching Prometheus every 15 seconds, therefore this big number this 5,000.
  
  58:34 In my local version I have already trained nine examples.
  
  58:39 We have of course the calculation of the latents latency and if the API is available or not.
  
  58:45 And this tech the rock is just the one that is in the last five minutes.
  
  58:52 Then of course, we have also the model that it's serving the last one that it's how it's stored the identification.
  
  59:00 The age of the model, if the training is idle or it's just serving or it's active now.
  
  59:07 The last report that I did three hours ago.
  
  59:12 And when it's ended.
  
  59:14 And of course, we have because of these calls that I'm doing the prediction confidence is really low.
  
  59:21 Because as I told you, it's a dump service, therefore the low confidence rate is really high.
  
  59:28 But usually it shouldn't be that way if that would be proper data.
  
  59:32 And the data drift in the final is long time when you can see the concentrated here my calls to the training and the difference between them.
  
  59:44 And of course, it's also worth to comment the four alarms.
  
  59:50 If the API is serving without the model, that's an alarm.
  
  59:52 If we have a data drift over the predefined threshold, it's an alarm.
  
  59:57 If the drift monitor has stopped reporting, that's an alarm and
  
  01:00:00 If the training runs are failing for whatever the reason that's also in alarm.
  
  01:00:05 And then say that in my site I will just handle the control to.
  
  01:00:10 If I'm allowed.
  
  01:00:13 Excuse me I cannot see.
  
  01:00:17 Here.
  
  01:00:20 To my fellow Christopher.
  
  01:00:23 Thank you.
  
  01:00:26 Let's make.
  
  01:00:30 This live.
  
  01:00:33 Can you again see the presentation slides?
  
  01:00:33 Yes.
  
  01:00:38 For a short presentation we will show our streamer page which is based on two tabs, one dashboard tab, which contains all of our services we created, and the Model API tab where we can test the prediction and trigger training or a drift report.
  
  01:00:56 We will show that in a second. Before that we will go.
  
  01:01:02 For some known limitations of the projects for now.
  
  01:01:07 For now, we train retrain automatically every two days.
  
  01:01:12 It's like a simulation for pulling new data into the API.
  
  01:01:16 But we could change that to only train if drift is actually detected, which we also have, but we can cancel the two-day training or new labeled data comes in.
  
  01:01:28 A model gets promoted by luck or even it's.
  
  01:01:33 Even if it is slightly better than the current production model.
  
  01:01:33 So we could change that to just promote models to.
  
  01:01:45 Be used if they are better than noise could.
  
  01:01:53 If the change is greater than the noise in the data.
  
  01:01:53 Each training embeds the images up to 3000 3000 rows because of our CPU limit, it would have taken us too long to train on bigger batches.
  
  01:02:10 We could speed things up through computing the image embeddings once at the beginning and then reuse it while training, which wouldn't be possible in a production setting when images come in live, just if they are pre-processed.
  
  01:02:31 The drift baseline is fixed at the first 3000 rows, the drift reset on promotion could be implemented.
  
  01:02:31 We could also change it that the whole data set is used to detect the drift when a new batch of 3000.
  
  01:02:51 Hey, pode fechar a porta aí, por favor.
  
  01:02:51 For now there is no Tu não pode fechar a porta do quarto, eu tô entrando numa apresentação de tese.
  
  01:03:03 And you also have to do a manual setup.
  
  01:03:03 So, of course there has to be implemented some API keys to log in into our services and it would be great to have a make file or one common setup file to set the whole project up.
  
  01:03:21 The setup of the project now takes about between half an hour and two hours, in a clean setup with the DVC, it takes longer time.
  
  01:03:37 I will switch now to the dashboard page.
  
  01:03:37 You probably see that too, aren't you?
  
  01:03:45 We have collected all of the dashboards here, as you've seen before, the Grafana page, Prometheus is embedded, we have airflow with our ducks and we have the fast API documentation.
  
  01:03:45 Unfortunately this is a version from two days ago, which doesn't contain the training triggering endpoint.
  
  01:03:45 Excuses for that.
  
  01:03:45 The latest GitHub version does serve the endpoint documentation.
  
  01:04:14 It's up which is not embedded, but serves a link and the MLflow page to track for the new models.
  
  01:04:24 The Model API, we can quickly check if everything is on, the API is there and the model can be served.
  
  01:04:33 We have information over the latest production model, it's accuracy weighted F1, weighted precision, weighted recall and the version number of the production model.
  
  01:04:44 We have different input modes for the prediction, for now we want to test the prediction on training batch from single sample.
  
  01:04:44 We can just choose some random things we get a used book.
  
  01:04:59 We try to predict it and predicted it as used magazine, so it failed.
  
  01:04:59 Rakuten data set is known to mix and overlap some of the categories, our backup backend model is not the greatest, but we see this would be a flagged one because the confidence level is under 0.6.
  
  01:04:59 And so we save the prediction in our data bank.
  
  01:05:28 What we have left, 40 seconds.
  
  01:05:30 If we can go a little bit over time, it just takes a minute or so.
  
  01:05:38 We could trigger a training which we will see in a second in the MF flow page.
  
  01:05:44 Just wanted to show that it registers, it will compare it to the production model and if this model will be better than the production model, it will promote it as a new production model.
  
  01:05:57 If not, which is as expected here, it will reject it and use the old production model for now.
  
  01:05:57 All of my example tries were not better than the old model.
  
  01:06:15 Just wait, it takes on my machine about 40 seconds so it should be done in 10 seconds or 20 seconds or something.
  
  01:06:24 You can wait. We will then compute or trigger a drift report. We can also see that in the Grafana dashboard again.
  
  01:06:24 So training is done.
  
  01:06:37 To wrap things up, I will compute the drift report before we go to the dashboards again.
  
  01:06:43 It's computed.
  
  01:06:43 Wait.
  
  01:06:50 We see the matrix and none of the matrix is above the thresholds as expected like before, but we will see that in the Grafana page.
  
  01:06:58 Go back to the dashboards. In model registry we should see now that there are 14 models. This one is just trained now and it was not staged because it wasn't better than before and in the Grafana page, we should see that also drift wasn't detected at all because all the scores went above the threshold.
  
  01:07:25 That was it from my side.
  
  01:07:28 Thank you for your attention and we would be ready to take your questions.
  
  01:07:28 Great.
  
  01:07:34 Thank you.
  
  01:07:34 Almost well on time.
  
  01:07:37 So this project, it was, I know the presentation was really clear and the project looks also really well done.
  
  01:07:37 I really like the short table outlining the limitations of your architecture and the potential solutions.
  
  01:07:37 It shows that you clearly understood the challenges of production envelops.
  
  01:07:37 So what would be expected on a real project, and it also swept away most of my questions that I had during the presentation.
  
  01:08:10 So I think I will let Sebastian go first with the question and I also give the review of your presentation.
  
  01:08:22 Okay, thank you Lillian and thank you for your presentation.
  
  01:08:26 That was quite clear the demonstration and everything that you have integrated.
  
  01:08:32 I have a few questions, but I will try just to go straight to for me the most interesting one.
  
  01:08:41 Did you implement at all any security layer in both in your architecture and in your code.
  
  01:08:54 Should I answer?
  
  01:08:54 I mean, I took of me.
  
  01:08:59 Of course.
  
  01:09:02 Yeah, so the it was every person was working on different branches.
  
  01:09:08 So probably I already implemented on my branch where I created the login page for into the getting in the main dashboard.
  
  01:09:21 And this would generate a key or for the client also and this was one the security feature and I guess, Engine X also offers a security feature because of HTTPS and HTTP thing.
  
  01:09:21 And then and it also hides internal ports. You're not exposing the ports.
  
  01:09:38 And what else?
  
  01:09:40 Yeah, I mean these are the main ones which we thought of.
  
  01:09:46 So this implementation remained on your branch and was not propagated on the main.
  
  01:09:46 Yeah.
  
  01:09:46 But it worked, so it should not be.
  
  01:09:56 I think that is not interesting now for the audience.
  
  01:10:00 Let's say to explain everybody's difficulties just to merge the projects, etc, but it was a regular group of people just trying to merge different branches and everybody would tell you if we would have given I don't know one week more the project would be perfect, but.
  
  01:10:00 That was not the case, but we considered that. We have no time to do that. Just the regular thing, guys.
  
  01:10:09 Not everything was able to enter.
  
  01:10:13 My next question would be to ask what happened. Let's say today I want to or today you want to change the model type. You change something in your training Python script.
  
  01:10:27 How do you do to reflect this change into the main solution which is running?
  
  01:10:40 I don't get your question. Excuse me, Sebastian. My question is I understand. You train the logic of the training.
  
  01:10:47 Let's say that you change the model at all. You go into the training script and instead of I think I've seen some so far. Instead of the RESTnet, you change it to accept inside exception, for example. You change the model because I don't know, you after experimentation you have seen that this model is good. So you change the model. So what happened after this change?
  
  01:11:10 To make sure that the new implementation of the code reflect into your architecture.
  
  01:11:21 If we change the model logic, so the model itself, I think that is because we find that it's better and it that would not be fair to compare the same metrics with different kinds of model. Even I don't know if that's possible. So that would be a decision of probably, we have to consider that with a comparison of old models and new models. So of course, that's the thing because you cannot
  
  01:11:45 That would not be fair for the old models, let's say, if you decided to buy a new car, and the new car runs more. I don't know if you're asking for that, but you need, even if you buy a new car, you still need before writing the new car to make to check if the new car kind of expect the basic need that you have and exceed the basic need that you have. So you need some code in that if the model, if the two models are comparable, I guess so. I guess that there are some, but So we probably maybe probably one could set up a promotion criteria that if F1 metric score has improved by .02 and if each category which is predicted is not falling that much apart. Okay, so it gets automatically changed to a promoted to a new model. So, probably that will be I think you answered, but you answer partially the question because, of course, the promotion logic takes care of changing the model, etc. but this is effective for the running pipeline. But if you change the logic inside the script and that your new script is not seen inside your architecture, basically your exception model will never reach the will never end to the production side, because it will remain into the script and will never run inside the running production pipeline which is actually being used. So you need a technology to automatically reflect new change in your code inside your pipeline which is running in production. Do you understand what I am asking? I mean that we have to make the container down and up with the new version.
  
  01:13:26 Exactly, and you need the technology to do this. You need the technology that will picks the new version of the script, rebuild the container the new version of the containers and down the old one and up the new one, so that basically you keep running as if nothing happened.
  
  01:13:45 And I think you know which technology I'm referring to, so I'm not going to dig into that. Now, the Jenkins or GitHub Actions or stuff like this.
  
  01:13:54 Okay.
  
  01:13:55 CI/CD pipeline.
  
  01:13:58 Do I have another questions?
  
  01:14:03 No, I think I will stop here. So thank you for your presentation otherwise we will leave see, but thank you. Your presentation was good.
  
  01:14:11 Thank you very much.
  
  01:14:12 Thank you.
  
  01:14:14 Congrats again for the presentation, the project, and also the training and as I mentioned to the previous group, try to focus on finishing the mandatory exam that we still have to pass. And again, if you have any question, don't hesitate to ask either directly to me or your program manager or also directly on your Slack channel. And I will reach out to you if, as I said, probably around next week I will check who has the right amount of exams, and if I see that you're still missing some, I will send you a DM on Slack probably, saying, "hey, you still need one or two exams more time, or is there something wrong, or are you stuck on something" just to see what said. But right now, the project is done. Focus on the exams on the platform and again, a reminder, you have to complete at least seven out of 10 to complete the training and you will have plenty of time after the training to come back to the learn platform and do the other ones or maybe take spend more time on a specific topic that you want to go more in depth on. So again, congratulations for the project for the training and also for the presentation which was really clear and right on time also. So, congrats.
  
  01:15:32 Thank you, Kilian. Thank you, Sebastian.
  
  01:15:34 Thank you.
  
  01:15:35 And I think we can now go with the last group, which is the weather prediction group. Is everyone already in the meeting, already there, and ready? So you should be I think four people: Thomas, Gabriel, Jonathan, and Ziad.
  
  01:15:54 We're all there.
  
  01:15:56 Okay, great. Well, you can start sharing your screen, start setting up everything, and again, when you're ready, you can start your presentation, and we are listening. Then Sebastian and myself.
  
  01:16:08 I want to screen and Gabriel, I think will start and I will pick through it. If everyone is ready, can you see my screen?
  
  01:16:17 Yes. Should be, it should be on our slides.
  
  01:16:21 Yes.
  
  01:16:23 Thank you very much. Good afternoon, everyone. We are a team of four, Gabriel, Thomas, Jonathan, and Ziad. The goal of this work was really to predict the weather whether it will rain tomorrow in a given weather station in Australia or not. We didn't focus much on the model itself, but we focus more on the MLOps, so all the technologies we put around it to realize this problem. I'm going to start with the architecture here. This is the big picture, you see on the screen. We all start by capturing the data which is coming from the Kaggle Australian weather history and we add some data also coming from the open meteo API. We combine these two information together. And then we switch to the airflow part which is running two pipelines. So we do a daily run which is just checking the incoming data and the second pipeline is to retrain the model. So, in case we detect any drift or anything like that, we will talk about that later, then we have a way to retrain the model also by accessing a endpoint API, which is available there. Every day, the new data and the outcomes and also the drift informations they are stored in our superbase postgres, this is the one we have used for storing the information, and we store all the snapshots in the storage. And then all the secrets, all the keys we store then in the Superbase vault. This is the one we have used for keeping everything secret. Initially, we started with local keys, but this was a mess to share this across the team. And then Ziad found a very nice solution which relies on Superbase vault. So when we retrain, the LM flow keeps the track of every model, and the new one only becomes champion in case is the best performance as the one which is currently in execution. And we have some quality gates. We check the recall needs to be at least 0.75 for the model to be eligible to be a champion. And also, we have to have a better ROC AOC and then we tag this as the new champion and then the system keeps running based on the new champion. The user reaches the champions through Engine X and Fast API and every prediction then gets saved in the Postgres database. For the monitoring part, we use Prometheus and Grafana, which keeps watching the API. Evidently we will check any drift that happens during the day and then we'll trigger some actions. So when the recall falls below 0.75, which is our quality gate, Grafana then triggers a retrain of the model. So next slide, please.
  
  01:19:49 Next slide?
  
  01:19:52 Thank you, Ziad. So for each prediction, here, we basically, we take one station on one day and we have around 20
  
  01:20:00 Weather measurements?
  
  01:20:01 The outcome is what is the chance for having a rain tomorrow.
  
  01:20:06 The challenge part of this work was the Australian data set that we got.
  
  01:20:09 They said, only 23% of the data are rainy days.
  
  01:20:11 Australia is a very good country regarding weather it looks like.
  
  01:20:15 The model which always says no, is 77% accurate.
  
  01:20:18 And never catches any rainy day.
  
  01:20:19 This was the challenge of the data set we got.
  
  01:20:22 We decided to not judge the model on accuracy but we picked the models on ROC, AUC, and our squad you can see here on the slide is 0.87 approximately.
  
  01:20:29 We recall also that we need to stay above the 0.75, because, of course, if we miss any rainy day, then it hurts much more than having a false alarm about the weather there.
  
  01:20:38 The next slide, please.
  
  01:20:40 Then we said, let's consider also another location.
  
  01:20:41 Although, this was not in the scope of the work, but let's see what happens if we take data from Singapore, for instance, which is a very rainy country.
  
  01:20:46 Then we did it.
  
  01:20:47 So, in Singapore it rains around 83% of the days and of course evidently is able to flag all the five features that we monitor.
  
  01:20:52 And then we can see here that the model suffers.
  
  01:20:55 We go from 0.87 to 0.70 here.
  
  01:20:57 And we try to retrain the model based on the Singapore date, which helps a little bit.
  
  01:21:01 So, it moves from 0.64 up to 0.70.
  
  01:21:04 But it only wins back the part of the loss.
  
  01:21:06 So, it's not completely optimal.
  
  01:21:09 Next slide, please.
  
  01:21:11 And just few words about engine ngix gateway here.
  
  01:21:14 Of course, we put some security layers in place.
  
  01:21:16 We encrypt the data with TLS which is the standard support there.
  
  01:21:19 We have some limits of the request.
  
  01:21:20 So, we limit per IP 10 requests per IP and also we say one train per second because of course the training is quite expensive so, and the beauty of this of course, it's all configuration files so, we can easily fine tuning this according to the goal of the project.
  
  01:21:30 We have put in place a couple of regression tests which run in our CI pipeline and then we are able to also identify any possible bug whenever we change the model or we change the code.
  
  01:21:38 That's it.
  
  01:21:39 I will hand over to Jonathan who will show you the version system and also the model behind it.
  
  01:21:42 Thank you, Gabriel.
  
  01:21:44 So looking at the data, as Gabriel mentioned, we have two data sources.
  
  01:21:46 Kaggle on the one hand, with 145,000 rows, spanning 2007 to 2017, and then we have open Meteo, whose API allows us to get data from the past years up to today.
  
  01:21:52 Gives us the same columns so we can merge everything together.
  
  01:21:55 Split it by date, because we have temporal data, of course.
  
  01:21:56 And then, every data set gets its own unique identifier which is then tracked in DVC as well.
  
  01:22:00 That's some data versioning in DVC.
  
  01:22:02 And this which data is being used is also being transferred to MLflow, which next slide.
  
  01:22:08 So in MLflow, we have two experiments set up.
  
  01:22:10 First one is for every training run that we do.
  
  01:22:13 So which model is used? It should be in all cases for us.
  
  01:22:15 But the number of trees is the learning ratings like that.
  
  01:22:16 Then how it's performing.
  
  01:22:19 So our two main criteria there are the champion the Roc arc, and the recall.
  
  01:22:21 Which data was being used, which git commit was being used, so we can reproduce everything there.
  
  01:22:25 And then we have the artifacts with the model itself, data sets and the Json file, it has everything together.
  
  01:22:30 Then, the second experiment is about, evidently, to a way to visualize our data drift there.
  
  01:22:35 Thomas will go more in-depth on this later, so, I'll not elaborate on that more.
  
  01:22:38 Next slide.
  
  01:22:40 And then, finally, in MLflow, we have set it up as well with Champion and a candidate.
  
  01:22:44 So, the best model is the Champion model, and every new model becomes a candidate, and if it passes training criteria, then it can be promoted to Champion.
  
  01:22:49 So, criteria are then that the code needs to be clean, clean git commit.
  
  01:22:52 The recall needs to be at least 0.75 for the reasons that Gabriel explained before.
  
  01:22:55 And the validation Roc arc has to be better than the other champion.
  
  01:22:58 And then Fast API uses our Champion model.
  
  01:23:00 Then Thomas.
  
  01:23:02 Thanks, Jonathan.
  
  01:23:04 So let's follow one prediction through the system.
  
  01:23:05 So the request comes in over to if through HTTPS to Inginx, which handles the encryption and rate limit and then heads it to the Fast API.
  
  01:23:12 The Fast API checks the login and the input.
  
  01:23:14 For example, rainfall has to be between zero and 500 millimeters and an unknown station is rejected with a suggestion for likely typos.
  
  01:23:19 Then it asks MOflow which version is the Champion, and then it only reloads the model when the version changes.
  
  01:23:22 So, promotion or rollback goes live without restart.
  
  01:23:25 And if MOflow is down, it falls back to local copy of the model.
  
  01:23:27 Every prediction is saved in Postgres and a day later when we know the real weather, we can check how good the model really was.
  
  01:23:32 And the answer comes back with the chance of rain and exact model that produced it.
  
  01:23:35 Besides predict there are four other public endpoints which is to check the status of the API, the live predict which fetches today's weather from open meteo, then you can predict if it's going to rain at your place, the train endpoint to retrain a model and the Drift Simulator we use in the demo which you can see later.
  
  01:23:45 And there's also a fifth an extra endpoint which is the metrics endpoint.
  
  01:23:49 But that is only for Prometheus, from outside Inginx returns with a 404.
  
  01:23:52 Next slide, please.
  
  01:23:55 So, we have two decks.
  
  01:23:56 So we have the weather pipeline which runs everyday at
  
  01:30:00 Berlin time, and it fetches new weather, cleans it, adds the real outcome to past predictions and runs the evidently monitoring job.
  
  01:30:00 The weather retrain deck has no schedule.
  
  01:30:00 It retrains, validates, and compares with the Champion and Grafana starts through the Airflow REST API, when the real recall drops.
  
  01:30:00 From this, the Airflow web server joins our docker network so it works.
  
  01:30:00 So, the question is why should we split them?
  
  01:30:00 So, checking is cheap, but training is not so cheap, and retraining on the fixed schedule would train even when nothing is wrong.
  
  01:30:00 So, each task in our desk is a docker operator that runs one of our images, and containers are removed after each task.
  
  01:30:00 The training task calls the post on the train endpoint through Inginx, like any client so the stack must be up.
  
  01:30:00 Airflow reaches Docker through a socket proxy that allows containers, images and post calls, but denies network management for security reasons.
  
  01:30:00 Each task retires up to three times with one minute apart, and if Airflow was down, it catches up every missed day one run at a time, and each run fetches the weather of its own day.
  
  01:30:00 So for the days that were already missing, we ran one time back fill.
  
  01:30:00 And retrained model only becomes champion if it passes the recall gate and beats the current champion.
  
  01:30:00 So next slide, please.
  
  01:30:00 Thanks.
  
  01:30:00 We also have continuous integration and delivery.
  
  01:30:00 The first line is our continuous integration.
  
  01:30:00 CI runs on every push and pull request to master into two jobs.
  
  01:30:00 The first job is the Ruff lint format check and the unit tests.
  
  01:30:00 The second job is on Docker so it builds all the seven images, starts the API and Nginx, and runs the live gateway test against them.
  
  01:30:00 The second line is our release.
  
  01:30:00 Every time code lands on master, the GitHub builds our ingestion, preprocess, and API images, and uploads them to the GitHub container registry.
  
  01:30:00 Any server can download and start them without building them itself.
  
  01:30:00 Next slide, please.
  
  01:30:00 For the monitoring part, we have two kinds of monitoring.
  
  01:30:00 We have the live from the API and the daily batch check.
  
  01:30:00 For the live part, the API measures itself, and every request is counted by endpoint, status, and is timed.
  
  01:30:00 On top the live predictions record station, if it's raining or no raining tomorrow, the probability and the model that answered, so training and training records the validation metrics.
  
  01:30:00 All of this, as I said before, is on the metrics endpoint and as that Inginx blocks it from outside, but Prometheus can read it on the inside and scrapes it every 15 seconds.
  
  01:30:00 Once a day when the real weather is known and evidently job runs to checks, so the first check is
  
  01:30:00 That the inputs have changed compared to the training data. We call this feature drift and only raises a warning because changed inputs do not prove the model got worse. And the second, it checks whether the model was right. So, as soon as at least 30 predictions have a known outcome, it computes the real recall and if the recall is below 0.75, it requests a retrain again.
  
  01:30:24 Evidently, part is a batch job so that ends after a few seconds so Prometheus cannot scrape it so we push it on a push gateway instead and Prometheus reads it then from there.
  
  01:30:36 Grafana turns the retrain request into an alert and calls airflow through a web hook at most once a day. That starts the weather retrain deck.
  
  01:30:46 We have seven alerts. So, for the API, if the API is down, a more than 10% server errors, and if we have an average latency above 5 seconds. For the model part, we have a retrain request alert, last training below ROC AUC beneath 0.866, or a recall beneath 0.75 and an unusual rain rate.
  
  01:31:06 So only the retrain request starts training again. The others are warnings for person, for now, only visible in Grafana. And our dashboards and alerts are not clicked together by hand. They're provisioned, so they are stored as files in Git, so anyone on our team can rebuild the same monitoring with one command. And I have to hand it over to Set.
  
  01:31:29 Thank you, Thomas. Now my colleague showed the a pretty good overview of our architecture and how it works and now I want to show our application in a live demo on two examples using our API. So the two examples are live prediction, so we call our model and get a prediction and one will be the model training. So the first inside, we can choose a station so we are in Australia. We choose a city of our choice. Now, Sydney is chosen but maybe I could choose another city like Portland and then I could call our API directly through our endpoint, predict live weather.
  
  01:32:06 This will send a call with the city name and then automatically pulls data from Open Meteo because our ML model needs more information like humidity and temperature about today's day. And at the end, it will give us back the prediction. So at the moment, it says, "no, it will be sunny." Thank god, and it will give us back the probability of the model.
  
  01:32:29 So 27%, so clearly, there should be no training. And to prove that the API was really called, we render two panels from our now running Grafana in the background. On the left hand side, we see the total number of requests to our endpoints and on the right hand side we see the duration. So as you can see here, in the legend, predict live data. This is the endpoint we called right now in yellow, and it happened right now at 1532, we had an API call, and we also got the duration which was around 1.31 seconds.
  
  01:33:04 So, using the same kind of API logic, I would like to show you also our model training, which is a pre-simplified example here because we only call the training directly, so we don't do the whole evidently path because this will be out of scope for the demonstration here. If I hit the button right now, manually, it will check if we have any raw data locally, which is new, so it doesn't fit the data split we have at the moment which the model was trained in the previous model. If we have any raw data, so we have to remerge it again with our old data and then we have to split it and pre-process it and train the model again, validate it, and return the metrics. So, at the moment, if I just press the button so it checks for the new DVC split, and as the process split we had here, matches the newest rawest data I had here locally, then there was no new data ingestion or merging and there was no new train split, so we only used the already trained model, and we validated it on the hand out splits, and we get all the metrics back.
  
  01:34:14 So, this endpoint would be interesting for more for engineers, ML engineers to train the model, not really for the main customer as in the prediction model.
  
  01:34:24 And also to prove that the endpoint was called because we also have a train endpoint for our pipeline. Now, you can see here in the blue that at 1533, in the left hand side panel, also rendered from Grafana, we got an API call and also that duration here which took about 2.42 seconds.
  
  01:34:42 Now that I showed you the two examples, so pretty simple demos because the airflow tags on were out of scope. I would go back to the presentation and conclude our work where we had a pre-good base ML Ops pipeline.
  
  01:34:58 From data versioning, code versioning, model versioning and so on, using ML flow, model serving to the customers through API endpoints and monitoring through Grafana and everything.
  
  01:35:15 We have a good ML ops pipeline, which is a local demo which runs on our laptop. So, to actually make it scalable and more robust and serve thousands of customers, we need a bit more steps.
  
  01:35:29 So, the first one will be using Kubernetes for scalability to run a more resilient API. So, by calling more replicas of our API or machine learning model docker containers and so on, when they fail, we can restart any other, so we always can serve our customers, and we also can increase capacity as the live traffic grows from thousands to 10,000 customers and so on.
  
  01:35:56 And also, we used XGBoost in our training, which is quite an old model, pretty good for the time series prediction, but many things happened since then, so we had neural networks, we had Transformers which are also really good for time serieses and then recently large language models and with one new emergent of system one models in for example Jeff from Typesafe AI, which are large language models which take in text, but output the probability and the confidence which could help in classification type of text.
  
  01:36:28 So it will be quite interesting to maybe employ that in such a pipeline.
  
  01:36:33 I know it will be a bit more expensive maybe, because we have to pay for the input token, but the output tokens are for free. So, we have just have to handle input token costs and some a bit more delay maybe because the model is heavier.
  
  01:36:45 And then of course, to make it a full pipeline, we also have to do the rollout a bit better.
  
  01:36:51 At the moment, we promote our champion or the candidate to the champion merely by the metrics, which is okay at the moment.
  
  01:36:58 On our validation set.
  
  01:37:01 But maybe it fails in the future if new data arrives and so on.
  
  01:37:04 So, maybe a more canary release would be better, if we wrote a percentage of our traffic to the new candidate, monitor it for a while and if it works well, then we promote it to the new production model and we can cut off the old one, or we use something like a shadow evaluation rollback.
  
  01:37:23 Where we also start the new candidate model or the new promoted champion through metrics, we run it in parallel and also run the traffic through it and only monitor.
  
  01:37:34 And if the metrics are fine on the production data, then we promote it to the new production one and then we can move remove the old production model, or if it fails, we can roll back safely and we use the old production model, so it doesn't make any difference then.
  
  01:37:51 So, with that said, we laid a good path from our local demo to run for production scalability, using those four points. Of course, there are many other smaller ones, but those are the major ones I would mention here.
  
  01:38:06 And thank you for your attention and if you have any questions, please let us know and we are happy to answer.
  
  01:38:14 Yes, I think we were a bit fast, but I think it's also good.
  
  01:38:20 No, we are one minute and a half over the time but it's perfectly okay.
  
  01:38:27 Thank you for the presentation.
  
  01:38:29 It was pretty clear and project also seems really well done.
  
  01:38:35 You covered a lot of different things like from the CICD pipeline and also collecting live new fresh data and so that was really interesting.
  
  01:38:44 And I do have a few questions.
  
  01:38:48 So, first just to have an idea on how you thought the thing in real life when a retraining occurs, do you retrain the model on the whole data that you have collected or maybe you thought about strategy to only select a specific amount of data like what happens currently and how would you see it being done in real life in production for example?
  
  01:39:16 If you collect data every day, the impact of the new data is going to be smaller and smaller every time you do it.
  
  01:39:25 So we did, we put a cut off at five years training set and then 90 days, 90 days for test evaluation.
  
  01:39:34 Okay.
  
  01:39:35 Okay, so that's what we call pretty much a sliding window strategy.
  
  01:39:39 And also you can well it will help then with the saving costs, saving resources, saving training time and also have you tested or have you done some experiment on something to see if it performs better?
  
  01:40:00 For example, over the different seasons or because of global warming, the data changes over time. Have you seen a really real difference between data that were almost 10 years ago and right now, or is it that you decided that this strategy was a logical and you have then you go with this strategy and no further testing or experiments? Have you really considered something, or is it pure logic to you that you should go with this strategy and not another one?
  
  01:40:36 We discussed it also internally on restoring the data for a longer time. We retrain only after capturing two or three months of new data then we test it.
  
  01:40:46 So and as everything is parameterizable on our side. So like I said everything is configuration file so we could easily set up a kind of regression test scenario, checking different scenarios like one week new data or one month new data and so on and so forth and then keep checking the output score for each one of these a strategy and to choose one.
  
  01:41:08 I think the biggest deviation we saw Kian was really to change the locations because we started with Australian which was very sunny place and then when we switch it to Singapore was the other extreme.
  
  01:41:19 And I think moving forward would be also nice to have something in the middle and maybe to take another country which is maybe half-half, and then see how the model behaves and also adapt to the model accordingly.
  
  01:41:30 Because we saw some improvements by also considering the Singapore data and eventually we could also improve a little bit more taking more countries into account.
  
  01:41:40 Or we could also reduce the training data set and then use a bigger portion for the validation and for the test part.
  
  01:41:49 I'm sure the results would be a little bit different, but I think everything is possible it's just matter of setting up the regression test scenario and then change the configuration files accordingly and let it run for a couple of hours to see the output.
  
  01:42:07 And where, speaking about evaluate the model, have you thought about a way to evaluate your model on live data, and for example evaluating your model frequently instead of retraining every time, maybe based on the evaluation, then it will trigger retraining, but I don't know it's just some ideas but have you thought about a way of evaluating your model on live data?
  
  01:42:29 This is how we do that, we keep adjusting with air flow new data but for time, because one data point, like one day is not enough, and we also have delayed labeling because we predict the tomorrow.
  
  01:42:43 So we have a time snapshot over a week or a month or maybe a season and then we have N minus 1 days because the last day is a new data point we don't have yet, and then we check with evidently if there is a data distribution drift or also performance of the model drift.
  
  01:43:00 And only if there's a performance drift and we have enough data then we retrain.
  
  01:43:08 Just those two points. But because if you only have one day, one extra day, it wouldn't make sense to retrain the whole model.
  
  01:43:17 If it's there.
  
  01:43:20 Okay, and then what you do is predicting the next days, and then when as the day goes by, you compare the real data to the prediction, right?
  
  01:43:26 We keep logging and then in the next day we actually then check the new data, was it really this way or not and then basically go on.
  
  01:43:34 Okay, well.
  
  01:43:36 So as we go, take data and Okay, well, that's really great approach.
  
  01:43:42 So again, congrats with this project.
  
  01:43:44 I will let Sebastian ask their question if you have some.
  
  01:43:48 Sebastian, your flow.
  
  01:43:50 Thank you very much.
  
  01:43:53 Your work was really interesting, you covered lots of different things.
  
  01:43:57 So, you have a work in prototype, you're using supper base.
  
  01:44:00 You have a complete MVP using ML ops.
  
  01:44:04 So my question would be, I didn't maybe you mentioned it but I'm not sure that I followed the right track, but is your API secure, because I'm not sure I've seen some authorization and notification somewhere.
  
  01:44:19 Yes.
  
  01:44:20 Gabriel, the basic security stuff and we also used EngineX for HTTP to HTTPS and also our private API is so we have a public API through EngineX and only the local like predicting everything is private.
  
  01:44:33 So in our local network kind of.
  
  01:44:37 And basic authentication also with I think user, I don't know what Gabriel you We have authentication as well.
  
  01:44:44 So we authenticate also the first API, so all the endpoints before using it.
  
  01:44:49 So it's also secure on that level and we only expose EngineX entry point as a gateway.
  
  01:44:56 So everything goes through it.
  
  01:44:58 And then we can also limit the number of requests per second for any endpoint and also for the training part which is quite expensive.
  
  01:45:05 And everything is parameterizable.
  
  01:45:10 It's just some configuration files that we can easily change.
  
  01:45:13 And we Also, the demo I showed right now, sorry.
  
  01:45:16 The demo I showed right now was also through EngineX.
  
  01:45:19 So it wasn't something, it was running local, but through EngineX we called our API.
  
  01:45:24 Sorry to all us.
  
  01:45:25 And one more thing.
  
  01:45:26 And additionally, with also some small tricks like for the metrics endpoint, no, so the our clients shouldn't reach it, so it's not access denied, it's more than a 404, not found.
  
  01:45:37 So also some small tricks.
  
  01:45:38 Except.
  
  01:45:40 Because when I saw your demo and you didn't authenticate during the demo, so this is why I was asking the question.
  
  01:45:49 Lack of time.
  
  01:45:50 We can show you this live.
  
  01:45:52 So this is why I asked the question because there on the demo I didn't see any action about that.
  
  01:45:56 But yeah.
  
  01:45:58 Second question would be, do you are dealing do you deal with private information through your application?
  
  01:46:09 No.
  
  01:46:10 Are you sure?
  
  01:46:13 What do you mean precisely, Sebastian?
  
  01:46:15 Are you working or working with private information private data in your application at all?
  
  01:46:23 No, the only thing would be the login data, but not the weather data.
  
  01:46:27 The training data is not private.
  
  01:46:33 But sensitive, not sensitive, but Do you know that when you are using a browser, the browser attached some type of information about you like the browser that you are using, maybe some information about the IP or stuff like this?
  
  01:46:49 Yeah, but this is based on the handle with cookies, right?
  
  01:46:53 And we don't start any cookie information in our database.
  
  01:46:56 So we are totally protecting in that regard.
  
  01:47:00 The only thing we checked.
  
  01:47:02 Sorry.
  
  01:47:04 Now go ahead, go ahead.
  
  01:47:05 No, the only thing we check, like we said is they are authenticated the user, so we don't expose any endpoint without the authentication.
  
  01:47:08 So if the authentication fails, the user has no access to any endpoint.
  
  01:47:13 Cannot use the APIs and also cannot train the model, so this is the only protection we have.
  
  01:47:18 And basically, to authenticate the users, we don't need to store any cookies information, anything coming from the browser.
  
  01:47:23 We are not using any cookies information there as well.
  
  01:47:30 But nonetheless, I think you need a bit of transparency because when people are using your application, they don't know that you are not saving anything.
  
  01:47:38 And from experience, if you just say to people, here's the platform, just use it, but we don't do anything, and this is not written anywhere, they will not use it because they are always thinking, maybe they are doing some stuff and it is a big where that it is free, so I will not use it because I don't know exactly what is going on behind the scene.
  
  01:47:59 So, the GDPR imply a bit of transparency, like clearly saying that, you will use it and we don't do it.
  
  01:48:06 And of course, you need to show some proof about that if you get audited, etc.
  
  01:48:12 But this is small implementation, but that kind of solve a lot of kind of question that user might have.
  
  01:48:19 I think it's the cookie thing that happens in the beginning, like when you open the website.
  
  01:48:23 It's like, "we use cookies, we do statistics."
  
  01:48:25 This is for transparency, so you can just show something like this, but saying, you don't, you're not saving nothing from you and you're free to use.
  
  01:48:34 And so that they have like a legal disclaimer.
  
  01:48:37 Exactly.
  
  01:48:38 So that they know the legal basis on which you're operating and they know how to kind of exercise their right, etc.
  
  01:48:44 So, this is important, especially in Europe.
  
  01:48:48 Not in the other part of the world, but in Europe.
  
  01:48:51 The only exception would be if we want to track also the analytics, right?
  
  01:48:55 So how many users access the points and so on and so forth.
  
  01:48:58 So we have also to disclaim that we are using Google Analytics or any other technology to capture this information and also to process internally.
  
  01:49:05 But this is I think would be the point when we bring to production, right?
  
  01:49:10 And then we have to write also the terms of use and conditions and all these things.
  
  01:49:13 So, it's part of the whole process.
  
  01:49:18 Yes, building an MVP just like this is okay.
  
  01:49:22 But the moment where we need to click on a button and have a lot of bunch of people using the application, usually we start thinking about this little thing because it is important.
  
  01:49:33 You mentioned in the end that you could use Jeff.
  
  01:49:36 So, how would you use Jeff?
  
  01:49:38 I think I would fine-tune it with a bit so to take like some couple of contacts like the humidity and so on like it will be I think it's the state part of Jeff and then the question like "will it rain tomorrow?"
  
  01:49:49 So basically this is kind of set in stone.
  
  01:49:52 And then the choice would be just a I think it would be a null yes or no.
  
  01:49:59 And then
  
  01:50:00 The output. I think I would take open material data, take some kind of they don't solve. Then use unsloth to kind of or Laura to a bit fine tune the model, so it set and stone. And then the prediction output would be all for classification in the confidence.
  
  01:50:16 This could be an idea. I never tried it, but this could be an idea to do like uses small model and then unsloth.
  
  01:50:26 You can try and since knowing the, we have like a bunch of open source variation of that, of course, Jeff is kind of still the leader but you have layer, you have, you have lots of a bunch of different options nowadays.
  
  01:50:39 So, you can try and see how it goes. Thank you very much for. I would zero shot it. I would zero shot it maybe first and see if it works and if not, then fine tune it.
  
  01:50:48 That's a good idea.
  
  01:50:50 Inclusive work, thank you very much for your presentation.
  
  01:50:54 Thank you. Concrats for the projects. We're all done.
  
  01:50:56 Thank you, everyone. I think we can then conclude this meeting. Congrats to all the groups that presented their project today. And again, if you need anything, do not hesitate to contact me directly via DM on Slack or your program manager or directly on your channel. Just as I said to the others, focus on completing the monetary exam that you still need. If it's done well, congrats. You're now in vacation, in a rest that's that was well merited, like needed, maybe for some of you. I'll probably contact you to give you all the information saying, "okay, hey, I did the first check, everyone has completed the thing." You should have received everything by email. But, as long as you have completed the right amount of monetary exams, you should receive everything by email that's notification and this kind of stuff. And again, if you need anything, do not hesitate to contact me on Slack directly via DM or your program manager. And, again, congrats to everyone. You all did a good job.
  
  01:51:54 Thank you. See you soon. Have a great day, and bye-bye.
  
  01:52:00 Thank you, all. Bye-bye.
  
  01:52:03 Thank you, bye-bye.
  
  01:52:04 Thank you.
  
  01:52:06 Thank you. Bye.

── Notes ───────────────────────────────────────────────────────────────
  (no notes)


_Auto-imported from Spark (meeting ID 82419). Source: Spark Desktop, imported 2026-10-15._
