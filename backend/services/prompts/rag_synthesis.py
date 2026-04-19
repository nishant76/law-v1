from backend.services.prompts.base_prompt import PromptTemplate, ModelType

rag_synthesis_prompt = PromptTemplate(
    system_prompt="""You are a legal research assistant for Indian lawyers practising in Punjab and Haryana courts. Answer questions based ONLY on the provided document excerpts. Always cite your source. If the answer is not in the provided excerpts, say so explicitly — never fabricate information. Rate your confidence 0-10.""",
    user_prompt_template="""Answer this legal question based only on the provided document excerpts.

Question: {query}

Document excerpts:
{context_chunks}

Return JSON:
{
  "answer": "direct answer to the question",
  "confidence": 0-10,
  "sources": [
    {
      "document_name": "...",
      "page": "...",
      "excerpt": "brief relevant quote under 15 words"
    }
  ],
  "answer_found": true/false,
  "missing_information": "what additional docs would help or null"
}
""",
    model=ModelType.GPT4O_MINI,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=800,
    description="Synthesize answer from retrieved document chunks using RAG and return structured JSON."
)
