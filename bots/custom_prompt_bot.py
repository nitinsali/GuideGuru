# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import urllib.parse
import urllib.request
import base64
import json
import easyocr
import openai
import json
import asyncio
from datetime import datetime, timedelta

from recognizers_number import recognize_number, Culture
from recognizers_date_time import recognize_datetime

from botbuilder.core import (
    ActivityHandler,
    ConversationState,
    TurnContext,
    UserState,
    MessageFactory,
    CardFactory,
)

from botbuilder.schema import (
    ActivityTypes,
    ActionTypes,
    Attachment,
    Activity,
    CardImage,HeroCard, ChannelAccount, CardAction
)

from data_models import ConversationFlow, Question, UserProfile


class ValidationResult:
    def __init__(
        self, is_valid: bool = False, value: object = None, message: str = None
    ):
        self.is_valid = is_valid
        self.value = value
        self.message = message


class CustomPromptBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        if conversation_state is None:
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. user_state is required but None was given"
            )

        self.conversation_state = conversation_state
        self.user_state = user_state

        self.flow_accessor = self.conversation_state.create_property("ConversationFlow")
        self.profile_accessor = self.user_state.create_property("UserProfile")
        openai.api_key = 'sk-UD6v6M1c55rfaA8cOTTwT3BlbkFJKXhzXqxsbdX2vLOEEEM'

    async def on_members_added_activity(
            self, members_added: ChannelAccount, turn_context: TurnContext
        ):
        hero_card = HeroCard(
            title="Welcome aboard! 🌟 ",
            images=[
                CardImage(
                    url="https://img.freepik.com/free-vector/conversation-chat-bot-screen-phone-customer-tiny-man-talking-with-cute-robot-online-messenger-flat-vector-illustration-chatbot-ai-virtual-support-social-media-concept_74855-24047.jpg"
                )
            ],
            text="Let's unlock your potential together. Explore new skills, take assessments, and discover personalized learning paths right here in Teams!",
            buttons=[
                CardAction(
                    type=ActionTypes.im_back,
                    title="Get Started",
                    value="I am Interested!",
                )
            ],
        )

        # Create a message activity with Hero card attachment
        message = Activity(
            type='message',
            attachments=[CardFactory.hero_card(hero_card)]
        )
    
        # Send message activity
        await turn_context.send_activity(message)
       

        # milestones = [
        #     {"name": "Complete Task A", "completed": False},
        #     {"name": "Submit Report B", "completed": False},
        #     {"name": "Attend Meeting C", "completed": False}
        # ]

        # # Create Adaptive Card with milestone list
        # card_json = {
        #     "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        #     "type": "AdaptiveCard",
        #     "version": "1.3",
        #     "body": [
        #         {
        #             "type": "TextBlock",
        #             "text": "Milestone List",
        #             "weight": "Bolder",
        #             "size": "Medium",
        #             "wrap": True
        #         }
        #     ],
        #     "actions": []
        # }

        # # Add milestones with checkboxes to the Adaptive Card
        # for milestone in milestones:
        #     card_json["body"].append({
        #         "type": "ColumnSet",
        #         "columns": [
        #             {
        #                 "type": "Column",
        #                 "width": "auto",
        #                 "items": [
        #                     {
        #                         "type": "Input.Toggle",
        #                         "id": milestone["name"],
        #                         "title": "",
        #                         "value": milestone["completed"]
        #                     }
        #                 ]
        #             },
        #             {
        #                 "type": "Column",
        #                 "width": "stretch",
        #                 "items": [
        #                     {
        #                         "type": "TextBlock",
        #                         "text": milestone["name"],
        #                         "wrap": True
        #                     }
        #                 ]
        #             }
        #         ]
        #     })

        # # Create button to submit marked items
        # card_json["actions"].append({
        #     "type": "Action.Submit",
        #     "title": "Submit"
        # })

        
        # message = Activity(
        #         type="message",
        #         text="",
        #         attachments=[CardFactory.adaptive_card(card_json)]
        #     )
        # await turn_context.send_activity(message)

    async def on_message_activity(self, turn_context: TurnContext):
        # Get the state properties from the turn context.
        profile = await self.profile_accessor.get(turn_context, UserProfile)
        flow = await self.flow_accessor.get(turn_context, ConversationFlow)
        
       
        if (turn_context.activity.attachments and len(turn_context.activity.attachments) > 0):
                print("has attachment")
                await self._handle_incoming_attachment(flow, profile, turn_context)

        # elif (turn_context.activity.value and "selectedCourse" in turn_context.activity.value):
        #             selected_item = turn_context.activity.value["selectedCourse"]
        #             await self._select_start(flow, profile, turn_context, selected_item)

        else:
                if turn_context.activity.text is not None:
                    print("no attachment")
                    await self._fill_out_user_profile(flow, profile, turn_context, skillset = "")
                    # # Save changes to UserState and ConversationState
                    await self.conversation_state.save_changes(turn_context)
                    await self.user_state.save_changes(turn_context)
                    #await self._handle_outgoing_attachment(turn_context)
                else:
                    if (turn_context.activity.value and "selectedItem" in turn_context.activity.value):
                        selected_item = turn_context.activity.value["selectedItem"]
                        await self._select_start(flow, profile, turn_context, selected_item)

                    elif (turn_context.activity.value and "dateSelection" in turn_context.activity.value.get("type")):
                        start_date = turn_context.activity.value.get("startDate")
                        end_date = turn_context.activity.value.get("endDate")
                        selected_course = turn_context.activity.value["selectedCourse"]
                        if start_date and end_date:
                            await self._get_selected_course_detail(flow, profile, turn_context, start_date, end_date, selected_course)
                        else:
                            await turn_context.send_activity("Please select both start and end dates.")


        
        

    async def _handle_outgoing_attachment(self, turn_context: TurnContext):
        reply = Activity(type=ActivityTypes.message)
        reply.text = "This is an inline attachment."
        reply.attachments = [self._get_inline_attachment()]
        await turn_context.send_activity(reply)

    def _get_inline_attachment(self) -> Attachment:
        """
        Creates an inline attachment sent from the bot to the user using a base64 string.
        Using a base64 string to send an attachment will not work on all channels.
        Additionally, some channels will only allow certain file types to be sent this way.
        For example a .png file may work but a .pdf file may not on some channels.
        Please consult the channel documentation for specifics.
        :return: Attachment
        """
        file_path = os.path.join(os.getcwd(), "resources/architecture-resize.png")
        print("_get_inline_attachment")
        with open(file_path, "rb") as in_file:
            base64_image = base64.b64encode(in_file.read()).decode()
        print(base64_image)
        return Attachment(
            name="architecture-resize.png",
            content_type="image/png",
            content_url=f"data:image/png;base64,{base64_image}",
        )

    async def _handle_incoming_attachment(self, flow, profile, turn_context: TurnContext):
        """
        Handle attachments uploaded by users. The bot receives an Attachment in an Activity.
        The activity has a List of attachments.
        Not all channels allow users to upload files. Some channels have restrictions
        on file type, size, and other attributes. Consult the documentation for the channel for
        more information. For example Skype's limits are here
        <see ref="https://support.skype.com/en/faq/FA34644/skype-file-sharing-file-types-size-and-time-limits"/>.
        :param turn_context:
        :return:
        """

        for attachment in turn_context.activity.attachments:
            attachment_info = await self._download_attachment_and_write(attachment)

            if "filename" in attachment_info:
                # Path to your JPG image
                image_path = attachment_info['local_path']
                
                # response_message = MessageFactory.text("You have wonderful skill set")

                try:
                    # Perform OCR, predict categories, and career choices
                   await self._perform_ocr_and_predict_categories(image_path, flow, profile, turn_context)
                except Exception as e:
                    print(f"Error: {str(e)}")
                

    async def _download_attachment_and_write(self, attachment: Attachment) -> dict:
        """
        Retrieve the attachment via the attachment's contentUrl.
        :param attachment:
        :return: Dict: keys "filename", "local_path"
        """
        try:
            response = urllib.request.urlopen(attachment.content_url)
            headers = response.info()

            # If user uploads JSON file, this prevents it from being written as
            # "{"type":"Buffer","data":[123,13,10,32,32,34,108..."
            if headers["content-type"] == "application/json":
                data = bytes(json.load(response)["data"])
            else:
                data = response.read()

            local_filename = os.path.join(os.getcwd(), attachment.name)
            with open(local_filename, "wb") as out_file:
                out_file.write(data)

            return {"filename": attachment.name, "local_path": local_filename}
        except Exception as exception:
            print(exception)
            return {}

    async def _fill_out_user_profile(
        self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext, skillset
    ):
        user_input = turn_context.activity
        

        # ask for name
        if flow.last_question_asked == Question.NONE:
            hero_card = HeroCard(
            images=[
                CardImage(
                    url="https://img.freepik.com/free-vector/first-step-illustration_23-2150146227.jpg"
                )
            ],
            text="Congratulations on taking the first step towards your learning adventure! 🚀 Let's embark on a journey of growth, discovery, and achievement together. Get ready to unlock your full potential and elevate your skills to new heights!",
            )

            # Create a message activity with Hero card attachment
            message = Activity(
                type='message',
                attachments=[CardFactory.hero_card(hero_card)]
            )
            # Send message activity
            await turn_context.send_activity(message)

            await turn_context.send_activity(
                MessageFactory.text("Ready to showcase your skills and experience? Upload your latest CV")
            )
            flow.last_question_asked = Question.AGE

        # validate age then ask for date
        elif flow.last_question_asked == Question.AGE:
        
            await turn_context.send_activity(
                MessageFactory.text("Please enter your domain of interest:")
            )
            flow.last_question_asked = Question.DATE

      
        # validate date and wrap it up
        elif flow.last_question_asked == Question.DATE:
            if turn_context.activity.text is not None:
                # Call the strip() method on the text attribute
                validate_result = self._validate_name(turn_context.activity.text.strip())
                profile.date = validate_result.value
                await self._get_career_prediction_prompt(profile.date, skillset, turn_context)
            else:
                # Handle the case where text is None
                # For example, you could set validate_result to some default value or raise an error
                validate_result = None 
              
                

    async def _perform_ocr_and_predict_categories(self, image_path, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext):
   
        # Perform OCR using EasyOCR
        reader = easyocr.Reader(['en'])
        result = reader.readtext(image_path)

        # Concatenate extracted text into a single string
        extracted_text = ' '.join([detection[1] for detection in result])


        prompt = f"From the given below text (OCR model predicted text), give me two categories in pointers; one reflecting Skillset of a person and the other with certifications. Mention all the skills and certifications under respective categories without missing any. Keep it crisp and on point. The text is: {extracted_text}"
        
        explanation = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role":"system", "content": f"{prompt}"}
        ]
        )

        # Get predicted categories
        predicted_categories = explanation.choices[0].message.content.strip().split('\n')

        # Extract skillset from predicted categories
        skillset = [category.strip() for category in predicted_categories[0].split(':')[1].split(',')]

        await turn_context.send_activity(
                MessageFactory.text("Wow! 🌟 Your skills are impressive! It's clear that you bring a wealth of expertise and talent to the table. Let's leverage these incredible skills to help you reach your goals and unlock new opportunities for growth and success.")
        )
       
        await self._fill_out_user_profile(flow, profile, turn_context, skillset)
             


    async def _get_career_prediction_prompt(self, domain_of_interest, skillset, turn_context: TurnContext):
       # Call OpenAI to predict career choices
        career_prediction_prompt = f"Given the domain of interest '{domain_of_interest}' and the extracted skillset '{', '.join(skillset)}', predict potential career choices."

        career_prediction_explanation = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role":"system", "content": f"{career_prediction_prompt}"}
        ]
        )

        # Get career predictions
        career_predictions = career_prediction_explanation.choices[0].message.content.strip().split('\n')
        
        # print("\nPredicted Career Choices:")
        if career_predictions:
            domain_str = domain_of_interest

            # Concatenate the string with the rest of the message
            # await turn_context.send_activity(MessageFactory.text(f"Based on the skill set of the individual in {domain_str}, potential career choices may include:"))
            
            # for i, prediction in enumerate(career_predictions, start=1):
            #     await turn_context.send_activity(
            #         MessageFactory.text(prediction))

            card = {
                      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.0",
                        "type": "AdaptiveCard",
                        "body": [
                        {
                            "type": "Container",
                            "style": "default",
                            "backgroundImage": "https://static.vecteezy.com/system/resources/previews/012/433/761/large_2x/aesthetic-colorful-pastel-floral-fluid-abstract-background-vector.jpg",  # URL to a pastel background image
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Predicted Career Choices:",
                                    "weight": "bolder",
                                    "size": "medium",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "emphasis",
                            
                            "items": [
                                {
                                    "type": "ColumnSet",
                                    "columns": [
                                        {
                                            "type": "Column",
                                            "width": "stretch",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": prediction,
                                                    "wrap": True
                                                }
                                            ]
                                        },
                                        {
                                            "type": "Column",
                                            "width": "auto",
                                            "items": [
                                                {
                                                    "type": "ActionSet",
                                                    "actions": [
                                                        {
                                                            "type": "Action.Submit",
                                                            "title": "👍",  # Thumbs-up icon
                                                            "data": {
                                                                "selectedItem": prediction
                                                            }
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                } for i, prediction in enumerate(career_predictions, start=1)  # Dynamically generate item columns with buttons using a for loop
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "default",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"These career options leverage the core skills and knowledge in {domain_str}, and provide opportunities to work on a variety of projects in different industries.",
                                    "size": "medium",
                                    "wrap": True
                                }
                            ]
                        },
                    ],
                    }
               

            # Send a message with the list of predictions using adaptive cards
            message = Activity(
                type="message",
                text="",
                attachments=[CardFactory.adaptive_card(card)]
            )
            await turn_context.send_activity(message)

            
        else:
            await turn_context.send_activity(
                    MessageFactory.text("No career predictions available."))


    async def _get_selected_course_detail(self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext, start_date, end_date, selected_skill):

       # Call OpenAI to show day wise plan
        course_planning_prompt = f"I am planning to learn '{selected_skill}'. Write a day-wise plan starting from '{start_date}' for someone who wants to learn '{selected_skill}' from scratch. The plan should cover the basics of '{selected_skill}', understanding core concepts. Each day should focus on specific topics or tasks to help the learner progress systematically along with the duration of course."
        # print(course_planning_prompt)

        course_planning_list = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role":"system", "content": f"{course_planning_prompt}"}
        ]
        )

        # Get course predictions
        course_planning = course_planning_list.choices[0].message.content.strip().split('\n')
        # print(course_planning)

        hero_card_text = {
                "type": "AdaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Day-wise Plan",
                        "weight": "Bolder",
                        "size": "Large"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"This is a day-wise plan to learn '{selected_skill}' from scratch. Each day covers specific topics to help you progress systematically.",
                        "wrap": 'True'
                    },
                    {
                        "type": "Container" ,
                        
                    }
                ],
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Let's Learn",
                        "data": {
                                 "selectedPlan": course_planning
                            }
                    }
                ]
            }

        # Dynamically populate items
        for planning in course_planning:
            hero_card_text["body"].append({
                "type": "TextBlock",
                "text": planning,
                "wrap": True
            })

        # Create a message activity with Hero card attachment
        message = Activity(
                type="message",
                text="",
                attachments=[CardFactory.adaptive_card(hero_card_text)]
            )
        await turn_context.send_activity(message)

    async def _select_start(self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext, selected_item):

        card_json = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.3",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Your Learning Journey Starts Here!",
                    "weight": "Bolder",
                    "size": "Medium"
                },
                {
                    "type": "Input.Date",
                    "id": "startDate",
                    "title": "Start Date"
                },
                {
                    "type": "Input.Date",
                    "id": "endDate",
                    "title": "End Date"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Submit",
                    "data": {
                        "type": "dateSelection",
                        "selectedCourse": selected_item
                    }
                }
            ]
        }
        message = Activity(
                type="message",
                text="",
                attachments=[CardFactory.adaptive_card(card_json)]
            )
        await turn_context.send_activity(message)


    # async def _generate_day_wise_plan(self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext, start_date, end_date, learning_plan):
    #     # Convert start_date and end_date strings to datetime objects
    #     if start_date is None or end_date is None or learning_plan is None:
    #         raise ValueError("Invalid input. Ensure all parameters are provided.")

    #     # Convert start_date and end_date strings to datetime objects
    #     start_date = datetime.strptime(start_date, "%Y-%m-%d")
    #     end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
    #     # Calculate the total number of days between start_date and end_date
    #     total_days = (end_date - start_date).days + 1

    #     if total_days <= 0:
    #         raise ValueError("End date must be after start date.")

    #     # Calculate the number of days for each task
    #     days_per_task = total_days // len(learning_plan)
        
    #     # Initialize the day-wise plan
    #     day_wise_plan = {}
    #     current_date = start_date
    #     print(learning_plan)
    #     # Distribute tasks evenly across days
    #     for task, task_duration in learning_plan:
    #         day_wise_plan[current_date.strftime("%Y-%m-%d")] = task
    #         current_date += timedelta(days=days_per_task)
        
    #     # If there are any remaining days, assign them to the last task
    #     remaining_days = total_days - sum(1 for _ in learning_plan) * days_per_task
    #     for i in range(remaining_days):
    #         day_wise_plan[current_date.strftime("%Y-%m-%d")] = task
    
    #     await turn_context.send_activity(day_wise_plan)
        
    #     # return day_wise_plan

    #     # # Sample learning plan (task durations for each day)
    #     # learning_plan = {
    #     #     "Task 1": 2,  # Task 1 takes 2 days
    #     #     "Task 2": 3,  # Task 2 takes 3 days
    #     #     "Task 3": 1   # Task 3 takes 1 day
    #     # }

    #     # # Define start date and end date for the learning period
    #     # start_date = "2024-04-01"
    #     # end_date = "2024-04-10"

    #     # # Generate day-wise plan
    #     # day_wise_plan = _generate_day_wise_plan(start_date, end_date, learning_plan)
    #     print(day_wise_plan)

    def _validate_name(self, user_input: str) -> ValidationResult:
        if not user_input:
            return ValidationResult(
                is_valid=False,
                message="Please enter a name that contains at least one character.",
            )

        return ValidationResult(is_valid=True, value=user_input)

    def _validate_age(self, user_input: str) -> ValidationResult:
        # Attempt to convert the Recognizer result to an integer. This works for "a dozen", "twelve", "12", and so on.
        # The recognizer returns a list of potential recognition results, if any.
        results = recognize_number(user_input, Culture.English)
        for result in results:
            if "value" in result.resolution:
                age = int(result.resolution["value"])
                if 18 <= age <= 120:
                    return ValidationResult(is_valid=True, value=age)

        return ValidationResult(
            is_valid=False, message="Please enter an age between 18 and 120."
        )

    def _validate_date(self, user_input: str) -> ValidationResult:
        try:
            # Try to recognize the input as a date-time. This works for responses such as "11/14/2018", "9pm",
            # "tomorrow", "Sunday at 5pm", and so on. The recognizer returns a list of potential recognition results,
            # if any.
            results = recognize_datetime(user_input, Culture.English)
            for result in results:
                for resolution in result.resolution["values"]:
                    if "value" in resolution:
                        now = datetime.now()

                        value = resolution["value"]
                        if resolution["type"] == "date":
                            candidate = datetime.strptime(value, "%Y-%m-%d")
                        elif resolution["type"] == "time":
                            candidate = datetime.strptime(value, "%H:%M:%S")
                            candidate = candidate.replace(
                                year=now.year, month=now.month, day=now.day
                            )
                        else:
                            candidate = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

                        # user response must be more than an hour out
                        diff = candidate - now
                        if diff.total_seconds() >= 3600:
                            return ValidationResult(
                                is_valid=True,
                                value=candidate.strftime("%m/%d/%y"),
                            )

            return ValidationResult(
                is_valid=False,
                message="I'm sorry, please enter a date at least an hour out.",
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                message="I'm sorry, I could not interpret that as an appropriate "
                "date. Please enter a date at least an hour out.",
            )

    def create_loader_attachment(self) -> Attachment:
        card = HeroCard(
            text="Please wait while I'm processing your request...",
            buttons=[],
        )
        return CardFactory.hero_card(card)
