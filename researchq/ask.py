from researchq.sonar_query import query_sonar_structured
from typing import Optional
from researchq.storage import QueryStorage
from pydantic import BaseModel
from string import Template
from typing import Type
from abc import ABC
from classes import Answer, StorageProvider, QueryHandler, Question, QuestionSet

from typing import final

@final
class Harness:
    def __init__(self, query_handler:QueryHandler, storage: StorageProvider):
        self.storage = storage
        self.query_handler = query_handler

    async def ask_question(self, question: Question) -> Answer:
        response_model: Type[BaseModel] = question.response_model
        prompt = question.get_string()
        response = await self.query_handler.query(prompt=prompt, response_model=response_model)
        full_response = response.full_response
        self.storage.save_response(question, response.full_response)
        
        self.query_handler.extract_fields(full_response)
        answer = Answer.from_question(question, response.full_response)
        return answer

    async def ask_question_set(self, question_set: QuestionSet, storage: Optional[QueryStorage] = None) -> list[Answer]:
        word_set_keys = list(question_set.word_sets.keys())

        answers = []
        for question in question_set.get_questions():
            question.response_model = question_set.response_model
            answer = await self.ask_question(question)
            answers.append(answer)
            if storage:
                await storage.save_query(question, answer)
        return answers