# from robora.sonar_query import query_sonar_structured  # Function doesn't exist
from typing import Optional
# from robora.storage import QueryStorage  # Commented out since it doesn't exist
from pydantic import BaseModel
from string import Template
from typing import Type, List, Dict, Any, Callable, AsyncIterable, Optional
from abc import ABC
from robora.classes import Answer, StorageProvider, QueryHandler, Question, QuestionSet, QueryResponse

from typing import final
import asyncio

@final
class Workflow:
    def __init__(self, query_handler:QueryHandler, storage: StorageProvider, workers=2):
        self.storage = storage
        self.query_handler = query_handler
        self.max_workers = workers

    async def ask(self, question: Question, overwrite:bool = False) -> Answer:
        response = None
        
        if not overwrite:
            response = await self.storage.get_response(question)
            if response is not None:
                print("Found cached response")
                if response.error:
                    print("Cached response has error, flushing:", response.error)
                    response = None
                else:
                    print("Using cached response")
                    print(response)

        # If no cached response, query
        if response is None:
            prompt = question.value
            response = await self.query_handler.query(prompt=prompt)
            assert response is not None
            assert isinstance(response, QueryResponse)
            await self.storage.save_response(question, response)

        answer = self.build_answer(question, response)
        return answer

    async def ask_multiple_stream(self, question_set: QuestionSet, overwrite:bool=False):
        semaphore = asyncio.Semaphore(self.max_workers)

        total = len(list(question_set.get_questions()))
        print(f"ask_multiple_stream: starting for {total} questions with {self.max_workers} workers")
        started = 0

        async def process_question(question):
            async with semaphore:
                question.response_model = question_set.response_model
                nonlocal started
                started += 1
                try:
                    print(f"Processing question {started}/{total}: {question.template} - {question.word_set}")
                    ans = await self.ask(question)
                    print(f"Finished question {started}/{total}")
                    return ans
                except Exception as e:
                    print(f"Error processing question {question.template} with words {question.word_set}: {e}")
                    raise

        tasks = [process_question(q) for q in question_set.get_questions()]
        for coro in asyncio.as_completed(tasks):
            answer = await coro
            yield answer

    async def ask_multiple(self, question_set: QuestionSet, overwrite:bool=False, return_results:bool=True) -> List[Answer]:
        """Convenience method to gather all answers into a list."""
        answers = []
        print("ask_multiple: gathering answers")
        try:
            async for answer in self.ask_multiple_stream(question_set, overwrite=overwrite):
                if return_results:
                    answers.append(answer)
        except Exception as e:
            print(f"ask_multiple: encountered error during processing: {e}")
            raise
        print(f"ask_multiple: completed, collected {len(answers)} answers")
        return answers

    def build_answer(self, question: Question, response: QueryResponse) -> Answer:
        if response is None:
            response = QueryResponse(error="No response")
        if not response.error:
            assert response.full_response is not None
            fields = self.query_handler.extract_fields(response.full_response)
        else:
            fields = {}
        answer = Answer.from_question(question, response.full_response, fields)
        return answer

    async def dump_answers(self, filter: Optional[Dict[str, Callable[[str], bool]]] = None) -> AsyncIterable[Answer]:
        async for question in self.storage.get_stored_questions():
            if filter is not None:
                if not all(fn(answer) for fn in filter.values()):
                    continue

            response = await self.storage.get_response(question)
            answer = self.build_answer(question, response)
            yield answer