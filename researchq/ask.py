# from researchq.sonar_query import query_sonar_structured  # Function doesn't exist
from typing import Optional
# from researchq.storage import QueryStorage  # Commented out since it doesn't exist
from pydantic import BaseModel
from string import Template
from typing import Type
from abc import ABC
from researchq.classes import Answer, StorageProvider, QueryHandler, Question, QuestionSet, QueryResponse

from typing import final
import asyncio

@final
class Workflow:
    def __init__(self, query_handler:QueryHandler, storage: Optional[StorageProvider]=None, workers=2):
        self.storage = storage
        self.query_handler = query_handler
        self.max_workers = workers

    async def ask(self, question: Question, overwrite:bool = False) -> Answer:
        response = None
        
        if self.storage and not overwrite:
            response = await self.storage.get_response(question)
            if response is not None:
                print("Found cached response")
                if response.error:
                    print("Cached response has error, flushing:", response.error)
                    response = None
                else:
                    print("Using cached response")
                    print(response)

        if response is None:
            prompt = question.value
            response = await self.query_handler.query(prompt=prompt)
 
        assert response is not None
        assert isinstance(response, QueryResponse)
        if self.storage:
            await self.storage.save_response(question, response)

        answer = self.answer_from_response(question, response)
        return answer

    async def ask_questions(self, question_set: QuestionSet, overwrite:bool=False):
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_question(question):
            async with semaphore:
                question.response_model = question_set.response_model
                return await self.ask(question)

        tasks = [process_question(q) for q in question_set.get_questions()]
        for coro in asyncio.as_completed(tasks):
            answer = await coro
            yield answer

    def answer_from_response(self, question: Question, response: QueryResponse) -> Answer:
        if not response.error:
            assert response.full_response is not None
            fields = self.query_handler.extract_fields(response.full_response)
        else:
            fields = {}
        answer = Answer.from_question(question, response.full_response, fields)
        return answer