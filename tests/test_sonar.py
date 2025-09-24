from robora.sonar_query import SonarQueryHandler
from pydantic import BaseModel
import pytest

class DummyModel(BaseModel):
    field1: str
    field2: int

@pytest.mark.asyncio
async def test_one():
    handler = SonarQueryHandler(response_model=DummyModel)
    result = await handler.query("Test prompt", DummyModel)
    print(result)