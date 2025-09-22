# from researchq.sonar_query import query_sonar_structured  # Function doesn't exist
from typing import Optional
# from researchq.storage import QueryStorage  # Commented out since it doesn't exist
from pydantic import BaseModel
from string import Template
from typing import Type
from abc import ABC
from researchq.classes import Answer, StorageProvider, QueryHandler, Question, QuestionSet

from typing import final
import asyncio

@final
class Workflow:
    def __init__(self, query_handler:QueryHandler, storage: Optional[StorageProvider]=None, workers=2):
        self.storage = storage
        self.query_handler = query_handler
        self.max_workers = workers

    async def ask(self, question: Question) -> Answer:
        prompt = question.get_string
        response = await self.query_handler.query(prompt=prompt)

        assert response.full_response is not None
        if self.storage:
            await self.storage.save_response(question, response.full_response)
        
        fields = self.query_handler.extract_fields(response.full_response)
        answer = Answer.from_question(question, response.full_response, fields)
        return answer

    # Requires storage to save responses
    async def ask_question_set(self, question_set: QuestionSet):
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_question(question):
            async with semaphore:
                question.response_model = question_set.response_model
                return await self.ask(question)

        tasks = [process_question(q) for q in question_set.get_questions()]
        for coro in asyncio.as_completed(tasks):
            answer = await coro
            yield answer