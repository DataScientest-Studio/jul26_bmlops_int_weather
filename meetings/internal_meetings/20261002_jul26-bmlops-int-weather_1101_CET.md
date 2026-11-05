2026-10-02

## **jul26-bmlops-int-weather**

**Attendees:** Jonathan, Ziad Hemidi, Nicolas Fradin, Gabriel Marchesan Almeida, thomas.maisch1996

### Transcript

Meeting: jul26_bmlops_int_weather
Date: 2026-10-02 11:01 - 2026-10-02 11:34
Participants: Jonathan <jonathanvints@gmail.com>, Ziad Hemidi <ziad.hemidi94@gmail.com>, Nicolas Fradin <fradin.nicolas.pro@gmail.com>, Gabriel Marchesan Almeida <gabriel@marchesan.me>, thomas.maisch1996@web.de
Link: https://sparkmailapp.com/dpl/bl?token=QTpwZXJzb25hbC10ZWFtO0lEOjZlZWRjZTYzLTUzZDktNDRhYS05ODY0LWFhYjY1%0D%0AYTQ0OWM2ZEBTcGFyazszNjE0OTYwNzgy

── Summary ─────────────────────────────────────────────────────────────
  The team should finalize a concise, architecture-led defense, demonstrate prediction and monitoring, and rehearse rigorously while presenting model safeguards and future production steps.
  
  ### Key Points
  
  #### Model and Data Progress
  
  The team strengthened its weather-model baseline and evaluated cross-region drift.
  
  * The team trained an Australian-weather model and tested it against Singapore data; predictions degraded substantially, demonstrating geographic data drift.
  * Retraining on Singapore data improved accuracy, giving the team a concrete drift-and-retraining example for the presentation.
  * A revised Kaggle training pipeline used random-search hyperparameter selection before retraining on the full dataset; the reported ROC AUC was about 0.9 and recall about 0.89.
  * The model’s promotion checks require performance to beat the champion, recall of at least 0.75, and—according to the speaker’s recollection—at least 90 days of data.
  * OpenMeteo rate limits interrupted collection of additional historical data; the team may gather data in batches over several days.
  
  #### Presentation and Demo Structure
  
  Nicola endorsed a concise architecture-led presentation and focused live demonstration.
  
  * The proposed presentation allocates five minutes per presenter, five minutes for the demo, and ten minutes for questions, totaling 30 minutes; Nicola stressed keeping the presentation and demo within the strict 20-minute limit.
  * Nicola recommended placing a high-level architecture diagram immediately after the introduction, showing Docker services and how Airflow, MLflow, Grafana, storage, and databases fit together.
  * The five-minute demo should make a Streamlit prediction, show relevant Grafana monitoring, and briefly demonstrate a drift alert triggering Airflow retraining.
  * Embedding Grafana and MLflow views in Streamlit can reduce screen switching; Nicola confirmed other teams have embedded these interfaces.
  * The team should add a future-work slide covering production hosting, Kubernetes for scalability, API security, additional data sources or databases, Stripe payments, and possible LLM-based prediction.
  
  #### Rehearsal and Feedback Plan
  
  The team set a rehearsal sequence to improve timing before the defense.
  
  * The team proposed finishing the presentation by Wednesday, holding an internal dry run and recording on Thursday, then sending the recording to Nicola through Slack.
  * Nicola offered to review the recording and provide feedback, including during the weekend; the defense date was referenced as the 15th, with the transcript also mentioning the 13th.
  * Nicola warned that the previous data-science presentation ran long: one presenter spoke for seven and a half minutes against a five-minute allocation.
  * Nicola prioritized a clear overview, a working demo, and staying within the allotted time over answering every jury question.
  
  #### Future AI Opportunities
  
  Participants identified structured-output models as a possible future extension, not current scope.
  
  * A participant introduced System 1-style models such as Leia and Jeff, which return structured choices, yes/no outputs, or scores instead of long-form text.
  * Participants highlighted potential uses in binary prediction, software routing, and confidence-based escalation to a human reviewer.
  * Nicola considered the technology promising but advised listing it as future work rather than expanding the current project scope.
  
  ### Action Items
  
  #### Jonathan
  
  * Update the presentation slides with the team’s latest findings.
  
  #### Project team
  
  * Finish the presentation by Wednesday next week.
  * Add an architecture diagram after the introduction and a future-work slide before questions.
  * Complete the Streamlit demo and rehearse it within the time limit.
  * Hold an internal dry run on Thursday, record it, and send the recording to Nicola on Slack.
  
  #### Nicola
  
  * Review the team’s Slack recording and provide feedback.

── Transcript ──────────────────────────────────────────────────────────
  00:03 Hi, good morning.
  
  00:04 Hello Gabriel.
  
  00:04 Morning Nicola.
  
  00:11 Morning.
  
  00:14 Hello.
  
  00:15 Hi Dad, good morning.
  
  00:16 Hi. Good morning.
  
  00:20 Hi, Thomas.
  
  00:36 Let me check just very quickly.
  
  00:42 He's not available.
  
  00:45 So let's start guys. Your next step we have to finish implementing MLflow, continue working on Airflow pipeline, integrate, evidently, reports to Grafana for drift and API monitoring dashboard.
  
  01:01 Continue developing the Streamlit application for the demo and start preparing the slide presentation.
  
  01:10 All right. If you can just tell me what you have done until now and if you succeed to make all of that and we can discuss about everything.
  
  01:24 Maybe I can start with the presentation if you don't mind just to get your confirmation, Nicola, if the structure is the one you are expecting.
  
  01:32 Let me shortly share my screen.
  
  01:37 So let me pick the right one.
  
  01:40 I hope you can see it soon.
  
  01:46 Yes.
  
  01:48 Okay, thanks.
  
  01:49 So what we did Nicola here, we did a Streamlit presentation.
  
  01:55 Of course, we leverage Cloud to do a beautiful layout for us and all these settings.
  
  02:00 But in the end of the day, we want to get a confirmation from you about the topics that we are covering here and if we need to adjust anything around that.
  
  02:14 So the project you know very well.
  
  02:19 So what we did here, Nicola was to give 5 minutes time for each one of us to present its part.
  
  02:24 And then we have 5 minutes of demo, so in total 20 minutes and then we have 10 minutes left for the questions and answers about precise topics.
  
  02:34 And the idea here is that we have some backup slides also for the follow up questions.
  
  02:40 In case they want to go deeper in certain aspects like model, I don't know, training and so on, so forth.
  
  02:48 So this is the kind of information we would like to present during the slides, of course, starting with the Australian CSV files that we are using here, the accuracy of the model that we have observed.
  
  03:06 And also what we did here, Nicola in the last meeting we had internally in our team, we decided also to look for other sets of data, picking up a city or a country which rains a lot, because the Australian, I think most of the test data, I think more than 75% of the data is no rain at all, and we wanted to use a place which rains a lot to detect this drift of the model.
  
  03:34 And then that's exactly what we did, we picked Singapore.
  
  03:38 So we used also the open weather, let's say database, and luckily it's exactly the same columns and parameters that you have in the Australian open weather file, so we didn't have to do any adjustment there, we just used as it is.
  
  03:59 Nice.
  
  03:59 And we also, so we took the Singapore data and we used it in our model trained on Australian data.
  
  04:11 And then of course, we saw a big deviation, so the prediction was not good and so on, so forth.
  
  04:16 And then what I did yesterday, I just did some refining in the training model itself, and I retrained the model based on Singapore data only, and then of course the accuracy is much higher, and this is what we want to present here in this introduction part.
  
  04:34 The pipelines we have here for the training part, for the Can I chime Gabriel, can I chime in also on the model training and so you also add this retraining and so on?
  
  04:43 Some technical parts, so we were thinking last time because of evidently and kind of the model performance drift and so on to rethink the training of the model.
  
  04:53 So what I did depending on the evidently course, I used the Kaggle data, I split it and did a validation model, do a hyperparameter search using random search only.
  
  05:04 Then I set those on stone, the best ones, and then I retrained on the full Kaggle data.
  
  05:10 And this is the first promoted production model or the champion.
  
  05:15 So this should be the best one and there the rock AUC was 0.9, I think.
  
  05:22 And also the guard rail like our recall was around 0.89, almost 90 also.
  
  05:28 So this is more data, was a bit better.
  
  05:30 And then my idea was kind, right now, this is the first champion, and now let's try to fetch from OpenMeteo the gap of those five years or something from 2017 till now or maybe a bit more.
  
  05:44 So this didn't work so good because OpenMeteo cut me off after 600 requests a minute, I think, or an hour.
  
  05:53 So maybe I can do that in batches, so over a couple of days, just get some more data, and then if I have enough, then we can have a bigger training data set again, and then retrain and then do this data drift with evidently and so on.
  
  06:06 So this was kind of my plan with evidently, but I think the baseline model is now a bit better because now we have 10 years of data training from 2007 till 2017, if I'm right.
  
  06:17 So this is also a bit better.
  
  06:20 With the improved model, I then have to change the alerts in Grafana.
  
  06:26 So otherwise, you set your heart set them like 271, or for now.
  
  06:33 Like 75.
  
  06:37 Because it goes for the rock AUC and like if it's better than the champion, and then also it has the guard rail that the recall recall has to be at least 0.75.
  
  06:50 This one it's still there.
  
  06:50 And I think I also put another guard that we have enough data, I think, to retrain the model.
  
  06:57 Also not just two days or three, so it has to be at least, I think I, I think 90 days or something, if I remember right.
  
  07:07 So we also need enough data to retrain, not that we only have two days and then we retrain with those two days.
  
  07:12 That wouldn't make so much sense.
  
  07:15 So three guard rails then, for and then we retraining.
  
  07:19 So that those were the two points I wanted to add for the model training, what I added today and yesterday.
  
  07:25 Fair enough. Thanks.
  
  07:27 You're welcome.
  
  07:29 I think this is super nice.
  
  07:32 And of course, I think it's good to have these meetings with Nicola from time to time because it looks like we are putting all the energies to get the things done, and I think we are pretty close to the end, to be honest with you.
  
  07:45 Of course, there are some refinements that we need to do here and there, especially in the presentation.
  
  07:48 Also, we need to put all these guard rails, right, Ziad because I remember not seeing that, but I think these are minor details.
  
  07:57 Cool.
  
  07:58 And then what we are going to talk about Nicola is the data itself.
  
  08:04 So how we capture the data, how we integrate that in MLflow runs and some informations here for you.
  
  08:12 And you can see in the slides that there is a slide downer there.
  
  08:14 So Jonathan is going to update these slides accordingly to the last findings we had so far.
  
  08:19 And then we hand over to Thomas and also to Ziad.
  
  08:28 For the live demo.
  
  08:28 And Ziad, you had some ideas for the live demo also in the last call.
  
  08:31 I don't know if you want to confirm with Nicola if this is okay.
  
  08:35 I don't know if it works, so I think my idea what your point was, was to put Grafana and kind of this graphs directly and inject them into Streamlit, kind of just render them there.
  
  08:50 I didn't check if it's possible, but I guess it should be because it's only HTML files, I think.
  
  08:56 So, I think you should be able to render them.
  
  08:58 What do you think about this idea when we do the demo that we just render the Grafana dashboards there without switching screens the whole time.
  
  09:07 If they're running in the background, it's totally possible.
  
  09:12 Other groups in the past made that, so you can include the Grafana dashboard, you can also include the UI of MLflow, I don't know for Airflow, but I know that it's possible, so if you can do that, it would be, of course, easier because you don't have to switch between Streamlit, Grafana, switch Streamlit, MLflow, etc.
  
  09:32 That's fine.
  
  09:34 So, for the live demo, we thought that just to show the Grafana stuff and maybe kind of simulate the data drift and alerts and then the retrain, because also what I wanted to do is that the Grafana alerts but then also triggers through a webhook Airflow again, but I think Thomas already did something similar and then does the retraining after all the guard rails pass, that we have enough data and so on.
  
  09:59 Exactly.
  
  10:00 From Grafana we do the Airflow re-trigger for re-train.
  
  10:06 And that we maybe you can simulate that in somehow.
  
  10:08 I think we didn't simulate it.
  
  10:14 But this will be cool to show on the demo as well.
  
  10:16 You have only five minutes for the demo, so of course you can't show everything.
  
  10:21 And showing only the Grafana, showing that you can erase some maybe ideas, trigger airflow.
  
  10:27 Stuff like that, it's good enough.
  
  10:30 And of course, if it's inside the stream, that's good because you're also showing that stream is working.
  
  10:39 And maybe something you can do very quickly, probably, it's to make a prediction.
  
  10:43 Exactly, on the streamlet.
  
  10:46 So just to show that your API and your model is working, that's it.
  
  10:49 Maybe we can do the prediction and then on the side we can also show the Grafana dashboard for the API that there was an API call or something.
  
  10:56 Just, I don't know if you can render just some parts of the dashboard only.
  
  11:01 Maybe just will be also cool.
  
  11:02 Just the API rate limit or whatever or something.
  
  11:05 I don't know.
  
  11:06 I don't really know about that, but probably, I don't know.
  
  11:10 We go over to the Almighty Cloud or ChatGPT.
  
  11:14 I think that Of course.
  
  11:16 I also read about the implementing it in streamlit, and I read that it's not It opens grafana a little bit more, so it's not that secure anymore.
  
  11:24 But I think for presentation, this project is not a big of a concern.
  
  11:29 Right now.
  
  11:32 I think it's fine.
  
  11:35 So I think for the 5-minute presentation is make a prediction show maybe the API calls and then we do this straight retraining kind of to show our triggers in and so on.
  
  11:46 I think this is enough.
  
  11:48 So, I don't know what we should also show.
  
  11:53 Okay.
  
  11:54 Just a question about the presentation here.
  
  11:59 Are you talking about docker and Docker compose stuff?
  
  12:02 Not in the details, not yet.
  
  12:04 Do you think it's worth mentioning that Docker Compose and the different containers we have?
  
  12:11 Maybe you can just tell some words about that, because it's a major part of your architecture.
  
  12:17 I mean, working with Docker is a good pattern, so maybe just tell some words about that to let the jury know that you are using Docker.
  
  12:26 Yeah.
  
  12:27 Maybe just like also an overview like what part is its own Docker container, maybe just for an example, evidently it doesn't have its own Docker container.
  
  12:37 It runs kind of in the main one.
  
  12:40 And MLFlow has its own one, Airflow has its own.
  
  12:42 Just like show the services.
  
  12:45 Exactly.
  
  12:46 We just show our services and then how we run it with docker-compose.
  
  12:50 I think the small slide then.
  
  12:55 Do you have a full architecture diagram somewhere?
  
  12:59 We have in our Wiki.
  
  13:01 That's what I'm trying to pull now.
  
  13:04 I hope you can still see the GitHub.
  
  13:07 The Wiki is up there, yes.
  
  13:11 We just need to bring some of these elements we have here in the wiki to the presentation itself.
  
  13:17 Probably we have to abstract a little bit higher because this is like sequence diagram.
  
  13:22 This is very detailed, but I think showing the overall architecture, the Docker images we have, the Docker containers we have, would be good.
  
  13:33 Probably putting that kind of architecture maybe in the beginning of your presentation part is good because you will give to the jury the full overview directly.
  
  13:47 And so they will directly understand the major part and how the things are orchestrated like why what they are working together.
  
  13:58 And then they will better listen to you explaining the things.
  
  14:03 Because if you don't put such full overview at the beginning, they will try to connect the dot in their mind slide after slide and maybe they will listen less what you are saying.
  
  14:15 My recommendation is to put that architecture at the very beginning after the introduction for example and on that diagram, you can also put a lot of logos like Docker logos, Airflow logos, MLFlow logos to very quickly understand what is about.
  
  14:37 And then you can develop and going deeper element per element in the further slides.
  
  14:45 It's a very good hint because I think at the moment they start asking questions.
  
  14:50 I think it's also good to go to this baseline slide with the overall architecture and then they can say, "hey, give me more information about your Grafana setup, how this talks to that element and so on and so forth."
  
  14:59 I think it's a very good idea to have a starting point for discussions.
  
  15:04 And maybe also to show also what we have in Superbase and so because this is like kind of part of our pipeline like that it's the Volt.
  
  15:11 It's the S3 buckets and it's the database and what are we saving?
  
  15:16 I think it's kind of in this description already like data versions and so on.
  
  15:19 It's the database.
  
  15:21 Well, maybe also the volt stuff that we also have a volt on super base for the environment variables.
  
  15:31 Other question.
  
  15:33 Do you have a next step slide?
  
  15:37 No.
  
  15:39 At the end of the slide?
  
  15:41 Not yet.
  
  15:42 No.
  
  15:43 We jump straight to the live demo and then here it is.
  
  15:47 Basically, what we have not build, but this is in should be empty.
  
  15:51 But evidently, I think it's not up to date yet because we have already evidently in place.
  
  15:56 We just need to update these slides and then we jump into the questions.
  
  16:00 Do you recommend us to insert?
  
  16:01 Probably before the questions slide, you could just put some keywords as a next step, just to show to the jury that you anticipate maybe a bit what you have to do after the defense, if you had to continue or if you want to continue the project, just for going for real into production.
  
  16:22 So can I say the biggest next step is at Stripe and sell the money.
  
  16:29 That could be one.
  
  16:31 You can also talk about or just not talking, but just saying the word Kubernetes, you can talk about Cloud, AWS and stuff like that.
  
  16:41 And it's very nice that you mentioned that Nicola, because in the last internal call, we also talked about including something with Kubernetes or not, because I think none of us back then, we finished the Kubernetes training.
  
  16:53 Now I just started and do you think would be good that we add this Kubernetes orchestration layer on top of the Dockers, for the scope of this work?
  
  17:00 It's a bit out of scope because Kubernetes is more DevOps thing and it's pretty complex as a tool.
  
  17:13 So, it's not expected for you to make Kubernetes in this project.
  
  17:16 If you want to make it, that's a good bonus, but for me, you can just keep it as a next step.
  
  17:21 Just get some words at the end of the presentation saying that maybe next major next step is put Kubernetes in the project in order to prepare for the real production scalability and stuff like that.
  
  17:36 Exactly.
  
  17:37 For scalability.
  
  17:39 Because right now we only need one API, kind of docker running.
  
  17:44 Maybe later we need many more if some of them fail.
  
  17:47 Exactly.
  
  17:49 And then you can also add a lot of things like API security or I don't know, adding more databases, plugging into real API for the weather data, I don't know.
  
  18:02 There is a lot of things you can do and it's just for showing to the jury that you anticipate a bit the next step and what you could do to improve your application.
  
  18:14 And I think one steps would be to really host it somewhere, because it's just running on the laptop.
  
  18:20 Maybe just a host then we scale it Kubernetes and then at the end we instruct.
  
  18:24 We add stripe so people can pay also for.
  
  18:27 Exactly.
  
  18:28 For each call.
  
  18:30 That's a good run map.
  
  18:35 And slide of question after it.
  
  18:39 It's good.
  
  18:41 Then we would before questions, we would jump into demo and then come back to. Sure.
  
  18:48 What still needs to do, like future work and then questions, I think.
  
  18:55 That's good.
  
  18:56 Do we have something in mind to tell you?
  
  19:01 No, just about the question.
  
  19:04 The question part of the defense, it's not the most important.
  
  19:09 So, maybe you won't have any question, maybe you have some.
  
  19:13 You're going to have some, but even if you don't have the answer to some question, that's fine.
  
  19:17 You can say, "I don't know, I will check that later, it's interesting, blah, blah, blah."
  
  19:21 But that's not the most important.
  
  19:23 The most important is making a good presentation for the jury to have a clear overview of what you have done, and a good demo to show that everything is working well.
  
  19:30 And then you have the questions, but again, it's not the most important.
  
  19:35 I think that's good.
  
  19:36 I think for me the slide are pretty good.
  
  19:39 The demo sounds good.
  
  19:43 So, just make sure to fit into the 20 minutes, but the most I think the most important thing, because they are pretty strict hard on that.
  
  19:55 So, maybe practice a bit to do the presentation plus demo.
  
  20:00 Make
  
  20:00 Sure that it's fitting into the 20 minutes, probably 21, not more than 22, and then they will stop.
  
  20:09 So, I think that the most important recommendation I can do for you.
  
  20:13 If you want to tell everything, fit everything in the 20 minutes and then everything will be fine.
  
  20:21 Can we somehow send it to you after we done before the presentation just to have a look?
  
  20:26 Just give us feedback.
  
  20:28 The problem is it's not a PowerPoint, so let's see how, the easiest way would be just to run the Docker container.
  
  20:35 I don't know if it's too much work also for you to do that.
  
  20:39 It will be just make a demo, I think, or make stream.
  
  20:43 Make Streamlit, make Streamlit, and then it runs.
  
  20:49 We'll do it with make files.
  
  20:52 The thing you can do if you want, is to make a practice together, record yourself and send me the recording on Slack, and I will give you feedback as a fake jury.
  
  21:00 After reviewing your recording.
  
  21:03 And, we can do that if you want.
  
  21:06 That sounds amazing, I think that even sounds better.
  
  21:10 Okay, cool.
  
  21:11 I can set a real meeting because I have lot of meetings next week, but send me your recording on slack directly, and I will make that probably in the evening in the week and I will give you the major feedback I have and if you have something to change.
  
  21:29 Because your defense is on 15th, and 13.
  
  21:34 Okay.
  
  21:36 So we can do that if you want.
  
  21:40 I think the next is really just harden the technical stuff a bit more.
  
  21:44 Finish the Streamlit, and, I think then we should be done kind of, then we can start mid-end next week to record ourselves and then send it to you.
  
  21:48 I don't know about you guys, but maybe this could be the timeline.
  
  21:55 I am also available during the weekend if you want.
  
  21:58 So if you want to send me your recording on Sunday, I can check it very quickly.
  
  22:02 There is no problem for me.
  
  22:05 Amazing, thank you.
  
  22:07 We can set an internal deadline for us, as you the Thomas, for let's say, Wednesday next week to finish the presentation.
  
  22:12 And then we schedule an internal call on Thursday and we record this as a dry run, and then we just share with Nicola afterwards, and then we still have one week to adjust according to Nicola's feedback, before the final jury.
  
  22:26 I think the hardest part for my experience in the first module was really time keeping.
  
  22:30 Because we have a lot of information to share, and sometimes we overdo it, right?
  
  22:35 So we need to do a dry run to make sure that we are within the time boundaries.
  
  22:41 I watched your presentation and the data science part, it was a little bit long.
  
  22:47 Especially myself, I think I took seven and a half minutes, and each one of us we had only five minutes, so I That's I ate more than I should.
  
  22:59 Then we need to train that.
  
  23:02 Yes, we need to train that.
  
  23:04 But anyway, I think it's quite good.
  
  23:07 We are almost done.
  
  23:10 Cool.
  
  23:12 Does any of you have another question?
  
  23:13 Because I would have a off-topic question a bit, which could be also in topic kind of.
  
  23:18 I don't know if somebody else has a question first.
  
  23:20 No.
  
  23:22 No.
  
  23:23 No, okay, so I was thinking last time since a week or something, this from TypeSafe AI, this Jeff model, or now there's an open-source one called Lia came out about the System 1 models.
  
  23:32 So basically LLM models which don't produce tokens or text, they produce predictions, or some kind of null values and so on.
  
  23:39 So, this could be a thing also for this project.
  
  23:42 Just say, maybe we can use LLM models for better prediction.
  
  23:45 And also one question to, did you guys think about adding this one also to the MLM?
  
  23:51 Because this would really change some stuff.
  
  23:53 This could be a judgment LLM or whatever, here real probabilities come out instead of just text tokens and so on.
  
  24:00 So this is quite cool models, I don't know if you played with them.
  
  24:04 There's open source called Lia on Hanging Face, Layal or something, and the TypeSafe Jeff model from typesafe.ai.
  
  24:13 The guy who worked with OpenAI before.
  
  24:16 But the waiting list is full, so I couldn't get my hands on Jeff.
  
  24:20 But you can get Lia, which should be also a bit better in some categories because they did many retrained fine-tuned models and so on.
  
  24:28 Lia is a LLM or Jeff.
  
  24:32 Both are LLMs, kind of, but System 1 models, not System 2 models.
  
  24:37 They don't give you broad text.
  
  24:41 They take tokens in text and they give you only predictions.
  
  24:44 Three types, so you have a choice.
  
  24:47 You have a score, and you have a null.
  
  24:49 Yes, no, probability from zero to 100 or zero to one.
  
  24:54 And there's only three choices you can get.
  
  24:57 So you can use them as a tool selection, probability score or kind of what category should we go in, or maybe just a true/false answer or something.
  
  25:05 Will it rain tomorrow, no, what is the probability and so on.
  
  25:10 And so, are you fitting text directly or three things?
  
  25:16 You're fitting text directly also, because it's also just an LLM or transformer-based model.
  
  25:22 So you have three things.
  
  25:24 You have a state, which is basically context.
  
  25:28 You have a question, where you write out your question in natural language, and then you have a category, I think it's called, which is like the type of answer you want.
  
  25:33 Do you want a choice, do you want a null, which is yes or no, or a score?
  
  25:41 And that's the input you can get.
  
  25:43 Also, I think Open AI, in Python, I think it's called Open AI the package, also has this type safe What were called the Name again? What's the name again on Eating face?
  
  25:53 Lia? Lia L a, A, I think, if I'm right.
  
  26:05 Leia Haging face.
  
  26:08 So that's been kind of a week or something of it that it came out.
  
  26:13 Now, not this one.
  
  26:16 Now, this interface, and I would write System 1 model.
  
  26:21 System 1 model.
  
  26:24 So, yeah.
  
  26:26 Is it this one?
  
  26:29 This is the one.
  
  26:30 Should I send the link into the chat?
  
  26:33 If somebody is interested, pressing.
  
  26:35 Sure.
  
  26:38 I can do that on Slack also.
  
  26:40 Convoy innovation, okay.
  
  26:41 I'll stop sharing my screen here.
  
  26:44 I found the article, so.
  
  26:48 From the Jeff, or from which one?
  
  26:49 From Leia.
  
  26:51 I have Leia AI model, how it works.
  
  26:53 Running locally, and evaluated.
  
  26:57 Exactly, we can also run.
  
  26:59 Oh llama has Leia, I think also right now.
  
  27:03 You can also use those type safe models kind of category, you can call them, or System 1 models.
  
  27:09 That is nice.
  
  27:12 Nice.
  
  27:13 I didn't know about that.
  
  27:16 So, if your question is, would it be interesting for the project?
  
  27:18 I think yes, of course.
  
  27:20 Everything is interesting to test.
  
  27:21 As a future step, basically.
  
  27:23 I think you can put that on next step.
  
  27:27 That seems promising.
  
  27:30 And I think, also for the courses, not for ours now, but maybe for future courses because we talked a lot about LLM models like those system two models, which are pretty heavy and cost.
  
  27:38 We always talk about cost and heaviness.
  
  27:41 Those are really cheap because you just pay for the input token, the output is for free.
  
  27:46 So, this is the, then you run it locally with Leia, then it's free.
  
  27:49 Anyways, it depends on your server, whatever, what you pay.
  
  27:53 But the Jeff from them is only the input token as you pay for, the output is no it's just a score at the end.
  
  28:00 So you pay only for input tokens.
  
  28:03 And they are quite fast, I think 220 to 200 times faster, 40 to 40- I don't know the numbers, they always tell on typesafe.ai, but they are really fast and the way less cost because the output tokens are the expensive ones, I think also from ChatGPT and Claude and so on.
  
  28:21 The output tokens are the ones which cost more.
  
  28:24 I think so, I'm not sure.
  
  28:26 For binary I think.
  
  28:28 Sorry, go on.
  
  28:29 No, you go.
  
  28:31 I was done talking.
  
  28:34 No, I was just about to say, I think for binary prediction it's quite powerful, right?
  
  28:38 Because you don't need a lot of response back, like a normal LLM.
  
  28:43 In the stock market, you also have these binary trading, right?
  
  28:48 Either you buy or sell.
  
  28:52 I think there are many nice use cases that you can leverage out of this technology here, so and it's good to know that all Llama is supporting them because I have a Llama locally started here on my server so I can play around with it.
  
  29:03 But Gabriel, I think you don't see, the bigger picture is, if you have a system or SaaS or something model working with LLM inside, so to make decisions to kind of route, this is the first one where really your code can really work with the output more professionally.
  
  29:17 So you have smart orchestrators kind of, which don't blubber like say, "blah, blah, blah," the whole time.
  
  29:23 They just tell, use this tool, do this, do that.
  
  29:27 They give instructions, and this is way costs expensive and then they're really an AI native software, whatever, could work way better than just like have a blob of text coming out the whole time.
  
  29:37 Like maybe you need a big orchestrator for to writing emails, to write reports and so on, this is okay, but for the real decision making and the interaction with your code base, it's way better to have some kind of probability or categories or something coming out.
  
  29:50 Like that this is what where it's really cool that your software could really run with LLM integrated into it.
  
  29:58 For like
  
  30:00 Routing and everything, this is quite cool. This is what I liked about it, especially in the medical domain right now. If you have some kind of decisions, you want to have Codex structure and whatever, ICD-C codes on. You can use also Jeff for this sort of layout.
  
  30:13 Now you have a probability and a confidence score. As a confidence score, a real one.
  
  30:20 Not just what the LLM tells you, there's a real confidence score, and this is the quite cool part.
  
  30:26 That's nice, because then you can know which risks you are willing to take and which not, to based on the confidence level, right?
  
  30:33 Interesting.
  
  30:33 I mean, you just tell it to the user. The confidence was 50%, so maybe check it again. Then you can, when can I escalate it? What is my threshold? If my confidence was 80, then maybe I don't just give a warning, I don't escalate it. Then you can do an escalation to human based score from real data.
  
  30:53 This is a cool thing.
  
  30:56 I don't know. I just wanted to mention that, maybe you guys are also interested in playing with such models.
  
  31:02 Thank you for sharing, that is. I think very nice. I think to have a look on this stuff as well.
  
  31:10 Alrighty, this was my question.
  
  31:12 Okay, no, that's interesting.
  
  31:14 But of course, I recommend you put that on next step.
  
  31:17 If you want to try before the difference you can, but I don't think we just need to run it locally.
  
  31:25 I think the layer model, without training, just like zero-shot, just give it context, the data and The problem is, I think we need unslot or something to fine-tune it on weather prediction, maybe.
  
  31:40 But I don't know. But we can put it in future work.
  
  31:43 Just like, I maybe try some LLM-based models.
  
  31:50 Okay, so let's do this.
  
  31:55 If you can just record yourself, practice a bit the difference, try to fit into the 20 minutes, apply the very few feedbacks I made today, put a diagram at the beginning, put the next step slide, and stuff like that, and tell me when it's ready, and I will give you feedback then in Slack.
  
  32:16 Okay. Thank you very much.
  
  32:18 Thank you, Nicola.
  
  32:18 Thank you to Adam and Thomas as well.
  
  32:22 And I don't know if I've told you before, but after the defense, I will send you a last message for collecting everything to give you my link profile if you want some recommendation on LinkedIn, if you want just to stay in contact.
  
  32:40 You'll see. Sure.
  
  32:42 A last message will come after the defense, so no worries.
  
  32:46 We stay in touch and maybe you find some jobs for us at Liora.
  
  32:50 Thanks a lot, Nicola.
  
  32:52 Thank you guys.
  
  32:54 Nice afternoon and nice weekend.
  
  32:58 Have a nice weekend.
  
  32:59 Take your beer, Gabriel.
  
  33:00 I need one.
  
  33:02 Thank you.
  
  33:03 Bye-bye, guys.
  
  33:04 Bye-bye, guys.
  
  33:05 Bye-bye.

── Notes ───────────────────────────────────────────────────────────────
  (no notes)


_Auto-imported from Spark (meeting ID 81670). Source: Spark Desktop, imported 2026-10-02._
