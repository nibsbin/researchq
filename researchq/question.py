
from itertools import product
import math
from typing import Dict, List, Any, Optional, Type, Union, Tuple
import json
from string import Template
from pydantic import BaseModel, ValidationError
from llm import query_sonar_structured

from researchq.researchq.storage import QueryStorage


def ask(question: Question, storage: Optional[QueryStorage] = None, response_model:BaseModel):
    prompt = question.get_string()
    result = query_sonar_structured(prompt)
    

class QuestionTemplate:
    def __init__(self, template: Template, word_sets: Dict[str, List[str]]):
        self.template = template
        self.word_sets = word_sets

    def get_count(self) -> int:
        return math.prod(len(v) for v in self.word_sets.values())

    def get_questions(self) -> List[Question]:
        combos = product(*(self.word_sets.values()))
        questions = []
        for combo in combos:
            word_set = dict(zip(self.word_sets.keys(), combo))
            questions.append(Question(word_set, self.template))
        return questions

class Question:
    def __init__(self, word_set: Dict[str, str], template: Template):
        self.word_set = word_set
        self.template = template

    @property
    def get_string(self) -> str:
        return self.template.substitute(**self.word_set)
    
