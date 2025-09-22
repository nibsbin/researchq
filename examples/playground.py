import researchq
import asyncio
from researchq.classes import Question, QuestionSet, Answer
from researchq.ask import Workflow
from researchq.session_storage import SessionStorageProvider
from researchq.mock_query import MockQueryHandler, MockResponseModel
from researchq.sonar_query import SonarQueryHandler

async def test_one():

    query_handler = SonarQueryHandler(MockResponseModel)
    storage_provider = SessionStorageProvider()
    workflow = Workflow(query_handler=query_handler, storage=storage_provider)

    question:Question = Question(
        word_set={
            "organization": "Department of Defense",
            "country": "United States"
        },
        template="What is the cybersecurity posture of the {organization} in {country}?",
        response_model=MockResponseModel
    )
    print(f"Question: {question}")
    print("asking...")

    answer = await workflow.ask(question)

    print(f"Answer: {answer}")

async def test_multiple():
    
    query_handler = MockQueryHandler(MockResponseModel)
    storage_provider = SessionStorageProvider()
    workflow = Workflow(query_handler=query_handler, storage=storage_provider)

    question_set = QuestionSet(
        template="What is the cybersecurity posture of the {organization} in {country}?",
        word_sets={
            "organization": ["Department of Defense", "NASA"],
            "country": ["United States", "Canada"]
        },
        response_model=MockResponseModel
    )
    print(f"QuestionSet: {question_set}")
    print("asking...")

    async for ans in workflow.ask_questions(question_set):
        print(f"Answer: {ans}")


asyncio.run(test_multiple())