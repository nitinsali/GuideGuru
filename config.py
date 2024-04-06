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
