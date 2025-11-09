import json
from uuid import uuid4
from fastapi import HTTPException
from app.repositories.vector_store import VectorStore
from app.repositories.redis_repo import ChatHistory
from app.utils.embeddings import EmbeddingClient
from app.utils.llm import LLMClient
from app.services.booking_service import BookingService
from app.schemas.chat import ChatResponse, Citation
from app.schemas.booking import BookingResponse, BookingRequest 

class RAGService:
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingClient,
        chat_history: ChatHistory,
        llm_client: LLMClient,
        booking_service: BookingService,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.chat_history = chat_history
        self.llm = llm_client
        self.booking_service = booking_service

    async def _condense_question(self, messages: list) -> str:
        """If there's a chat history, condense it and the latest question into a standalone question."""
       
        if len(messages) <= 1:
            return messages[-1]["content"]

        prompt = [
            {"role": "system", "content": "Given a chat history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the chat history. Do not answer the question, just reformulate it."},
            {"role": "user", "content": f"Chat History:\n{json.dumps(messages[:-1])}\n\nFollow-up question: {messages[-1]['content']}"}
        ]
        return await self.llm.generate(prompt)

    async def chat(self, user_message: str, conversation_id: str | None, k: int) -> ChatResponse:
        # get/creatre conversation id
        if not conversation_id:
            conversation_id = str(uuid4())
        
        await self.chat_history.add_message(conversation_id, "user", user_message)
        history = await self.chat_history.get_messages(conversation_id)

        # condense question for better retrieval
        try:
            standalone_question = await self._condense_question(history)
        except Exception:
            
            standalone_question = user_message

        # retrieving context from Qdrant
        query_vector = (await self.embedder.embed_texts([standalone_question]))[0]
        retrieved_chunks = await self.vector_store.client.search(
            collection_name=self.vector_store.collection,
            query_vector=query_vector,
            limit=k,
            with_payload=True
        )

        
        context = ""
        citations_set = set() 
        for chunk in retrieved_chunks:
            context += f"\n---\n{chunk.payload.get('text', '')}"
            # Create a tuple to store in the set for uniqueness
            citation_tuple = (chunk.payload['doc_id'], chunk.payload.get('filename'), chunk.score)
            citations_set.add(citation_tuple)
        
        citations = [Citation(doc_id=c[0], filename=c[1], score=c[2]) for c in sorted(list(citations_set), key=lambda x: x[2], reverse=True)]
       
        booking_schema = BookingRequest.model_json_schema()["properties"]
        booking_json_format = json.dumps({"tool_name": "book_interview", "arguments": booking_schema})
        
        system_prompt = f"""You are an expert assistant. Your job is to answer user questions based ONLY on the provided context, or to help them book an interview.

RULES:
1. If the user wants to book an interview, you MUST respond ONLY with a single JSON object matching this exact format: {booking_json_format}
2. If the user is asking a general question, answer it based on the provided context.
3. If the context does not contain the answer, state that you don't know. DO NOT make up information or use prior knowledge.

Context:
{context}
"""
        final_messages = [{"role": "system", "content": system_prompt}, *history]

        # 6. Generating response from LLM 
        try:
            llm_text_response = await self.llm.generate(final_messages)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM provider error: {e}")

        answer, booking_info = "", None

     
        try:
           
            if llm_text_response.strip().startswith('{') and llm_text_response.strip().endswith('}'):
                data = json.loads(llm_text_response)
                if isinstance(data, dict) and data.get("tool_name") == "book_interview":
                    args = data.get("arguments", {})
                    try:
                        booking_result = await self.booking_service.create_booking(**args, conversation_id=conversation_id)
                        booking_info = BookingResponse(**booking_result)
                        answer = f"Success! Your interview is confirmed for {booking_info.start_time_utc.strftime('%A, %B %d at %H:%M UTC')}. A confirmation email will be sent. Booking ID: {booking_info.booking_id}"
                    except (ValueError, RuntimeError) as e:
                        answer = f"I tried to book the interview, but there was a problem. Reason: {e}"
                else:
                   
                    answer = llm_text_response
            else:
              
                answer = llm_text_response
        except (json.JSONDecodeError, AttributeError):
          
            answer = llm_text_response

        # Saving the final assistant response to chat history
        await self.chat_history.add_message(conversation_id, "assistant", answer)

        # final structured response
        return ChatResponse(
            answer=answer,
            conversation_id=conversation_id,
            citations=citations if not booking_info else [], 
            booking_info=booking_info
        )