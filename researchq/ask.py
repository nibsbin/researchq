# from researchq.sonar_query import query_sonar_structured  # Function doesn't exist
from typing import Optional
# from researchq.storage import QueryStorage  # Commented out since it doesn't exist
from pydantic import BaseModel
from string import Template
from typing import Type
from abc import ABC
from classes import Answer, StorageProvider, QueryHandler, Question, QuestionSet

from typing import final

@final
class Workflow:
    def __init__(self, query_handler:QueryHandler, storage: StorageProvider=None):
        self.storage = storage
        self.query_handler = query_handler

    async def ask_question(self, question: Question) -> Answer:
        response_model: Type[BaseModel] = question.response_model
        prompt = question.get_string
        response = await self.query_handler.query(prompt=prompt, response_model=response_model)
        full_response = response.full_response
        if self.storage:
            await self.storage.save_response(question, response.full_response)
        
        fields = self.query_handler.extract_fields(full_response) if full_response else {}
        answer = Answer.from_question(question, response.full_response, fields)
        return answer

    # Requires storage to save responses
    async def ask_question_set(self, question_set: QuestionSet, storage: Optional[StorageProvider]) -> None:
        for question in question_set.get_questions():
            question.response_model = question_set.response_model
            answer = await self.ask_question(question)
            await storage.save_query(question, answer)