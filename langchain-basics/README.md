# [한시간으로 끝내는 LangChain 기본기](https://www.inflearn.com/course/%ED%95%9C%EC%8B%9C%EA%B0%84-%EB%81%9D%EB%82%B4%EB%8A%94-%EB%9E%AD%EC%B2%B4%EC%9D%B8-%EA%B8%B0%EB%B3%B8)

> **LLM 기반 애플리케이션 개발을 위한 필수 프레임워크, LangChain**  
> 이 문서는 "한시간으로 끝내는 LangChain 기본기" 인프런 강의를 학습하고 정리한 저장소입니다.


## 1. LangChain의 목적

LangChain의 주된 목적은 **LLM 기반 애플리케이션 개발을 위해 다양한 구성 요소를 연결하는 것**입니다.

즉, 프롬프트(prompt), 모델(model), 출력 파서(output parser), 메모리(memory), 도구(tool) 등 LLM 관련 모듈들을 손쉽게 **체인(chain)** 형태로 결합할 수 있도록 돕는 프레임워크입니다.


## 2. LangChain의 메시지 타입

LangChain은 LLM에게 **대화 맥락(Context)** 과 **지시(Instruction)** 를 전달할 때  
다양한 메시지 타입을 사용합니다.


<div align="center">


| 메시지 타입 | 설명 |
|--------------|------|
| **System** | AI의 전반적인 동작 원칙이나 역할을 정의 |
| **Human** | 사용자가 입력하는 프롬프트 또는 요청 |
| **AI** | 모델이 생성한 응답을 나타냄 |
| **Tool** | 외부 도구 호출 결과를 메시지 형태로 전달 |

</div>

> 즉, LangChain의 주요 메시지 타입은 `System`, `Human`, `AI`, `Tool` 네 가지입니다.

## 3. 구조화된 출력 받기 (Structured Output)

LLM으로부터 일관된 구조의 데이터를 받기 위해서는 단순히 JSON 문자열을 요청하는 것보다 **Pydantic 모델**을 사용하는 것이 권장됩니다.

### 권장 방식

```python
from langchain_core.pydantic_v1 import BaseModel
from langchain_openai import ChatOpenAI

class Product(BaseModel):
    name: str
    price: float
    description: str

model = ChatOpenAI(model="gpt-4o-mini").with_structured_output(Product)

result = model.invoke("스마트폰 제품 정보를 JSON 형식으로 알려줘.")
print(result)
 ```
💡 JSON Output Parser는 불안정할 수 있습니다.
대신 Pydantic 모델을 활용하면 스키마 검증과 파싱을 자동화할 수 있습니다.

## 4. LCEL (LangChain Expression Language)

LangChain의 핵심은 “체인(Chain)”을 구성하는 것입니다.
여러 구성 요소를 파이프 연산자(|) 로 연결하여 실행 가능한 데이터 흐름을 만들 수 있습니다.

```python
from langchain_core.prompts import ChatPromptTemplate

recipe_prompt = ChatPromptTemplate.from_messages([
    ("system", """Provide the recipe of the food that the user wants. 
    Please return the recipe only as a numbered list."""),
    ("human", "Can you give me the recipe for making {food}?"),
])

recipe_chain = recipe_prompt | llm | StrOutputParser()
```

🔍 LCEL의 | (파이프 연산자)는 Runnable 객체 간 데이터 흐름을 연결하는 핵심 문법입니다.

## 5. RAG (Retriever Augmented Generation)

LLM은 knowledge cut-off에 의해서 특정 과거 시점까지의 데이터로 학습되었기 때문에 최신 정보나 사내 데이터, 외부 문서 기반 응답을 직접 생성할 수 없습니다. 이를 해결하는 방식이 바로 **RAG (검색 증강 생성)** 입니다.

### RAG의 동작 원리

1. Query 입력 – 사용자의 질문을 받는다.

2. Retriever 검색 – 관련 문서를 벡터 검색으로 탐색한다.

3. Context 결합 – 검색된 문서를 LLM의 프롬프트에 포함한다.

4. Generation – 최신 정보 기반의 답변을 생성한다.

즉, RAG는 LLM이 최신 지식에 접근할 수 있게 만드는 핵심 기술입니다.