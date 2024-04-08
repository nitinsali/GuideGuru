#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "d6461019-4923-46af-9f52-f81a0b16486a")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "Hgc8Q~EIJVtFxhv50fdm~oSWLnkF3J.SghLYBcEd")
    GPT4V_ENDPOINT = os.environ.get("GPT4V_ENDPOINT", "https://holmes-genopenai.openai.azure.com/openai/deployments/gpt4-Vision/chat/completions?api-version=2024-02-15-preview")
    GPT4V_KEY = os.environ.get("GPT4V_KEY", "d36dbc6b61154c4c8ca62f2c2cc386a3")
