# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class UserProfile:
    def __init__(self, name: str = None, file: str = None, age: int = 0, date: str = None):
        self.name = name
        self.age = age
        self.file = file
        self.date = date
