from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from openai import OpenAI
from openai.types.responses import FileSearchToolParam
from dotenv import load_dotenv
import os

load_dotenv()

# === Зависимости агента ===
@dataclass
class AppAgentDeps:
    vector_store_id: Optional[str] = None
    pdf_file_id: Optional[str] = None
    pdf_path: str = 'data/project_info.pdf'
    openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')

# === Модель ответа ===
class AppAgentOutput(BaseModel):
    answer: str = Field(..., description='Ответ на вопрос пользователя')
    source: str = Field(..., description='Источник ответа: "pdf" или "llm"')

# === Вспомогательная функция для загрузки PDF в vector store ===
def setup_vector_store(deps: AppAgentDeps) -> AppAgentDeps:
    client = OpenAI(api_key=deps.openai_api_key)
    # Создаём vector store (однократно)
    vector_store = client.vector_stores.create(name="project_info_store")
    # Загружаем PDF (однократно)
    file_response = client.files.create(file=open(deps.pdf_path, 'rb'), purpose="assistants")
    client.vector_stores.files.create(vector_store_id=vector_store.id, file_id=file_response.id)
    deps.vector_store_id = vector_store.id
    deps.pdf_file_id = file_response.id
    return deps



# === Агент с Responses API и file_search tool ===
def build_agent(vector_store_id: str) -> Agent:
    # Включаем file_search tool для Responses API
    model_settings = OpenAIResponsesModelSettings(
        openai_builtin_tools=[FileSearchToolParam(type='file_search', vector_store_ids=[vector_store_id])]
    )
    model = OpenAIResponsesModel('gpt-4o')
    agent = Agent(
        model=model,
        model_settings=model_settings,
        output_type=AppAgentOutput,
        system_prompt=(
            'Ты — интеллектуальный агент. Если вопрос о приложении, используй file_search tool для поиска по PDF. '
            'Если нет — отвечай как обычный LLM. Всегда указывай источник ответа: "pdf" или "llm".'
        ),
    )
    return agent

# === Пример main ===
def main():
    deps = AppAgentDeps()
    deps = setup_vector_store(deps)
    agent = build_agent(deps.vector_store_id)
    while True:
        query = input("Введите ваш вопрос: ")
        # Для Responses API: file_search tool будет вызван автоматически, если вопрос о приложении
        # Агент сам решит, использовать ли file_search или обычный LLM
        result = agent.run_sync(query)
        print(f"Ответ: {result.output.answer}\nИсточник: {result.output.source}")

if __name__ == "__main__":
    main()
