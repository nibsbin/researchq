
from abc import ABC, abstractmethod
from typing import Type, Optional, Dict, Any
from pydantic import BaseModel
import pandas as pd
from itertools import product
import math
from typing import Dict, List, Any, Optional, Type, Union, Tuple, final, AsyncIterable
import json
from pydantic import BaseModel, ValidationError

# Removed the storage import since it doesn't exist


class Question:
    def __init__(self, word_set: Dict[str, str], template: str, response_model:Type[BaseModel]):
        self.word_set = word_set
        self.template = template
        self.response_model = response_model

    @property
    def value(self) -> str:
        
        return str.format(self.template, **self.word_set)
    
    def __repr__(self) -> str:
        return f"Question(template={self.template}, word_set={self.word_set})"
    
    def __hash__(self) -> int:
        return hash((self.template, frozenset(self.word_set.items())))

    

class QuestionSet:
    def __init__(self, template: str, word_sets: Dict[str, List[str]], response_model:Type[BaseModel]):
        self.template = template
        self.word_sets = word_sets
        self.response_model = response_model

    def get_count(self) -> int:
        return math.prod(len(v) for v in self.word_sets.values())

    def get_questions(self) -> List[Question]:
        combos = product(*(self.word_sets.values()))
        questions = []
        for combo in combos:
            word_set = dict(zip(self.word_sets.keys(), combo))
            questions.append(Question(word_set, self.template, self.response_model))
        return questions
    
@final
class Answer:
    # Fundamental attributes
    word_set: dict
    question_template:str
    question_value: str
    full_response: dict|None
    fields: dict|None
    error: Optional[str]|None

    def __init__(self, word_set: dict, question_template:str, question_value: str, full_response: dict|None, fields: dict|None):
        self.word_set = word_set
        self.question_template = question_template
        self.question_value = question_value
        self.full_response = full_response
        self.fields = fields or {}
        self.error = None

    @staticmethod
    def from_question(question:Question, full_response:Dict[str,Any]|None, fields: Dict[str,Any]|None) -> 'Answer':
        if fields is None:
            fields = {}
        answer = Answer(
            word_set=question.word_set,
            question_template=question.template,
            question_value=question.value,
            full_response=full_response,
            fields=fields
        )
        return answer
    
    def flattened(self) -> pd.DataFrame:
        data = {
            'question': self.question_value,
            'error': self.error
        }
        if not self.error:
            assert self.full_response is not None
            assert self.fields is not None
            data.update(self.word_set)
            data.update(self.fields)
        df = pd.DataFrame([data])
        return df

    def __repr__(self) -> str:
        return f"Answer(question='{self.question_value}', fields={self.fields}, error={self.error})"
@final
class QueryResponse:
    full_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __init__(self, full_response=None, error=None):
        self.full_response = full_response
        self.error = error

    def __repr__(self) -> str:
        return f"QueryResponse(full_response={self.full_response}, error={self.error})"


class QueryHandler(ABC):
    async def query(self, prompt:str) -> QueryResponse:
        raise NotImplementedError()
    
    def extract_fields(self, full_response:Dict[str,Any]) -> dict[str,Any]:
        raise NotImplementedError()
    
class StorageProvider(ABC):
    @abstractmethod
    async def save_response(self, question:Question, response:QueryResponse) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_response(self, question: Question) -> QueryResponse:
        raise NotImplementedError()

    @abstractmethod
    async def delete_response(self, question: Question) -> None:
        raise NotImplementedError()
    
    @abstractmethod
    async def get_stored_questions(self) -> AsyncIterable[Question]:
        raise NotImplementedError()
    