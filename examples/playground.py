import robora
import asyncio
from robora.classes import Question, QuestionSet, Answer
from robora.workflow import Workflow
from robora.session_storage import SessionStorageProvider
from robora.mock_query import MockQueryHandler, MockResponseModel
from robora.sonar_query import SonarQueryHandler

query_handler = MockQueryHandler(MockResponseModel)
storage_provider = SessionStorageProvider()
workflow = Workflow(query_handler=query_handler, storage=storage_provider)
async def test_one():
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

    async for ans in workflow.ask_multiple(question_set):
        print(f"Answer: {ans}")

async def main():
    await test_one()
    await test_multiple()
    print("\n=====nDumping all stored answers:")
    async for ans in workflow.dump_answers():
        print(ans)

asyncio.run(main())
