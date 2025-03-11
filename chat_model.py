from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model_name="ep-20250311103513-hvhq9",
    openai_api_key="ee27bcd9-26d5-41c1-b47b-af78c71b7561",
    openai_api_base="https://ark.cn-beijing.volces.com/api/v3/",
    temperature=0.7
)