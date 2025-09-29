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
                print("Found doc hit response")
                if response.error:
                    print("Doc hit response has error, flushing:", response.error)
                    response = None
                else:
                    print("Using doc hit response")
                    print(response)

        # If no doc hit response, query
        if response is None:
            prompt = question.value
            response = await self.query_handler.query(prompt=prompt)
            assert response is not None
            assert isinstance(response, QueryResponse)
            await self.storage.save_response(question, response)

        answer = self.build_answer(question, response)
        return answer

    async def _ask_without_cache_check(self, question: Question) -> Answer:
        """Internal method to ask a question without checking cache - used when doc sweep has already been performed."""
        prompt = question.value
        response = await self.query_handler.query(prompt=prompt)
        assert response is not None
        assert isinstance(response, QueryResponse)
        await self.storage.save_response(question, response)
        
        answer = self.build_answer(question, response)
        return answer

    async def ask_multiple_stream(self, question_set: QuestionSet, overwrite:bool=False):
        questions = list(question_set.get_questions())
        total = len(questions)
        print(f"ask_multiple_stream: starting for {total} questions with {self.max_workers} workers")
        
        # Set response model for all questions
        for question in questions:
            question.response_model = question_set.response_model
        
        # Doc sweep: check which questions have doc hits
        doc_hits = []
        doc_misses = []
        
        print("ask_multiple_stream: performing doc sweep...")
        
        for question in questions:
            if not overwrite:
                cached_response = await self.storage.get_response(question)
                if cached_response is not None and not cached_response.error:
                    doc_hits.append((question, cached_response))
                else:
                    doc_misses.append(question)
            else:
                doc_misses.append(question)
        
        doc_hit_count = len(doc_hits)
        doc_miss_count = len(doc_misses)
        
        print(f"ask_multiple_stream: doc sweep complete - {doc_hit_count} doc hit, {doc_miss_count} doc miss")
        
        # First, yield all doc hit responses
        for question, cached_response in doc_hits:
            print(f"Returning doc hit response for: {question.template} - {question.word_set}")
            answer = self.build_answer(question, cached_response)
            yield answer
        
        # Then process doc misses with workers
        if doc_misses:
            semaphore = asyncio.Semaphore(self.max_workers)
            started = 0

            async def process_question(question):
                async with semaphore:
                    nonlocal started
                    started += 1
                    try:
                        print(f"Processing question {started}/{doc_miss_count}: {question.template} - {question.word_set}")
                        # Call ask with skip_cache=True to avoid double cache lookup
                        ans = await self._ask_without_cache_check(question)
                        print(f"Finished question {started}/{doc_miss_count}")
                        return ans
                    except Exception as e:
                        print(f"Error processing question {question.template} with words {question.word_set}: {e}")
                        raise

            tasks = [process_question(q) for q in doc_misses]
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
                for key in filter.keys():
                    if key not in question.word_set:
                        continue
                    fn = filter[key]
                    if not fn(question.word_set[key]):
                        continue

            response = await self.storage.get_response(question)
            answer = self.build_answer(question, response)
            yield answer