# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import urllib.parse
import urllib.request
import base64
import json
import easyocr
import openai

from datetime import datetime

from recognizers_number import recognize_number, Culture
from recognizers_date_time import recognize_datetime

from botbuilder.core import (
    ActivityHandler,
    ConversationState,
    TurnContext,
    UserState,
    MessageFactory,
)

from botbuilder.schema import (
    ActivityTypes,
    Attachment,
    Activity,
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
        openai.api_key = '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'

    async def on_message_activity(self, turn_context: TurnContext):
        # Get the state properties from the turn context.
        profile = await self.profile_accessor.get(turn_context, UserProfile)
        flow = await self.flow_accessor.get(turn_context, ConversationFlow)
       
        if (turn_context.activity.attachments and len(turn_context.activity.attachments) > 0):
                print("has attachment")
                await self._handle_incoming_attachment(flow, profile, turn_context)
        else:
                print("no attachment")
                await self._fill_out_user_profile(flow, profile, turn_context, skillset = "")
                # # Save changes to UserState and ConversationState
                await self.conversation_state.save_changes(turn_context)
                await self.user_state.save_changes(turn_context)
                #await self._handle_outgoing_attachment(turn_context)
        

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
                await turn_context.send_activity(
                    f"Attachment {attachment_info['filename']} has been received to {image_path}"
                )
              
                try:
                    # Perform OCR, predict categories, and career choices
                   await self._perform_ocr_and_predict_categories(image_path, flow, profile, turn_context)
                except Exception as e:
                    print(f"Error: {str(e)}")

                # Print the extracted text
                # await turn_context.send_activity(
                #     f"Attachment {extracted_text}"
                # )
                # await self._fill_out_user_profile(flow, profile, turn_context)
                

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
            await turn_context.send_activity(
                MessageFactory.text("Let's get started. What is your name?")
            )
            flow.last_question_asked = Question.NAME

        # validate name then ask for age
        elif flow.last_question_asked == Question.NAME:
            validate_result = self._validate_name(turn_context.activity.text.strip())
            print(validate_result)
            # if not validate_result.is_valid:
            #     await turn_context.send_activity(
            #         MessageFactory.text(validate_result.message)
            #     )
            # else:
            profile.name = validate_result.value
            await turn_context.send_activity(
                MessageFactory.text(f"Hi {profile.name}")
            )
            await turn_context.send_activity(
                MessageFactory.text("Please upload your latest CV")
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
                validate_result = self._validate_name(turn_context.activity.text.strip())
                profile.date = validate_result.value
                await self._get_career_prediction_prompt(profile.date, skillset, turn_context)
                # await turn_context.send_activity(
                #     MessageFactory.text(
                #         f"Your cab ride to the airport is scheduled for {profile.date}."
                #     )
                # )
                # await turn_context.send_activity(
                #     MessageFactory.text(
                #         f"Thanks for completing the steps {profile.name}."
                #     )
                # )
                

    async def _perform_ocr_and_predict_categories(self, image_path, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext):
        # Perform OCR using EasyOCR
        reader = easyocr.Reader(['en'])
        result = reader.readtext(image_path)

        # Concatenate extracted text into a single string
        extracted_text = ' '.join([detection[1] for detection in result])

        # Print the extracted text
        print("Extracted Text:")
        print(extracted_text)

        prompt = f"From the given below text (OCR model predicted text), give me two categories in pointers; one reflecting Skillset of a person and the other with certifications. Mention all the skills and certifications under respective categories without missing any. Keep it crisp and on point. The text is: {extracted_text}"

        explanation = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role":"system", "content": f"{prompt}"}
        ]
        )

        messages = explanation.choices[0].message
        print(messages.content)

        # Get predicted categories
        predicted_categories = explanation.choices[0].message.content.strip().split('\n')

        # Extract skillset from predicted categories
        skillset = [category.strip() for category in predicted_categories[0].split(':')[1].split(',')]

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
        # Print formatted career predictions
        await turn_context.send_activity(
                    MessageFactory.text(
                        f"Predicted Career Choices: ."
                    )
                )
        # print("\nPredicted Career Choices:")
        if career_predictions:
            await turn_context.send_activity(
                    MessageFactory.text("Based on the skill set of the individual in", domain_of_interest + ", potential career choices may include:"))
            for i, prediction in enumerate(career_predictions, start=1):
                await turn_context.send_activity(
                    MessageFactory.text(prediction))
            await turn_context.send_activity(
                    MessageFactory.text("\nThese career options leverage the core skills and knowledge in", domain_of_interest + ", and provide opportunities to work on a variety of projects in different industries."))
        else:
            await turn_context.send_activity(
                    MessageFactory.text("No career predictions available."))

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
